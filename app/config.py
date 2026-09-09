"""全局配置：全部经环境变量读取（python-dotenv）并给默认值。

纪律（task_project_scaffold R3 边界二/三）：
- 密钥仅以 SILICONFLOW_API_KEY env 变量名引用，空值占位，禁止硬编码明文；
- 模型选型（D5）仅以 LLM_MODEL / EMBEDDING_MODEL env 变量名引用，
  业务代码内不得出现第二个模型名字面量；默认值与 .env.example 逐字一致。
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

_logger = logging.getLogger(__name__)

# --- SiliconFlow（D2 服务商 · D5 模型选型） ---
SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V4-Flash")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# --- 进程端口（架构 §0 双进程拓扑） ---
FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8000"))
FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))

# --- 语料与目标（D6 语料目录 · D4 MVP 场景） ---
COMPANY_DIR: str = os.getenv("COMPANY_DIR", "./company")
TASK_TARGET_URLS: list[str] = [
    u.strip()
    for u in os.getenv(
        "TASK_TARGET_URLS",
        "https://quote.eastmoney.com/sz000858.html,https://quote.eastmoney.com/sz300810.html",
    ).split(",")
    if u.strip()
]

if not SILICONFLOW_API_KEY:
    # 失败路径第 4 行：缺 Key 仅记 warning 一行，stub 节点不调 LLM/Embedding，不阻断冒烟。
    _logger.warning("SILICONFLOW_API_KEY 为空：LLM/Embedding 调用不可用（stub 骨架阶段不阻断）")
