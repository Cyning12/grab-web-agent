"""内部知识库 Top-K 混合检索（FAISS 进程内索引 · 显式禁用 Rerank · SPEC R2 分叉二）。

- 混合检索 = 向量相似度 + 标量过滤（company_code）拼接：先按向量分数取过采样集合，
  再按标量过滤截取 Top-K；结果顺序即 FAISS 分数序，无任何重排序步骤（铁律三 / SPEC 非范围 7）。
- 检索接口抽象（Retriever Protocol）：FAISS 调用封闭在 FaissVectorStore 内，
  不散落于业务逻辑，V2 可替换 Qdrant 实现（task R2 接口抽象约束）。
- 语料 = company/ 目录（人决 D6：按上市编号命名，如 000858/ 300810/）；语料 Embedding
  经注入的 embed_fn（SiliconFlow bge-m3 API · D5），本进程不加载任何本地 Embedding 模型（铁律二）。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

import faiss
import numpy as np

_logger = logging.getLogger(__name__)

EmbedFn = Callable[[list[str]], list[list[float]]]


@dataclass
class CorpusDoc:
    """语料切片（索引构建期产物）。"""

    text: str
    company_code: str  # company/ 子目录名（上市编号，如 000858）
    source_path: str  # 语料文件相对路径（溯源用）


@dataclass
class RetrievedChunk:
    """检索命中（context_chunks 元素）。"""

    text: str
    company_code: str
    source_path: str
    score: float


class Retriever(Protocol):
    """检索接口抽象（SPEC R2 遗留建议：向量库可替换，FAISS 调用不得散落业务逻辑）。"""

    def search(
        self, query_embedding: list[float], top_k: int, company_code: str | None = None
    ) -> list[RetrievedChunk]: ...


class FaissVectorStore:
    """FAISS 进程内向量库（IndexFlatIP + L2 归一化 = 余弦相似度 · 禁 Rerank）。"""

    def __init__(self, dim: int) -> None:
        self._index = faiss.IndexFlatIP(dim)
        self._docs: list[CorpusDoc] = []

    @classmethod
    def from_docs(cls, docs: list[CorpusDoc], embed_fn: EmbedFn) -> "FaissVectorStore":
        if not docs:
            raise ValueError("语料为空，无法构建索引")
        vectors = embed_fn([d.text for d in docs])
        store = cls(dim=len(vectors[0]))
        store.add(docs, vectors)
        return store

    def add(self, docs: list[CorpusDoc], vectors: list[list[float]]) -> None:
        arr = np.asarray(vectors, dtype=np.float32)
        faiss.normalize_L2(arr)
        self._index.add(arr)
        self._docs.extend(docs)

    def __len__(self) -> int:
        return len(self._docs)

    def search(
        self, query_embedding: list[float], top_k: int, company_code: str | None = None
    ) -> list[RetrievedChunk]:
        """Top-K 混合检索：向量分数过采样 → 标量过滤拼接 → 截取 K（无 Rerank，顺序=分数序）。"""
        if len(self._docs) == 0 or top_k <= 0:
            return []
        q = np.asarray([query_embedding], dtype=np.float32)
        faiss.normalize_L2(q)
        oversample = min(len(self._docs), max(top_k * 4, top_k + 8))
        scores, idxs = self._index.search(q, oversample)
        hits = [
            RetrievedChunk(
                text=self._docs[i].text,
                company_code=self._docs[i].company_code,
                source_path=self._docs[i].source_path,
                score=float(s),
            )
            for s, i in zip(scores[0], idxs[0])
            if 0 <= i < len(self._docs)
        ]
        if company_code:
            filtered = [h for h in hits if h.company_code == company_code]
            if filtered:
                return filtered[:top_k]
            _logger.info("标量过滤无命中（company_code=%s），回退纯向量 Top-%d", company_code, top_k)
        return hits[:top_k]


_COMPANY_CODE_RE = re.compile(r"(?:sz|sh)?(\d{6})")


def derive_company_code(url: str) -> str | None:
    """从目标 URL 提取上市编号（如 quote.eastmoney.com/sz000858.html → 000858）。"""
    m = _COMPANY_CODE_RE.search(url)
    return m.group(1) if m else None


def _extract_pdf_text(path: Path) -> str:
    """PDF 文本提取（pypdf）；解析失败记 warning 返回空串，不中断索引构建。"""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # pypdf 缺失 / 加密 / 扫描件无文本层
        _logger.warning("PDF 文本提取失败，跳过 %s：%s", path, exc)
        return ""


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    _logger.warning("不支持的语料格式，跳过：%s", path)
    return ""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """定长滑窗切分（语料侧轻量切分；对外 chunk 语义切分属 T-ACQ 范围）。"""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(text), step):
        piece = text[start : start + chunk_size].strip()
        if piece:
            chunks.append(piece)
    return chunks


def load_corpus(corpus_dir: str | Path, chunk_size: int = 800, overlap: int = 100) -> list[CorpusDoc]:
    """扫描 company/ 语料目录（D6 约定：子目录名=上市编号），切分为 CorpusDoc 列表。"""
    root = Path(corpus_dir)
    docs: list[CorpusDoc] = []
    if not root.is_dir():
        _logger.warning("语料目录不存在：%s（V1 接受空库 · task residual_risks ①）", root)
        return docs
    for company_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        company_code = company_dir.name
        for f in sorted(company_dir.rglob("*")):
            if not f.is_file() or f.name.startswith("."):
                continue
            for piece in chunk_text(_extract_text(f), chunk_size, overlap):
                docs.append(
                    CorpusDoc(
                        text=piece,
                        company_code=company_code,
                        source_path=str(f.relative_to(root)),
                    )
                )
    _logger.info("语料加载完成：%d 个切片（目录 %s）", len(docs), root)
    return docs


def build_index_from_corpus(
    corpus_dir: str | Path, embed_fn: EmbedFn, chunk_size: int = 800, overlap: int = 100
) -> FaissVectorStore:
    """从 company/ 语料构建 FAISS 索引（Embedding 走注入的 embed_fn，本地不加载模型）。"""
    docs = load_corpus(corpus_dir, chunk_size, overlap)
    if not docs:
        raise ValueError(f"语料目录无可用文本：{corpus_dir}")
    return FaissVectorStore.from_docs(docs, embed_fn)
