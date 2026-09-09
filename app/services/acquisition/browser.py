"""n2 fetch_page：Playwright 渲染抓取 + CDP Turbo 加速 + 渲染完成确认 + 反爬检测 + 截图落盘。

- 主路径为 Playwright 全量渲染（task R2 裁定 · PRD §4.1 锁定），超时阈值经
  ACQ_FETCH_TIMEOUT_MS 可配置；
- 渲染完成确认（task_fetch_render_wait_lite）：goto 后 wait_for_load_state
  （networkidle 优先 / domcontentloaded 兜底）+ 非占位文本等待，确认通过才交
  parse_dom；等待超时抛 FetchTimeout（终态 Error）。阈值经 FETCH_RENDER_TIMEOUT_MS
  可配置（本模块内 os.getenv 读取 · app/config.py 为共享冻结文件）；
- 滑块/验证码覆盖层检测（东财「拖动下方滑块完成拼图」等特征 · 人决 D7 放宽）：
  检出后先跑渲染确认探针（非占位内容门槛）；探针通过 -> slider_overlay_flag=True
  降级为警告继续解析（Supervisor 透传 warning 事件 + 结论标注「页面含验证覆盖层」），
  探针不通过 -> 维持 anti_bot_flag=True -> ANTI_BOT 终态；403/401 与验证页
  title/URL 硬特征不放宽；任何分支均不主动绕过验证；
- CDP Turbo：路由拦截丢弃 font/media 等大体积静态资源，仅保留 DOM/脚本/图片，
  换取渲染吞吐（收益未量化，V1 接受基线，见 task residual_risks）；
- BoundingRect：渲染后 DOM 才有布局信息（架构 §1.3 n2 注），抓取阶段以
  xpath -> bbox 映射随 FetchResult 带出，供 n3 parse_dom 绑定；
- 截图仅落盘 app/static/（payload 写 /static 相对路径），职责封闭为
  「落盘 + 展示 + 人工复核」三用途，不做任何像素级分析（铁律一）。
"""

import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.acquisition.errors import FetchFailed, FetchTimeout

logger = logging.getLogger(__name__)

_DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[2] / "static"
_DEFAULT_TIMEOUT_MS = 30000
_DEFAULT_RENDER_TIMEOUT_MS = 10000
_SETTLE_MS = 1200
_CONTENT_READY_MIN_CHARS = 30

# 反爬特征：HTTP 状态码 + 验证页标题/URL 特征（SPEC FP-2）
_ANTI_BOT_STATUSES = {401, 403}
_ANTI_BOT_PATTERN = re.compile(
    r"(captcha|verify|verification|security check|访问验证|安全验证|滑块|验证码)",
    re.IGNORECASE,
)

# 滑块/验证码覆盖层特征：东财「拖动下方滑块完成拼图」等软反爬（title/URL 无特征时
# 补扫正文 innerText 与 DOM 组件签名；命中后由渲染确认探针裁决降级警告或 ANTI_BOT）
_SLIDER_OVERLAY_PATTERN = re.compile(
    r"(拖动下方滑块完成拼图|拖动左边滑块|拖动滑块|滑动滑块|滑块验证|滑块拼图|"
    r"请完成安全验证|nc-container|nc_wrapper|geetest|slide-verify|滑块)",
    re.IGNORECASE,
)

# 滑块组件常挂独立 iframe（东财实证：i.eastmoney.com/websitecaptcha/slidervalid），
# 主框架 innerText/content 均扫不到，须按子框架 URL + 子框架正文补扫
_CAPTCHA_FRAME_URL_PATTERN = re.compile(
    r"(websitecaptcha|slidervalid|captcha|geetest)", re.IGNORECASE
)

# 非占位文本等待脚本：body 可见文本剔除空白与占位符（- — – _）后须达阈值，
# 用于确认 JS 异步渲染真实完成（东财个股页未渲染时字段多为「-」占位）
_CONTENT_READY_JS = (
    "() => {"
    "  const el = document.body;"
    "  if (!el) return false;"
    f"  const text = (el.innerText || '').replace(/[\\s\\-—–_]/g, '');"
    f"  return text.length >= {_CONTENT_READY_MIN_CHARS};"
    "}"
)

# 渲染后 DOM 的 xpath -> BoundingRect 采集脚本（xpath 规则与 parser.element_xpath 逐字对齐）
_BBOX_MAP_JS = """() => {
  const tags = new Set(['h1','h2','h3','h4','p','li','tr','td','th','div','span','table','section','article']);
  const xp = (el) => {
    if (el.tagName.toLowerCase() === 'html') return '/html[1]';
    let ix = 1;
    let sib = el.previousElementSibling;
    while (sib) { if (sib.tagName === el.tagName) ix++; sib = sib.previousElementSibling; }
    return xp(el.parentElement) + '/' + el.tagName.toLowerCase() + '[' + ix + ']';
  };
  const map = {};
  document.querySelectorAll([...tags].join(',')).forEach((el) => {
    const r = el.getBoundingClientRect();
    map[xp(el)] = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
  });
  return map;
}"""


