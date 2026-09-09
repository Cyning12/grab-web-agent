"""n4 chunk_sections：H1/H2 语义切分用例（task 验收切分断言行 · SPEC A3）。

不变式：每条 chunk token_count ∈ [512, 1024] 且 section_path / xpath 非空；
整页文本不足 512 tokens -> 空 pre_chunks（SPEC FP-3）。
"""

from app.services.acquisition import MAX_TOKENS, MIN_TOKENS, chunk_blocks, estimate_tokens
from app.services.acquisition.chunker import _take_prefix, _take_suffix


def _blocks_from_sections(section_token_sizes):
    blocks = [{"tag": "h1", "text": "公司档案", "xpath": "/html[1]/body[1]/h1[1]"}]
    for idx, size in enumerate(section_token_sizes):
        blocks.append(
            {"tag": "h2", "text": f"章节{idx}", "xpath": f"/html[1]/body[1]/h2[{idx + 1}]"}
        )
        # 4 CJK/字 * 重复次数控制体量，句号为句边界
        repeats = max(1, size // 20)
        blocks.append(
            {
                "tag": "p",
                "text": "这是用于切分体量控制的完整中文句子。" * repeats,
                "xpath": f"/html[1]/body[1]/p[{idx + 1}]",
            }
        )
    return blocks


class TestEstimateTokens:
    def test_cjk_one_char_one_token(self):
        assert estimate_tokens("五粮液") == 3

    def test_latin_runs_four_chars_per_token(self):
        assert estimate_tokens("sz000858") == 2

    def test_empty(self):
        assert estimate_tokens("") == 0


class TestChunkBlocks:
    def test_sections_in_range_with_paths(self):
        chunks = chunk_blocks(_blocks_from_sections([600, 600, 600]))
        assert chunks
        for chunk in chunks:
            assert MIN_TOKENS <= chunk["token_count"] <= MAX_TOKENS
            assert chunk["section_path"]
            assert chunk["xpath"]
            assert chunk["title"]

    def test_small_sections_merge(self):
        chunks = chunk_blocks(_blocks_from_sections([200, 200, 200, 200]))
        assert len(chunks) == 1
        assert MIN_TOKENS <= chunks[0]["token_count"] <= MAX_TOKENS

    def test_oversized_section_splits(self):
        chunks = chunk_blocks(_blocks_from_sections([2500]))
        assert len(chunks) >= 2
        for chunk in chunks:
            assert MIN_TOKENS <= chunk["token_count"] <= MAX_TOKENS

    def test_oversized_single_sentence_hard_cut(self):
        blocks = [
            {"tag": "h1", "text": "章节", "xpath": "/html[1]/body[1]/h1[1]"},
            {"tag": "p", "text": "无句号长句连续文本" * 150, "xpath": "/html[1]/body[1]/p[1]"},
        ]
        chunks = chunk_blocks(blocks)
        assert chunks
        for chunk in chunks:
            assert MIN_TOKENS <= chunk["token_count"] <= MAX_TOKENS

    def test_tail_remainder_rebalanced_into_range(self):
        # 1390 tokens 总量：贪婪得 [~930, ~460]，尾部须向首 chunk 借句补足 ≥ 512
        blocks = [
            {"tag": "h1", "text": "五粮液公司档案", "xpath": "/html[1]/body[1]/h1[1]"}
        ]
        for idx in range(3):
            blocks.append(
                {"tag": "h2", "text": f"章节{idx}", "xpath": f"/html[1]/body[1]/h2[{idx + 1}]"}
            )
            blocks.append(
                {
                    "tag": "p",
                    "text": "公司主营业务涵盖白酒酿造与全国渠道销售网络建设，" * 19,
                    "xpath": f"/html[1]/body[1]/p[{idx + 1}]",
                }
            )
        chunks = chunk_blocks(blocks)
        assert len(chunks) == 2
        for chunk in chunks:
            assert MIN_TOKENS <= chunk["token_count"] <= MAX_TOKENS

    def test_tiny_page_yields_empty_chunks(self):
        blocks = [{"tag": "p", "text": "一点点内容", "xpath": "/html[1]/body[1]/p[1]"}]
        assert chunk_blocks(blocks) == []

    def test_empty_blocks_yield_empty_chunks(self):
        assert chunk_blocks([]) == []

    def test_section_path_tracks_h1_h2_hierarchy(self):
        chunks = chunk_blocks(_blocks_from_sections([600, 600, 600]))
        paths = {chunk["section_path"] for chunk in chunks}
        assert any("公司档案" in path for path in paths)
        assert any("章节" in path for path in paths)

    def test_content_before_first_heading_gets_fallback_path(self):
        blocks = [
            {"tag": "p", "text": "页首正文。" * 120, "xpath": "/html[1]/body[1]/p[1]"}
        ]
        chunks = chunk_blocks(blocks)
        assert chunks[0]["section_path"] == "页面正文"


class TestTextSplitHelpers:
    def test_take_prefix_respects_budget(self):
        text = "句子一。" * 300
        prefix, rest = _take_prefix(text, 600)
        assert estimate_tokens(prefix) <= 600
        assert rest

    def test_take_suffix_respects_budget(self):
        text = "句子二。" * 300
        head, tail = _take_suffix(text, 600)
        assert estimate_tokens(tail) <= 600
        assert head
