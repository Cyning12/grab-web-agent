"""m1 receive_validate 契约校验单测（架构 §1.5 表① · T-RAG 失败路径契约行）。

契约违例（字段缺失/类型不符/缺 embedding）→ error{code:"CONTRACT_VIOLATION"}，
图短路至终态 Error，不产生结论（铁律二：缺 embedding 不得重算，只能拒绝）。
"""

from internal_rag_fakes import make_deps, make_payload
from app.graphs.internal_rag import run_internal_rag


def _run(payload):
    return run_internal_rag(payload, deps=make_deps())


def test_valid_payload_passes_validation():
    result = _run(make_payload())
    assert "error" not in result
    assert result["payload_validated"].url == "https://quote.eastmoney.com/sz000858.html"


def test_missing_embedding_is_contract_violation():
    payload = make_payload()
    for chunk in payload["pre_chunks"]:
        del chunk["embedding"]  # 铁律二边界：缺 embedding = 契约违例，禁止对内重算
    result = _run(payload)
    assert result["error"]["code"] == "CONTRACT_VIOLATION"
    assert "conclusion" not in result  # 短路终态，不进入检索/生成/回填


def test_non_http_url_rejected():
    payload = make_payload(url="ftp://internal.host/x")
    result = _run(payload)
    assert result["error"]["code"] == "CONTRACT_VIOLATION"


def test_missing_screenshot_path_is_contract_violation():
    payload = make_payload()
    del payload["screenshot_path"]
    result = _run(payload)
    assert result["error"]["code"] == "CONTRACT_VIOLATION"


def test_token_count_out_of_range_is_contract_violation():
    payload = make_payload()
    payload["pre_chunks"][0]["token_count"] = 100  # PRD §4.3 区间 [512,1024]（SPEC A3）
    result = _run(payload)
    assert result["error"]["code"] == "CONTRACT_VIOLATION"


def test_empty_xpath_is_contract_violation():
    payload = make_payload()
    payload["pre_chunks"][0]["xpath"] = ""  # §1.5 表①：xpath 必填非空（SPEC A3 可溯源）
    result = _run(payload)
    assert result["error"]["code"] == "CONTRACT_VIOLATION"


def test_contract_violation_emits_error_event():
    result = _run({"url": "not-a-url"})
    events = result["events"]
    assert any(e["event"] == "error" and e["data"]["code"] == "CONTRACT_VIOLATION" for e in events)
