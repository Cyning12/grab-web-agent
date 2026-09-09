"""n2 fetch_page 渲染完成确认 + 滑块/验证码覆盖层检测单测（task_fetch_render_wait_lite）。

纪律：禁真实浏览器 / 禁外网 —— 以 FakePage + monkeypatch playwright.sync_api.sync_playwright
注入桩驱动真实 PlaywrightFetcher 全路径；滑块检出断言走 ANTI_BOT 终态（图级闭环）。
"""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from app.graphs.acquisition import build_acquisition_graph, clear_status_hooks
from app.services.acquisition import FetchResult, FetchTimeout
from app.services.acquisition.browser import PlaywrightFetcher
from test_acquisition_parser import build_fixture_html

# 1x1 像素 PNG（截图桩落盘用）
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c6264f8cf500f00018601805a747d6b"
    "0000000049454e44ae426082"
)

# 东财「拖动下方滑块完成拼图」滑块验证覆盖层夹具（真机验收截图留证特征）
SLIDER_FIXTURE_HTML = (
    "<html><head><title>东方财富网</title></head><body>"
    '<div id="nc_wrapper" class="nc-container">'
    '<span class="nc-lang-cnt">拖动下方滑块完成拼图</span>'
    '<div class="geetest_slider">slide to verify</div>'
    "</div>"
    "<p>请完成安全验证后继续访问</p>"
    "</body></html>"
)

_NORMAL_BODY_TEXT = "五粮液(sz000858) 公司档案 主营白酒生产与销售 股价 ¥128.50 盘口数据齐全"
_SLIDER_BODY_TEXT = "拖动下方滑块完成拼图 请完成安全验证后继续访问"


