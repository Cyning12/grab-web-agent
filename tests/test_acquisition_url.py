"""n1 validate_url：SSRF 白名单用例（task 验收 SSRF 行 · SPEC R4 安全用例）。"""

import logging

import pytest

from app.graphs.acquisition import build_acquisition_graph
from app.services.acquisition import UrlRejected, validate_target_url


class TestValidateTargetUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://quote.eastmoney.com/sz000858.html",
            "http://example.com/page",
            "https://quote.eastmoney.com/sz300810.html",
        ],
    )
    def test_public_http_https_accepted(self, url):
        assert validate_target_url(url) == url

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/x",
            "javascript:alert(1)",
            "",
            "not-a-url",
        ],
    )
    def test_non_http_schemes_rejected(self, url):
        with pytest.raises(UrlRejected):
            validate_target_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://10.0.0.1/internal",
            "http://10.255.255.1/",
            "http://172.16.0.1/",
            "http://172.31.255.1/",
            "http://192.168.1.1/",
            "http://127.0.0.1:8000/",
            "http://127.1/",
            "http://169.254.0.1/",
            "http://0.0.0.0/",
            "http://localhost/",
            "http://localhost.localdomain/",
            "http://nas.local/",
            "http://printer.internal/",
            "http://[::1]/",
        ],
    )
    def test_intranet_and_loopback_rejected(self, url):
        with pytest.raises(UrlRejected):
            validate_target_url(url)

    def test_rejection_is_logged(self, caplog):
        with caplog.at_level(logging.WARNING):
            with pytest.raises(UrlRejected):
                validate_target_url("http://192.168.0.1/admin")
        assert any("SSRF" in record.message for record in caplog.records)


class _FetcherMustNotRun:
    def fetch(self, url):  # pragma: no cover - 被调用即测试失败
        raise AssertionError("fetcher 不得在 URL 被拒绝后调用")


class TestGraphEntryRejection:
    def test_file_scheme_rejected_at_entry(self):
        graph = build_acquisition_graph(fetcher=_FetcherMustNotRun())
        result = graph.invoke({"url": "file:///etc/passwd"})
        assert result["error"]["code"] == "URL_REJECTED"
        assert result["error"]["user_message"] == "目标 URL 不被允许"
        assert result["error"]["retryable"] is True
        assert "payload" not in result

    def test_intranet_ip_rejected_at_entry(self):
        graph = build_acquisition_graph(fetcher=_FetcherMustNotRun())
        result = graph.invoke({"url": "http://192.168.1.100/secret"})
        assert result["error"]["code"] == "URL_REJECTED"
        assert "payload" not in result
