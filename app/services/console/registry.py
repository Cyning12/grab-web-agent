"""任务注册表（架构 §1.1「任务注册表内存态结构」逐字段对齐）。

- 内存 dict 存任务状态（SPEC FP-5：内存态可接受、须日志可查、服务重启即丢 —— V1 接受）；
- 每 SSE 订阅者一个 asyncio.Queue，Supervisor 钩子经 emit() 广播写入；
- history 保留全量 SSE 事件序列：SSE 订阅即回放（断线补拉语义 · 架构 §2.3），
  前端以回放事件幂等重建三区块，无数据空洞；
- 终态集合 {Done, Error}：所有失败路径均落终态，不滞留中间态（SPEC A9）。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

TERMINAL_STATUSES: frozenset[str] = frozenset({"Done", "Error"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TaskRecord:
    """单任务内存态（架构 §1.1 注册表字段表）。"""

    task_id: str
    url: str
    status: str = "Pending"
    status_detail: str | None = None
    progress: int = 0
    payload: dict[str, Any] | None = None
    # D7：滑块覆盖层降级警告（PAGE_CAPTCHA_OVERLAY）；非 None 时结论 JSON 带标注
    warning: dict[str, Any] | None = None
    conclusion: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    history: list[dict[str, Any]] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES


class TaskRegistry:
    """内存任务注册表 + SSE 事件广播中心。"""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}

    def create(self, url: str) -> TaskRecord:
        """登记新任务（初始态 Pending），并把 state Pending 事件写入历史供回放。"""
        record = TaskRecord(task_id=uuid.uuid4().hex, url=url)
        self._tasks[record.task_id] = record
        logger.info("任务登记 task_id=%s url=%s", record.task_id, url)
        self.emit(record.task_id, "state", {"status": "Pending", "detail": None})
        return record

    def get(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def update(self, task_id: str, **fields: Any) -> TaskRecord | None:
        """回写注册表字段（Supervisor 输出 State 的落点）。"""
        record = self._tasks.get(task_id)
        if record is None:
            return None
        for key, value in fields.items():
            if not hasattr(record, key):
                raise AttributeError(f"TaskRecord 无字段 {key!r}")
            setattr(record, key, value)
        record.updated_at = _utcnow()
        return record

    def emit(self, task_id: str, event: str, data: dict[str, Any]) -> None:
        """广播一条 SSE 事件：写历史（断线回放源）+ 扇出全部订阅队列 + 落日志。"""
        record = self._tasks.get(task_id)
        if record is None:
            logger.warning("emit 命中未知任务 task_id=%s event=%s（已丢弃）", task_id, event)
            return
        envelope = {"event": event, "data": data}
        record.history.append(envelope)
        record.updated_at = _utcnow()
        for queue in list(record.subscribers):
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:  # 防御：订阅者停滞不阻断广播
                logger.warning("订阅队列已满 task_id=%s（丢弃一条 %s）", task_id, event)
        logger.info("SSE 事件 task_id=%s event=%s data=%s", task_id, event, data)

    def subscribe(self, task_id: str) -> tuple[list[dict[str, Any]], asyncio.Queue] | None:
        """订阅任务：返回（回放历史快照, 实时队列）；未知任务返回 None。"""
        record = self._tasks.get(task_id)
        if record is None:
            return None
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        record.subscribers.append(queue)
        return list(record.history), queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        record = self._tasks.get(task_id)
        if record is not None and queue in record.subscribers:
            record.subscribers.remove(queue)

    def snapshot(self, task_id: str) -> dict[str, Any] | None:
        """GET /api/task/{id} 快照补拉数据源（架构 §1.1 端点表）。"""
        record = self._tasks.get(task_id)
        if record is None:
            return None
        return {
            "task_id": record.task_id,
            "url": record.url,
            "status": record.status,
            "status_detail": record.status_detail,
            "progress": record.progress,
            "payload": record.payload,
            "warning": record.warning,
            "conclusion": record.conclusion,
            "receipt": record.receipt,
            "error": record.error,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    def clear(self) -> None:
        """清空全部任务（测试隔离用）。"""
        self._tasks.clear()
