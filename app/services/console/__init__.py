"""Web 控制台支撑服务（task_web_console_mvp 范围）。

registry：任务注册表（内存态 + 每订阅者 asyncio.Queue 广播 + 事件历史回放）。
"""

from app.services.console.registry import TaskRecord, TaskRegistry

__all__ = ["TaskRecord", "TaskRegistry"]
