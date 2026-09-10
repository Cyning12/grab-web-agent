"""腾讯 gu.qq.com 页解析/切分用例（task_switch_target_gu_qq · 人决 D8 默认目标）。

fixture = 2026-09-09 真机 Playwright 渲染后 DOM 快照（tests/fixtures/gu_qq_sz000858.html，
https://gu.qq.com/sz000858/gp · http 200 · anti_bot=False）：
- 解析断言：title/price 为真实值、blocks ≥1 且 xpath 非空、正文非全占位；
- 切分断言：pre_chunks ≥1 且 token_count ∈ [512, 1024]、section_path/xpath 非空；
- 价格最小适配回归：span#price 纯标签「分价」不得误提取，标题带价正则兜底。
"""

import re
from pathlib import Path

from app.services.acquisition import parse_page
from app.services.acquisition.chunker import chunk_blocks

FIXTURE = Path(__file__).parent / "fixtures" / "gu_qq_sz000858.html"
_PLACEHOLDER = re.compile(r"^[-—–_\s]*$")


def _load() -> str:
    return FIXTURE.read_text(encoding="utf-8")


class TestGuQqFixtureParse:
    def test_fixture_extracts_real_content(self):
        meta, blocks = parse_page(_load(), http_status=200)
        assert meta["title"]  # 快照标题「五 粮 液 71.16 -0.49(-0.68%)_财经频道_腾讯网」
        assert "五粮" in meta["title"].replace(" ", "")
        assert meta["price"] == "71.16"  # 真价在标题；span#price=「分价」标签不得误提取
        assert blocks
        for block in blocks:
            assert block["xpath"].startswith("/")
        # 正文非全占位：存在 ≥30 字符的非占位正文块（真实行情/资讯文本）
        assert any(
            len(b["text"]) >= 30 and not _PLACEHOLDER.match(b["text"]) for b in blocks
        )

    def test_fixture_chunks_legal(self):
        _, blocks = parse_page(_load(), http_status=200)
        chunks = chunk_blocks(blocks)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert 512 <= chunk["token_count"] <= 1024
            assert chunk["section_path"] and chunk["xpath"]
            assert not _PLACEHOLDER.match(chunk["text"])


class TestPriceLabelSkip:
    """parser 最小适配回归：纯标签命中跳过 + 标题正则兜底（腾讯页语义增补）。"""

    def test_price_selector_label_without_digits_skipped(self):
        html = (
            "<html><head><title>某股票 71.16 -0.49(-0.68%)_财经频道</title></head>"
            '<body><span id="price">分价</span></body></html>'
        )
        meta, _ = parse_page(html, 200)
        assert meta["price"] == "71.16"

    def test_price_selector_numeric_hit_still_wins(self):
        html = (
            "<html><head><title>某股票 71.16 行情</title></head>"
            '<body><span class="price">¥128.50</span></body></html>'
        )
        meta, _ = parse_page(html, 200)
        assert meta["price"] == "¥128.50"
