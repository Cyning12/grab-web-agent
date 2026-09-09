"""对外子图全管道契约测试与失败注入（task 验收契约/截图/铁律一/失败注入/状态钩子行）。

- 契约测试：本地静态测试页（H1/H2/价格 DOM）跑完整六节点管道，产出 Payload 过 §1.5 校验；
- fetcher / embedder 全部注入桩，单元测试零真实浏览器 / 零真实 Embedding / 零外网；
- live 冒烟（真实东财页 + 真实 Embedding）须显式 ACQ_LIVE_SMOKE=1 开启，默认关闭。
"""

import logging
import os
from pathlib import Path

import pytest

from app.graphs.acquisition import (
    build_acquisition_graph,
    clear_status_hooks,
    register_status_hook,
)
from app.services.acquisition import (
    EmbedError,
    FetchResult,
    FetchTimeout,
    validate_payload,
)
from test_acquisition_parser import build_fixture_bbox_map, build_fixture_html

# 1x1 像素 PNG（截图桩落盘用，断言「真实落盘可读」）
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c6264f8cf500f00018601805a747d6b"
    "0000000049454e44ae426082"
)


@pytest.fixture(autouse=True)
def _clean_hooks():
    clear_status_hooks()
    yield
    clear_status_hooks()


class FakeFetcher:
    """抓取桩：返回夹具 DOM + 坐标映射，并把 PNG 桩字节真实写入 tmp static 目录。"""

    def __init__(self, static_dir: Path, dom: str | None = None, http_status: int = 200):
        self.static_dir = static_dir
        self.dom = dom if dom is not None else build_fixture_html()
        self.http_status = http_status
        self.calls = []

    def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        filename = "shot_test_contract.png"
        (self.static_dir / filename).write_bytes(_PNG_BYTES)
        return FetchResult(
            raw_dom=self.dom,
            http_status=self.http_status,
            screenshot_path=f"/static/{filename}",
            anti_bot_flag=False,
            bbox_map=build_fixture_bbox_map(),
        )


class FakeEmbedder:
    def __init__(self, dim=8):
        self.dim = dim
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[0.1 + i * 0.01] * self.dim for i, _ in enumerate(texts)]


class FailingEmbedder:
    def embed(self, texts):
        raise EmbedError("向量化失败：RuntimeError")


class TimeoutFetcher:
    def fetch(self, url):
        raise FetchTimeout(f"目标页面抓取超时（30000ms）：{url}", url=url)


class AntiBotFetcher:
    def __init__(self, static_dir: Path):
        self.static_dir = static_dir

    def fetch(self, url):
        filename = "shot_test_antibot.png"
        (self.static_dir / filename).write_bytes(_PNG_BYTES)
        return FetchResult(
            raw_dom="<html><body>验证页</body></html>",
            http_status=403,
            screenshot_path=f"/static/{filename}",
            anti_bot_flag=True,
            bbox_map={},
        )


class TestContractPipeline:
    """完整管道（本地静态页）：Payload 过 §1.5 校验 + 截图落盘 + 切分断言 + 状态钩子。"""

    def test_full_pipeline_payload_contract(self, tmp_path):
        fetcher, embedder = FakeFetcher(tmp_path), FakeEmbedder()
        events = []
        register_status_hook(events.append)
        graph = build_acquisition_graph(fetcher=fetcher, embedder=embedder)
        result = graph.invoke({"url": "https://quote.eastmoney.com/sz000858.html"})

        assert "error" not in result
        payload = result["payload"]
        # ① §1.5 契约逐字段校验（url/screenshot_path/extracted_meta/pre_chunks 齐全）
        assert validate_payload(payload) == []
        assert payload["url"] == "https://quote.eastmoney.com/sz000858.html"
        assert payload["extracted_meta"]["http_status"] == 200
        assert payload["extracted_meta"]["price"] == "¥128.50"
        # ② 切分断言：块长 ∈ [512, 1024] 且 section_path/xpath 非空
        assert payload["pre_chunks"]
        for chunk in payload["pre_chunks"]:
            assert 512 <= chunk["token_count"] <= 1024
            assert chunk["section_path"] and chunk["xpath"]
            assert len(chunk["embedding"]) == 8
        # ③ 截图断言：payload 路径可追溯且文件真实落盘可读
        shot_rel = payload["screenshot_path"]
        assert shot_rel.startswith("/static/")
        shot_file = tmp_path / Path(shot_rel).name
        assert shot_file.read_bytes().startswith(b"\x89PNG")
        # ④ BoundingRect 经 bbox_map 绑定到解析块
        h1_block = next(b for b in result["blocks"] if b["tag"] == "h1")
        assert h1_block["bbox"] == {"x": 16, "y": 16, "width": 400, "height": 40}
        # ⑤ 状态钩子：Fetching -> Parsing 迁移事件可被 Supervisor 层观测
        assert any(
            event.get("from") == "Fetching"
            and event.get("to") == "Parsing"
            and event.get("progress") == 50
            for event in events
        )

    def test_iron_rule_one_no_multimodal_calls(self, tmp_path, caplog):
        """铁律一审计：全流程日志无任何多模态/视觉模型调用记录。"""
        with caplog.at_level(logging.DEBUG):
            graph = build_acquisition_graph(
                fetcher=FakeFetcher(tmp_path), embedder=FakeEmbedder()
            )
            graph.invoke({"url": "https://quote.eastmoney.com/sz000858.html"})
        banned = ("multimodal", "vision", "多模态", "视觉")
        for record in caplog.records:
            message = record.getMessage().lower()
            assert not any(word in message for word in banned), record.getMessage()