@dataclass
class FetchResult:
    """n2 输出（对齐架构 §1.3 n2 输出 State + bbox_map 供 n3 绑定 BoundingRect）。"""

    raw_dom: str
    http_status: int
    screenshot_path: str
    anti_bot_flag: bool
    bbox_map: dict[str, list[int]] = field(default_factory=dict)
    # 人决 D7：检出滑块覆盖层但渲染确认探针通过（警告但继续解析，非反爬终态）
    slider_overlay_flag: bool = False


class PlaywrightFetcher:
    """Playwright 同步抓取器（可注入替换；timeout_ms / static_dir 可经 env 或参数覆盖）。"""

    def __init__(
        self,
        timeout_ms: int | None = None,
        render_timeout_ms: int | None = None,
        static_dir: str | Path | None = None,
    ) -> None:
        self.timeout_ms = timeout_ms or int(
            os.getenv("ACQ_FETCH_TIMEOUT_MS", str(_DEFAULT_TIMEOUT_MS))
        )
        # 渲染确认超时阈值（networkidle / 兜底 / 非占位文本等待共用 · env 可配）
        self.render_timeout_ms = render_timeout_ms or int(
            os.getenv("FETCH_RENDER_TIMEOUT_MS", str(_DEFAULT_RENDER_TIMEOUT_MS))
        )
        self.static_dir = Path(static_dir or os.getenv("ACQ_STATIC_DIR") or _DEFAULT_STATIC_DIR)

    def fetch(self, url: str) -> FetchResult:
        """渲染抓取单 URL；超时抛 FetchTimeout，其余抓取异常归一为 FetchFailed。"""
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright

        self.static_dir.mkdir(parents=True, exist_ok=True)
        logger.info("fetch 开始 url=%s timeout_ms=%d", url, self.timeout_ms)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    self._enable_cdp_turbo(page)
                    response = page.goto(
                        url, wait_until="domcontentloaded", timeout=self.timeout_ms
                    )
                    self._wait_for_render(page, url)  # 渲染完成确认：未通过即 FetchTimeout
                    page.wait_for_timeout(_SETTLE_MS)
                    http_status = response.status if response else 0
                    raw_dom = page.content()
                    anti_bot = self._detect_hard_anti_bot(page, http_status)
                    slider_overlay = False
                    if not anti_bot and self._detect_slider_overlay(page, raw_dom):
                        # 人决 D7：检出滑块覆盖层先跑渲染确认探针（非占位内容门槛）；
                        # 探针通过 -> 降级为警告继续解析，探针不通过 -> ANTI_BOT 终态；
                        # 两种分支均不主动绕过验证
                        if self._content_probe_passed(page):
                            slider_overlay = True
                            logger.warning(
                                "页面含验证覆盖层（渲染探针通过，降级为警告继续）url=%s", url
                            )
                        else:
                            anti_bot = True
                            logger.warning(
                                "滑块覆盖层检出且渲染探针不通过 url=%s -> ANTI_BOT 终态", url
                            )
                    screenshot_path = self._save_screenshot(page, url)
                    # 反爬终态页无采集价值：仅截图留痕，跳过 bbox 采集
                    bbox_map = {} if anti_bot else self._collect_bbox_map(page)
                finally:
                    browser.close()
        except PlaywrightTimeout as exc:
            logger.warning("fetch 超时 url=%s timeout_ms=%d", url, self.timeout_ms)
            raise FetchTimeout(f"目标页面抓取超时（{self.timeout_ms}ms）：{url}", url=url) from exc
        except (FetchTimeout, FetchFailed):
            raise
        except Exception as exc:  # 浏览器不可用 / 导航失败等归一为 FETCH_FAILED
            logger.warning("fetch 失败 url=%s err=%s", url, exc)
            raise FetchFailed(f"目标页面抓取失败：{url}（{exc}）", url=url) from exc
        logger.info(
            "fetch 完成 url=%s http_status=%d anti_bot=%s slider_overlay=%s dom_bytes=%d",
            url,
            http_status,
            anti_bot,
            slider_overlay,
            len(raw_dom),
        )
        return FetchResult(
            raw_dom=raw_dom,
            http_status=http_status,
            screenshot_path=screenshot_path,
            anti_bot_flag=anti_bot,
            bbox_map=bbox_map,
            slider_overlay_flag=slider_overlay,
        )

    def _wait_for_render(self, page: Any, url: str) -> None:
        """渲染完成确认：networkidle 优先 / domcontentloaded 兜底 + 非占位文本等待。

        - networkidle 超时降级为 domcontentloaded 等待（不视为失败）；
        - 非占位文本等待超时 -> FetchTimeout（终态 Error，失败路径第 2 行），
          确认通过前不放行 parse_dom（task_fetch_render_wait_lite 范围第 1 行）。
        """
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        try:
            page.wait_for_load_state("networkidle", timeout=self.render_timeout_ms)
        except PlaywrightTimeout:
            logger.info(
                "networkidle 等待超时，兜底 domcontentloaded url=%s timeout_ms=%d",
                url,
                self.render_timeout_ms,
            )
            try:
                page.wait_for_load_state(
                    "domcontentloaded", timeout=self.render_timeout_ms
                )
            except PlaywrightTimeout as exc:
                logger.warning("渲染等待超时（load_state 兜底亦超时）url=%s", url)
                raise FetchTimeout(
                    f"目标页面抓取超时（渲染确认 {self.render_timeout_ms}ms）：{url}",
                    url=url,
                ) from exc
        try:
            page.wait_for_function(_CONTENT_READY_JS, timeout=self.render_timeout_ms)
        except PlaywrightTimeout as exc:
            logger.warning(
                "渲染等待超时（非占位文本未就绪）url=%s timeout_ms=%d",
                url,
                self.render_timeout_ms,
            )
            raise FetchTimeout(
                f"目标页面抓取超时（{self.render_timeout_ms}ms 内未渲染出有效内容）：{url}",
                url=url,
            ) from exc

    @staticmethod
    def _enable_cdp_turbo(page: Any) -> None:
        """CDP Turbo：路由拦截丢弃 font/media 资源（PRD §4.1 CDP Turbo 加速）。"""

        def _route_handler(route: Any) -> None:
            if route.request.resource_type in {"media", "font"}:
                route.abort()
            else:
                route.continue_()

        page.route("**/*", _route_handler)

    @staticmethod
    def _detect_hard_anti_bot(page: Any, http_status: int) -> bool:
        """硬反爬检出（D7 不放宽）：403/401 状态码或验证页标题/URL 特征（SPEC FP-2）。"""
        if http_status in _ANTI_BOT_STATUSES:
            return True
        try:
            title = page.title() or ""
        except Exception:
            title = ""
        final_url = page.url or ""
        return bool(
            _ANTI_BOT_PATTERN.search(title) or _ANTI_BOT_PATTERN.search(final_url)
        )

    @staticmethod
    def _detect_slider_overlay(page: Any, raw_dom: str = "") -> bool:
        """滑块/验证码覆盖层检出（东财「拖动下方滑块完成拼图」等软反爬）。

        覆盖层常 200 + 正常 title，故补扫正文 innerText 与 raw_dom 组件签名；
        检出后的裁决（警告继续 / ANTI_BOT 终态）由 fetch() 经渲染确认探针完成
        （人决 D7 · task_fetch_render_wait_lite 失败路径第 3 行）。
        """
        try:
            body_text = (
                page.evaluate("() => (document.body ? document.body.innerText : '')")
                or ""
            )
        except Exception:
            body_text = ""
        if _SLIDER_OVERLAY_PATTERN.search(body_text) or _SLIDER_OVERLAY_PATTERN.search(
            raw_dom
        ):
            return True
        # 子框架补扫：滑块组件在 iframe 内（主框架 DOM/正文均不可见）
        try:
            frames = list(page.frames)[1:]
        except Exception:
            frames = []
        for frame in frames:
            try:
                frame_url = frame.url or ""
            except Exception:
                frame_url = ""
            if _CAPTCHA_FRAME_URL_PATTERN.search(frame_url):
                return True
            try:
                frame_text = (
                    frame.evaluate(
                        "() => (document.body ? document.body.innerText : '')"
                    )
                    or ""
                )
            except Exception:  # 跨域子框架不可读时跳过（URL 特征已先行判定）
                continue
            if _SLIDER_OVERLAY_PATTERN.search(frame_text):
                return True
        return False

    @staticmethod
    def _content_probe_passed(page: Any) -> bool:
        """渲染确认探针（人决 D7 放行前提）：主框架非占位文本达阈值即视内容真实渲染。

        复用 _CONTENT_READY_JS 口径（与 _wait_for_render 同一门槛）；探针异常
        （页面崩溃/上下文销毁等）一律视为不通过 -> ANTI_BOT 终态，不放大放行面。
        """
        try:
            return bool(page.evaluate(_CONTENT_READY_JS))
        except Exception:
            return False

    def _save_screenshot(self, page: Any, url: str) -> str:
        """整页截图落盘 static_dir，返回 /static 相对路径（SPEC A6 可追溯）。"""
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        filename = f"shot_{digest}_{int(time.time() * 1000)}.png"
        page.screenshot(path=str(self.static_dir / filename), full_page=True)
        return f"/static/{filename}"

    @staticmethod
    def _collect_bbox_map(page: Any) -> dict[str, list[int]]:
        """采集 xpath -> BoundingRect 映射（绑定发生在 n3，此处仅取渲染后坐标）。"""
        try:
            result = page.evaluate(_BBOX_MAP_JS)
            return {str(k): list(v) for k, v in result.items()}
        except Exception as exc:  # 坐标采集失败不阻断主路径，bbox 降级为 None
            logger.warning("bbox_map 采集失败（降级为无坐标）：%s", exc)
            return {}
