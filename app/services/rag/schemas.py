"""对内子图 Schema（架构 §1.5 跨子图契约逐字段对齐）。

① PRD §6.2 标准 Payload（对外产出 / 对内消费双向校验）
② 结论 JSON Schema + 回填回执（SPEC A4/A5）
契约违例（字段缺失/类型不符/缺 embedding）= m1 失败路径第一行（铁律二：对内禁重算 Embedding）。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PreChunk(BaseModel):
    """PRD §6.2 pre_chunks[]（对外轨预计算向量，缺失即契约违例）。"""

    title: str
    text: str
    embedding: list[float]  # 必填 · 缺失 = 契约违例（铁律二）
    xpath: str = Field(min_length=1)
    section_path: str = Field(min_length=1)
    token_count: int = Field(ge=512, le=1024)  # PRD §4.3 · SPEC A3 区间断言


class ExtractedMeta(BaseModel):
    """PRD §6.2 extracted_meta（http_status 为 SPEC A2 强制扩展字段）。"""

    title: str
    price: str
    http_status: int
    meta: dict[str, Any] = Field(default_factory=dict)


class Payload(BaseModel):
    """PRD §6.2 标准 Payload（pre_chunks 可空数组 = 解析为空失败路径，正常流转）。"""

    url: str
    screenshot_path: str
    extracted_meta: ExtractedMeta
    pre_chunks: list[PreChunk]

    @field_validator("url")
    @classmethod
    def _url_scheme(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url 仅允许 http/https 协议")
        return v


class Conclusion(BaseModel):
    """结论 JSON（SPEC A4 三字段 + 信息不足标记 + 溯源列表）。

    「信息不足」结论 = insufficient_info=True 且三字段给占位文案，仍通过本 Schema 校验。
    """

    competitor_price: str
    risk_level: Literal["低", "中", "高"]
    suggested_action: str
    insufficient_info: bool
    sources: list[str] = Field(default_factory=list)


class Receipt(BaseModel):
    """回填回执（SPEC A5 闭环：ticket_id 非空且与 Tool Node 回调一致；V1 恒 mock=true）。"""

    status: Literal["success", "failed"]
    ticket_id: str | None
    reason: str | None
    mock: bool = True
