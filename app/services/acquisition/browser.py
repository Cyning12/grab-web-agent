"""n2 fetch_page：Playwright 渲染抓取 + CDP Turbo 加速 + 反爬检测 + 截图落盘。

- 主路径为 Playwright 全量渲染（task R2 裁定 · PRD §4.1 锁定），超时阈值经
  ACQ_FETCH_TIMEOUT_MS 可配置；
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
_SETTLE_MS = 1200

# 反爬特征：HTTP 状态码 + 验证页标题/URL 特征（SPEC FP-2）
_ANTI_BOT_STATUSES = {401, 403}
_ANTI_BOT_PATTERN = re.compile(
    r"(captcha|verify|verification|security check|访问验证|安全验证|滑块|验证码)",
    re.IGNORECASE,
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


class PlaywrightFetcher:
    """Playwright 同步抓取器（可注入替换；timeout_ms / static_dir 可经 env 或参数覆盖）。"""

    def __init__(
        self,
        timeout_ms: int | None = None,
        static_dir: str | Path | None = None,
    ) -> None:
        self.timeout_ms = timeout_ms or int(
            os.getenv("ACQ_FETCH_TIMEOUT_MS", str(_DEFAULT_TIMEOUT_MS))
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
                    page.wait_for_timeout(_SETTLE_MS)
                    http_status = response.status if response else 0
                    anti_bot = self._detect_anti_bot(page, http_status)
                    screenshot_path = self._save_screenshot(page, url)
                    bbox_map = self._collect_bbox_map(page)
                    raw_dom = page.content()
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
            "fetch 完成 url=%s http_status=%d anti_bot=%s dom_bytes=%d",
            url,
            http_status,
            anti_bot,
            len(raw_dom),
        )
        return FetchResult(
            raw_dom=raw_dom,
            http_status=http_status,
            screenshot_path=screenshot_path,
            anti_bot_flag=anti_bot,
            bbox_map=bbox_map,
        )

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
    def _detect_anti_bot(page: Any, http_status: int) -> bool:
        """403/401 状态码或验证页标题/URL 特征命中即判反爬（SPEC FP-2）。"""
        if http_status in _ANTI_BOT_STATUSES:
            return True
        try:
            title = page.title() or ""
        except Exception:
            title = ""
        final_url = page.url or ""
        return bool(_ANTI_BOT_PATTERN.search(title) or _ANTI_BOT_PATTERN.search(final_url))

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
