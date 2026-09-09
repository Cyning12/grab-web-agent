"""n5 embed_chunks：Embedding 用例（mock openai 兼容客户端 · 禁止真实 API 调用）。

Embedding 失败路径：error{EMBED_FAILED} + 用户可见文案「向量化失败，请稍后重试」。
"""

import pytest

from app.services.acquisition import ChunkEmbedder, EmbedError


class _FakeResponse:
    def __init__(self, vectors):
        self.data = [type("Item", (), {"embedding": vector}) for vector in vectors]


class _FakeClient:
    def __init__(self, dim=8, fail=None):
        self.dim = dim
        self.fail = fail
        self.calls = []
        self.embeddings = self

    def create(self, model, input):
        self.calls.append({"model": model, "input": list(input)})
        if self.fail:
            raise self.fail
        return _FakeResponse([[0.1] * self.dim for _ in input])


class TestChunkEmbedder:
    def test_embed_returns_vectors_per_text(self):
        client = _FakeClient(dim=16)
        embedder = ChunkEmbedder(api_key="test-key", model="test-model", client=client)
        vectors = embedder.embed(["文本一", "文本二"])
        assert len(vectors) == 2
        assert all(len(vector) == 16 for vector in vectors)
        assert client.calls[0]["model"] == "test-model"

    def test_empty_input_skips_api(self):
        client = _FakeClient()
        embedder = ChunkEmbedder(api_key="test-key", client=client)
        assert embedder.embed([]) == []
        assert client.calls == []

    def test_api_failure_raises_embed_error(self):
        client = _FakeClient(fail=RuntimeError("boom"))
        embedder = ChunkEmbedder(api_key="test-key", client=client)
        with pytest.raises(EmbedError):
            embedder.embed(["文本"])

    def test_missing_api_key_raises_embed_error(self):
        embedder = ChunkEmbedder(api_key="", client=_FakeClient())
        with pytest.raises(EmbedError):
            embedder.embed(["文本"])

    def test_count_mismatch_raises_embed_error(self):
        client = _FakeClient()
        embedder = ChunkEmbedder(api_key="test-key", client=client)

        class _ShortResponse:
            data = [type("Item", (), {"embedding": [0.1]})]

        client.embeddings = type("E", (), {"create": lambda self, model, input: _ShortResponse()})
        with pytest.raises(EmbedError):
            embedder.embed(["文本一", "文本二"])
