"""n5 embed_chunks：SiliconFlow Embedding（openai 兼容客户端 · 人决 D2/D5）。

base_url / api_key / model 全部来自 app.config（env 注入），业务代码零模型名字面量、
零密钥字面量；Key 不落盘明文、不打印（SPEC R3）。对外轨预计算向量（铁律二），
对内子图禁止重算——本模块是唯一 Embedding 调用点。
"""

import logging
from typing import Any

from app import config
from app.services.acquisition.errors import EmbedError

logger = logging.getLogger(__name__)


class ChunkEmbedder:
    """轻量 Embedding 客户端（可注入替换；单元测试一律 mock，禁止真实调用）。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model or config.EMBEDDING_MODEL
        self._client = client
        self._api_key = api_key if api_key is not None else config.SILICONFLOW_API_KEY
        self._base_url = base_url or config.SILICONFLOW_BASE_URL

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化；空输入直接返回空（空 chunks 路径不调 API）；失败抛 EmbedError。"""
        if not texts:
            return []
        if not self._api_key:
            raise EmbedError("SILICONFLOW_API_KEY 为空，Embedding 调用不可用")
        try:
            response = self._get_client().embeddings.create(model=self.model, input=texts)
        except EmbedError:
            raise
        except Exception as exc:
            logger.warning("embedding 调用失败：%s", type(exc).__name__)
            raise EmbedError(f"向量化失败：{type(exc).__name__}") from exc
        vectors = [list(map(float, item.embedding)) for item in response.data]
        if len(vectors) != len(texts):
            raise EmbedError(f"向量化返回数量不符：期望 {len(texts)} 实得 {len(vectors)}")
        logger.info("embedding 完成 chunks=%d dim=%d", len(vectors), len(vectors[0]))
        return vectors
