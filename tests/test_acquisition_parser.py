"""n3 parse_dom：BS4 + CSS 语义推断解析用例（含本地静态测试页夹具）。

夹具页含 H1/H2/价格/Meta DOM（task 验收契约行）；BoundingRect 经注入 bbox_map 绑定。
"""

from app.services.acquisition import parse_page

_SECTION_SENTENCE = "五粮液股份有限公司主营白酒生产与销售，产品覆盖高端与大众价格带，渠道网络遍布全国。"
_SECTIONS = ["公司概况", "主营业务", "财务摘要"]


def _section_html(title: str, index: int) -> str:
    body = _SECTION_SENTENCE * 15  # 每节约 600+ 估计 tokens，保证契约测试可切出合规 chunk
    return f'<h2 id="sec-{index}">{title}</h2><p class="sec-p">{body}</p>'


def build_fixture_html() -> str:
    """本地静态测试页（H1 + 3×H2 正文 + 价格 span + Meta），完整管道契约测试共用。"""
    sections = "".join(
        _section_html(title, idx) for idx, title in enumerate(_SECTIONS)
    )
    return (
        "<html><head>"
        "<title>五粮液(sz000858)股票行情_东方财富</title>"
        '<meta name="description" content="五粮液股票行情与资料">'
        '<meta name="keywords" content="五粮液,sz000858">'
        "</head><body>"
        "<h1>五粮液(sz000858) 公司档案</h1>"
        '<span class="price">¥128.50</span>'
        f"{sections}"
        "</body></html>"
    )


def build_fixture_bbox_map() -> dict:
    """与夹具 DOM 对齐的 xpath -> BoundingRect（模拟浏览器渲染后坐标采集）。"""
    result = {
        "/html[1]/body[1]/h1[1]": [16, 16, 400, 40],
        "/html[1]/body[1]/span[1]": [16, 64, 120, 24],
    }
    for idx in range(len(_SECTIONS)):
        result[f"/html[1]/body[1]/h2[{idx + 1}]"] = [16, 100 + idx * 200, 300, 32]
        result[f"/html[1]/body[1]/p[{idx + 1}]"] = [16, 140 + idx * 200, 800, 160]
    return result


class TestParsePage:
    def test_extracts_title_meta_price(self):
        meta, blocks = parse_page(build_fixture_html(), http_status=200)
        assert meta["title"] == "五粮液(sz000858)股票行情_东方财富"
        assert meta["price"] == "¥128.50"
        assert meta["meta"]["description"] == "五粮液股票行情与资料"
        assert meta["meta"]["keywords"] == "五粮液,sz000858"
        assert meta["http_status"] == 200
        assert len(blocks) >= 7  # h1 + 3×(h2+p)

    def test_blocks_carry_xpath_and_bbox(self):
        _, blocks = parse_page(
            build_fixture_html(), http_status=200, bbox_map=build_fixture_bbox_map()
        )
        for block in blocks:
            assert block["xpath"].startswith("/html[1]/body[1]/")
        h1 = next(b for b in blocks if b["tag"] == "h1")
        assert h1["bbox"] == {"x": 16, "y": 16, "width": 400, "height": 40}
        first_p = next(b for b in blocks if b["tag"] == "p")
        assert first_p["bbox"] == {"x": 16, "y": 140, "width": 800, "height": 160}

    def test_bbox_none_when_map_missing(self):
        _, blocks = parse_page(build_fixture_html(), http_status=200, bbox_map={})
        assert all(block["bbox"] is None for block in blocks)

    def test_empty_body_yields_empty_blocks_without_fallback(self):
        """空解析 -> 空 blocks 继续流转（铁律一：不存在任何降级调用路径）。"""
        meta, blocks = parse_page("<html><head></head><body></body></html>", 200)
        assert blocks == []
        assert meta["title"] == ""
        assert meta["price"] == ""

    def test_script_style_noise_excluded(self):
        html = (
            "<html><body><script>var price=999;</script>"
            "<style>.price{color:red}</style>"
            f"<p>{_SECTION_SENTENCE}</p></body></html>"
        )
        _, blocks = parse_page(html, 200)
        texts = [b["text"] for b in blocks]
        assert not any("var price" in t or "color:red" in t for t in texts)

    def test_price_fallback_regex(self):
        html = f"<html><body><p>最新价 128.50 元。{_SECTION_SENTENCE}</p></body></html>"
        meta, _ = parse_page(html, 200)
        assert meta["price"] == "128.50"
