"""tests/test_fetch_cninfo.py —— scripts/fetch_cninfo.py 单测（mock httpx，零外网）。"""

from __future__ import annotations

import io
from urllib.parse import parse_qs

import httpx
import pytest
from pypdf import PdfWriter

from scripts import fetch_cninfo


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


PDF_BYTES = _make_pdf_bytes()

ANNOUNCEMENTS = [
    {"announcementTitle": "2026年半年度报告", "adjunctUrl": "finalpage/2026-08-29/1002.PDF", "announcementTime": 1787932800000},
    {"announcementTitle": "2026年半年度报告摘要", "adjunctUrl": "finalpage/2026-08-29/1001.PDF", "announcementTime": 1787932800000},
    {"announcementTitle": "2025年年度报告（更新后）", "adjunctUrl": "finalpage/2026-04-30/2091.PDF", "announcementTime": 1777544425000},
    {"announcementTitle": "2025年年度报告（更新前）", "adjunctUrl": "finalpage/2025-08-28/1999.PDF", "announcementTime": 1756310400000},
    {"announcementTitle": "2025年年度报告（英文版）", "adjunctUrl": "finalpage/2026-05-23/24762.PDF", "announcementTime": 1779465600000},
    {"announcementTitle": "第七届董事会2026年第11次会议决议公告", "adjunctUrl": "finalpage/2026-03-01/3000.PDF", "announcementTime": 1772000000000},
]


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)


def _ok_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/topSearch/query"):
        code = parse_qs(request.content.decode())["keyWord"][0]
        return httpx.Response(200, json=[{"code": code, "orgId": f"gssz0000{code[-3:]}", "zwjc": "测试"}])
    if path.endswith("/hisAnnouncement/query"):
        return httpx.Response(200, json={"announcements": ANNOUNCEMENTS, "totalAnnouncement": 6})
    if request.url.host == "static.cninfo.com.cn":
        return httpx.Response(200, content=PDF_BYTES)
    return httpx.Response(404)


class TestNormalizeCode:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("000858", "000858"), ("sz000858", "000858"), ("SZ000858", "000858"),
         ("SH600519", "600519"), ("bj830799", "830799"), (" 300810 ", "300810")],
    )
    def test_valid(self, raw, expected):
        assert fetch_cninfo.normalize_code(raw) == expected

    @pytest.mark.parametrize("raw", ["12345", "0008587", "xx000858", "", "sz00858", "abcdef"])
    def test_invalid(self, raw):
        with pytest.raises(ValueError):
            fetch_cninfo.normalize_code(raw)


def test_main_two_codes_creates_dirs_and_filters(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(fetch_cninfo.time, "sleep", lambda *_: None)
    rc = fetch_cninfo.main(
        ["sz000858", "300810", "--limit", "2", "--out-dir", str(tmp_path)],
        client=_client(_ok_handler),
    )
    assert rc == 0
    for code in ("000858", "300810"):
        pdfs = sorted((tmp_path / code).glob("*.pdf"))
        names = [p.name for p in pdfs]
        assert "2026年半年度报告.pdf" in names
        assert "2025年年度报告（更新后）.pdf" in names
        assert len(pdfs) == 2  # 摘要/英文/更新前/决议公告均已剔除，同期去重取更新后
        for p in pdfs:
            assert p.read_bytes() == PDF_BYTES
    out = capsys.readouterr().out
    assert "成功 4 份" in out


def test_invalid_code_errors_and_creates_no_dir(tmp_path, capsys):
    rc = fetch_cninfo.main(["xx000858", "--out-dir", str(tmp_path)], client=_client(_ok_handler))
    assert rc == 2
    assert list(tmp_path.iterdir()) == []
    assert "非法上市编号" in capsys.readouterr().err


def test_unknown_code_no_dir_and_failure_list(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(fetch_cninfo.time, "sleep", lambda *_: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])  # topSearch 查无此编号

    rc = fetch_cninfo.main(["000999", "--out-dir", str(tmp_path)], client=_client(handler))
    assert rc == 0
    assert not (tmp_path / "000999").exists()
    assert "失败 1 项" in capsys.readouterr().out


def test_download_failure_skips_file_and_continues(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(fetch_cninfo.time, "sleep", lambda *_: None)
    calls = {"bad": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "static.cninfo.com.cn" and "1002" in request.url.path:
            calls["bad"] += 1
            return httpx.Response(500, text="server error")
        return _ok_handler(request)

    rc = fetch_cninfo.main(["000858", "--limit", "2", "--out-dir", str(tmp_path)], client=_client(handler))
    assert rc == 0
    pdfs = [p.name for p in (tmp_path / "000858").glob("*.pdf")]
    assert pdfs == ["2025年年度报告（更新后）.pdf"]  # 坏的那份重试 2 次后跳过
    assert calls["bad"] == 3  # 首次 + 重试 ≤2
    out = capsys.readouterr().out
    assert "成功 1 份" in out and "失败 1 项" in out


def test_corrupt_pdf_deleted_and_counted(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(fetch_cninfo.time, "sleep", lambda *_: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "static.cninfo.com.cn" and "1002" in request.url.path:
            return httpx.Response(200, content=b"not a pdf at all")
        return _ok_handler(request)

    rc = fetch_cninfo.main(["000858", "--limit", "2", "--out-dir", str(tmp_path)], client=_client(handler))
    assert rc == 0
    pdfs = [p.name for p in (tmp_path / "000858").glob("*.pdf")]
    assert pdfs == ["2025年年度报告（更新后）.pdf"]  # 坏文件已删除
    assert "PDF 损坏" in capsys.readouterr().out