def _body_text_of(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


class FakePage:
    """Playwright Page 桩：记录调用序，断言「内容就绪前不放行」。"""

    def __init__(
        self,
        html: str,
        *,
        body_text: str | None = None,
        networkidle_ok: bool = True,
        content_ready: bool = True,
        http_status: int = 200,
        sub_frames: list | None = None,
        frame_url: str = "",
    ):
        self._html = html
        self._body_text = body_text if body_text is not None else _body_text_of(html)
        self.networkidle_ok = networkidle_ok
        self.content_ready = content_ready
        self.http_status = http_status
        self._sub_frames = sub_frames or []
        self._frame_url = frame_url
        self.calls: list[tuple] = []

    @property
    def frames(self):
        """Playwright 语义：frames[0] 为主框架。"""
        return [self, *self._sub_frames]

    # --- 导航与等待 ---
    def route(self, *_a, **_k):
        self.calls.append(("route",))

    def goto(self, url, wait_until, timeout):
        self.calls.append(("goto", wait_until))
        return SimpleNamespace(status=self.http_status)

    def wait_for_load_state(self, state, timeout=None):
        self.calls.append(("wait_for_load_state", state))
        if state == "networkidle" and not self.networkidle_ok:
            raise PlaywrightTimeout("networkidle timeout")
        if state == "domcontentloaded" and not self.networkidle_ok and not self.content_ready:
            raise PlaywrightTimeout("domcontentloaded timeout")

    def wait_for_function(self, js, timeout=None):
        self.calls.append(("wait_for_function",))
        if not self.content_ready:
            raise PlaywrightTimeout("content not ready")

    def wait_for_timeout(self, ms):
        self.calls.append(("wait_for_timeout", ms))

    # --- 取数 ---
    def title(self):
        m = re.search(r"<title>(.*?)</title>", self._html)
        return m.group(1) if m else ""

    @property
    def url(self):
        return self._frame_url or "https://quote.eastmoney.com/concept/sz000858.html"

    def content(self):
        self.calls.append(("content",))
        return self._html

    def screenshot(self, path, full_page=False):
        self.calls.append(("screenshot",))
        with open(path, "wb") as fh:
            fh.write(_PNG_BYTES)

    def evaluate(self, js):
        self.calls.append(("evaluate",))
        if "innerText" in js:
            return self._body_text
        return {}  # bbox 采集脚本


class FakeBrowser:
    def __init__(self, page: FakePage):
        self._page = page

    def new_page(self, viewport=None):
        return self._page

    def close(self):
        pass


class FakePlaywright:
    def __init__(self, page: FakePage):
        self.chromium = SimpleNamespace(launch=lambda headless=True: FakeBrowser(page))

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _patch_playwright(monkeypatch, page: FakePage):
    monkeypatch.setattr(
        "playwright.sync_api.sync_playwright", lambda: FakePlaywright(page)
    )


@pytest.fixture(autouse=True)
def _clean_hooks():
    clear_status_hooks()
    yield
    clear_status_hooks()


class TestRenderWait:
    """渲染完成确认：networkidle 优先 / domcontentloaded 兜底 + 非占位文本等待。"""

    def test_waits_networkidle_then_content_before_releasing_dom(
        self, tmp_path, monkeypatch
    ):
        page = FakePage(build_fixture_html(), body_text=_NORMAL_BODY_TEXT)
        _patch_playwright(monkeypatch, page)
        result = PlaywrightFetcher(static_dir=tmp_path).fetch(page.url)

        states = [c[1] for c in page.calls if c[0] == "wait_for_load_state"]
        assert states[0] == "networkidle"  # networkidle 优先
        kinds = [c[0] for c in page.calls]
        # 非占位文本等待（wait_for_function）先于 content() 取 DOM —— 内容就绪前不放行
        assert kinds.index("wait_for_function") < kinds.index("content")
        assert result.raw_dom == build_fixture_html()
        assert result.anti_bot_flag is False

    def test_networkidle_timeout_falls_back_to_domcontentloaded(
        self, tmp_path, monkeypatch
    ):
        page = FakePage(
            build_fixture_html(), body_text=_NORMAL_BODY_TEXT, networkidle_ok=False
        )
        _patch_playwright(monkeypatch, page)
        result = PlaywrightFetcher(static_dir=tmp_path).fetch(page.url)

        states = [c[1] for c in page.calls if c[0] == "wait_for_load_state"]
        assert states == ["networkidle", "domcontentloaded"]  # 兜底链
        assert result.anti_bot_flag is False

    def test_content_wait_timeout_raises_fetch_timeout(self, tmp_path, monkeypatch):
        """非占位文本等待超时 -> FetchTimeout（终态 Error · 失败路径第 2 行）。"""
        page = FakePage(
            "<html><body><p>-</p></body></html>", body_text="- - -", content_ready=False
        )
        _patch_playwright(monkeypatch, page)
        with pytest.raises(FetchTimeout) as exc_info:
            PlaywrightFetcher(static_dir=tmp_path).fetch(page.url)
        assert "超时" in str(exc_info.value)
        # 渲染确认未通过即失败，不放行 content() 取半成品 DOM
        assert ("content",) not in page.calls

    def test_render_timeout_ms_env_override(self, monkeypatch):
        monkeypatch.setenv("FETCH_RENDER_TIMEOUT_MS", "4321")
        fetcher = PlaywrightFetcher()
        assert fetcher.render_timeout_ms == 4321


class TestSliderDetection:
    """滑块/验证码覆盖层检出 -> ANTI_BOT；正常页不误报。"""

    def test_slider_overlay_detected_from_content(self, tmp_path, monkeypatch):
        page = FakePage(SLIDER_FIXTURE_HTML, body_text=_SLIDER_BODY_TEXT)
        _patch_playwright(monkeypatch, page)
        result = PlaywrightFetcher(static_dir=tmp_path).fetch(page.url)
        assert result.anti_bot_flag is True
        # 滑块截图留痕供人工复核（SPEC FP-2）
        assert result.screenshot_path.startswith("/static/")

    def test_slider_fixture_lands_anti_bot_terminal_error(self, tmp_path, monkeypatch):
        """图级闭环：滑块夹具 -> ANTI_BOT 终态 Error，禁止继续解析半成品。"""

        class SliderFetcher:
            def fetch(self, url):
                return FetchResult(
                    raw_dom=SLIDER_FIXTURE_HTML,
                    http_status=200,
                    screenshot_path="/static/shot_slider.png",
                    anti_bot_flag=PlaywrightFetcher._detect_anti_bot(
                        FakePage(SLIDER_FIXTURE_HTML, body_text=_SLIDER_BODY_TEXT),
                        200,
                        SLIDER_FIXTURE_HTML,
                    ),
                    bbox_map={},
                )

        graph = build_acquisition_graph(fetcher=SliderFetcher(), embedder=SimpleNamespace())
        result = graph.invoke({"url": "https://quote.eastmoney.com/concept/sz000858.html"})
        assert result["error"]["code"] == "ANTI_BOT"
        assert "反爬拦截" in result["error"]["user_message"]
        assert "payload" not in result
        assert "blocks" not in result  # 未进入 parse_dom

    def test_slider_in_iframe_detected_by_frame_url(self, tmp_path, monkeypatch):
        """滑块组件挂独立 iframe（东财实证 websitecaptcha/slidervalid）：主框架干净亦须检出。"""
        captcha_frame = FakePage(
            "<html><body>loading</body></html>",
            body_text="loading",
            frame_url="https://i.eastmoney.com/websitecaptcha/slidervalid",
        )
        page = FakePage(
            build_fixture_html(), body_text=_NORMAL_BODY_TEXT, sub_frames=[captcha_frame]
        )
        _patch_playwright(monkeypatch, page)
        result = PlaywrightFetcher(static_dir=tmp_path).fetch(page.url)
        assert result.anti_bot_flag is True

    def test_slider_in_iframe_detected_by_frame_text(self, tmp_path, monkeypatch):
        """iframe URL 无特征但子框架正文含滑块文案 -> 检出。"""
        captcha_frame = FakePage(
            SLIDER_FIXTURE_HTML,
            body_text=_SLIDER_BODY_TEXT,
            frame_url="https://i.eastmoney.com/anon/widget",
        )
        page = FakePage(
            build_fixture_html(), body_text=_NORMAL_BODY_TEXT, sub_frames=[captcha_frame]
        )
        _patch_playwright(monkeypatch, page)
        result = PlaywrightFetcher(static_dir=tmp_path).fetch(page.url)
        assert result.anti_bot_flag is True

    def test_benign_iframe_no_false_positive(self, tmp_path, monkeypatch):
        """正常广告/数据 iframe（same.eastmoney.com 等）不误报。"""
        ad_frame = FakePage(
            "<html><body><p>广告位</p></body></html>",
            body_text="广告位",
            frame_url="https://same.eastmoney.com/s?z=eastmoney&c=1747&op=1",
        )
        page = FakePage(
            build_fixture_html(), body_text=_NORMAL_BODY_TEXT, sub_frames=[ad_frame]
        )
        _patch_playwright(monkeypatch, page)
        result = PlaywrightFetcher(static_dir=tmp_path).fetch(page.url)
        assert result.anti_bot_flag is False

    def test_normal_fixture_no_false_positive(self, tmp_path, monkeypatch):
        """正常行情页夹具不误报滑块/反爬。"""
        page = FakePage(build_fixture_html(), body_text=_NORMAL_BODY_TEXT)
        _patch_playwright(monkeypatch, page)
        result = PlaywrightFetcher(static_dir=tmp_path).fetch(page.url)
        assert result.anti_bot_flag is False
        assert "五粮液" in result.raw_dom