class TestFailureInjection:
    """失败注入 ×3（task 验收失败行 · SPEC R4-5）：超时桩 / 403 反爬桩 / 空 body 桩。"""

    def test_fetch_timeout_terminal_error(self, tmp_path):
        events = []
        register_status_hook(events.append)
        graph = build_acquisition_graph(fetcher=TimeoutFetcher(), embedder=FakeEmbedder())
        result = graph.invoke({"url": "https://quote.eastmoney.com/sz000858.html"})
        assert result["error"]["code"] == "FETCH_TIMEOUT"
        assert result["error"]["user_message"] == "目标页面抓取超时，请稍后重试"
        assert result["error"]["retryable"] is True
        assert "payload" not in result
        assert any(event.get("to") == "Error" for event in events)

    def test_anti_bot_403_terminal_error(self, tmp_path):
        graph = build_acquisition_graph(
            fetcher=AntiBotFetcher(tmp_path), embedder=FakeEmbedder()
        )
        result = graph.invoke({"url": "https://quote.eastmoney.com/sz000858.html"})
        assert result["error"]["code"] == "ANTI_BOT"
        assert "反爬拦截" in result["error"]["user_message"]
        assert result["http_status"] == 403
        # 反爬截图留痕（SPEC FP-2）
        assert result["screenshot_path"].endswith("shot_test_antibot.png")
        assert "payload" not in result

    def test_empty_parse_flows_with_empty_chunks(self, tmp_path):
        """空 body 桩：不降级、不报错，Payload 带空 pre_chunks 正常流转（SPEC FP-3）。"""
        embedder = FakeEmbedder()
        graph = build_acquisition_graph(
            fetcher=FakeFetcher(tmp_path, dom="<html><head></head><body></body></html>"),
            embedder=embedder,
        )
        result = graph.invoke({"url": "https://quote.eastmoney.com/sz000858.html"})
        assert "error" not in result
        payload = result["payload"]
        assert payload["pre_chunks"] == []
        assert validate_payload(payload) == []
        assert embedder.calls == []  # 空 chunks 不调 Embedding

    def test_embed_failure_terminal_error(self, tmp_path):
        graph = build_acquisition_graph(
            fetcher=FakeFetcher(tmp_path), embedder=FailingEmbedder()
        )
        result = graph.invoke({"url": "https://quote.eastmoney.com/sz000858.html"})
        assert result["error"]["code"] == "EMBED_FAILED"
        assert result["error"]["user_message"] == "向量化失败，请稍后重试"
        assert "payload" not in result


@pytest.mark.skipif(
    os.getenv("ACQ_LIVE_SMOKE") != "1",
    reason="live 冒烟默认关闭（真实浏览器 + 真实 SiliconFlow Embedding + 外网）",
)
class TestLiveSmoke:
    """可选 live 冒烟：ACQ_LIVE_SMOKE=1 时跑真实东财页（concept 极速版 · task_fetch_render_wait_lite）。"""

    def test_live_eastmoney(self, tmp_path):
        from app.services.acquisition import ChunkEmbedder, PlaywrightFetcher

        graph = build_acquisition_graph(
            fetcher=PlaywrightFetcher(static_dir=tmp_path), embedder=ChunkEmbedder()
        )
        result = graph.invoke({"url": "https://quote.eastmoney.com/concept/sz000858.html"})
        if "error" in result:  # 反爬/超时属已定义失败路径，live 环境不保证成功率
            assert result["error"]["code"] in {
                "FETCH_TIMEOUT",
                "FETCH_FAILED",
                "ANTI_BOT",
                "EMBED_FAILED",
            }
        else:
            assert validate_payload(result["payload"]) == []
            assert (tmp_path / Path(result["payload"]["screenshot_path"]).name).exists()
