"""禁 Rerank / 禁本地 Embedding 模型加载审计（铁律二/三 · 验收「禁 Rerank 审计」行）。

- 检索路径代码（app/services/rag/ + app/graphs/internal_rag.py）无 rerank 标识符调用
  （以 tokenize 提取 NAME token 判定，注释/文档字符串中的「禁 Rerank」字样不误伤）；
- 对内进程不加载任何本地 Embedding 模型（sentence_transformers/torch/transformers 等
  一律禁止 import；Embedding 只经 SiliconFlow API，语料索引构建亦不落地本地模型）。
"""

import io
import re
import tokenize
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCOPE = sorted((REPO_ROOT / "app/services/rag").glob("*.py")) + [
    REPO_ROOT / "app/graphs/internal_rag.py"
]

_FORBIDDEN_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+(sentence_transformers|torch|transformers|flagembedding)\b",
    re.M | re.I,
)


def _name_tokens(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    return [
        tok.string
        for tok in tokenize.generate_tokens(io.StringIO(src).readline)
        if tok.type == tokenize.NAME
    ]


def test_no_rerank_identifier_in_retrieval_path():
    offenders = []
    for path in SCOPE:
        for name in _name_tokens(path):
            if "rerank" in name.lower():
                offenders.append(f"{path.name}: {name}")
    assert not offenders, f"检索路径存在 Rerank 调用（铁律三显式禁用）：{offenders}"


def test_no_local_embedding_model_imports():
    offenders = []
    for path in SCOPE:
        src = path.read_text(encoding="utf-8")
        for m in _FORBIDDEN_IMPORT_RE.finditer(src):
            offenders.append(f"{path.name}: {m.group(0).strip()}")
    assert not offenders, f"对内进程禁止加载本地 Embedding 模型（铁律二）：{offenders}"


def test_audit_scope_files_exist():
    names = {p.name for p in SCOPE}
    assert {"retriever.py", "generator.py", "writeback.py", "schemas.py", "resources.py"} <= names
    assert "internal_rag.py" in names
