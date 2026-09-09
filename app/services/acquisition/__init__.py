"""对外子图服务层（Web Acquisition · 胖采集）。

模块划分（架构 §1.3 六节点的实现细节下沉处）：
- errors：统一异常与 error dict 构造（对齐 §1.5 错误码词汇表）
- url_validator：n1 SSRF 白名单校验
- browser：n2 Playwright + CDP Turbo 抓取 / 反爬检测 / 截图落盘 / BoundingRect 采集
- parser：n3 BeautifulSoup + CSS 语义推断解析（铁律一：唯一内容提取路径）
- chunker：n4 H1/H2 语义切分（每块 512–1024 tokens）
- embedder：n5 SiliconFlow Embedding（openai 兼容客户端，base_url/model 全部来自 app.config）
- payload：n6 标准 Payload 组装与 §1.5 Schema 校验
"""

from app.services.acquisition.browser import FetchResult, PlaywrightFetcher
from app.services.acquisition.chunker import MAX_TOKENS, MIN_TOKENS, chunk_blocks, estimate_tokens
from app.services.acquisition.embedder import ChunkEmbedder
from app.services.acquisition.errors import (
    AcquisitionError,
    AntiBotDetected,
    EmbedError,
    FetchFailed,
    FetchTimeout,
    PayloadInvalid,
    UrlRejected,
    make_error,
)
from app.services.acquisition.parser import element_xpath, parse_page
from app.services.acquisition.payload import (
    PAYLOAD_SCHEMA,
    assert_payload,
    build_payload,
    validate_payload,
)
from app.services.acquisition.url_validator import validate_target_url

__all__ = [
    "AcquisitionError",
    "AntiBotDetected",
    "ChunkEmbedder",
    "EmbedError",
    "FetchFailed",
    "FetchResult",
    "FetchTimeout",
    "MAX_TOKENS",
    "MIN_TOKENS",
    "PAYLOAD_SCHEMA",
    "PayloadInvalid",
    "PlaywrightFetcher",
    "UrlRejected",
    "assert_payload",
    "build_payload",
    "chunk_blocks",
    "element_xpath",
    "estimate_tokens",
    "make_error",
    "parse_page",
    "validate_payload",
    "validate_target_url",
]
