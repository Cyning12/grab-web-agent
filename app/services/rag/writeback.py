"""模拟回填 Tool Node（m4 末节点 · PRD §5.3 · SPEC FP-4 / A5）。

V1 仅模拟回填（非范围：真实 OA/CRM/Jira 审批流 · PRD §9.3 V2.0+）：
- InMemoryOAEndpoint：内存模拟端点，成功桩返回 200 + 工单号；fail_status=500 即 500 桩；
- MockWritebackClient：POST 结论 JSON 到端点并捕获回调（成功/失败/工单号）→ Receipt。
回填失败不丢结论，仅回执标失败原因（SPEC FP-4），终态 Done(回填失败)。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.services.rag.schemas import Conclusion, Receipt

_logger = logging.getLogger(__name__)


@dataclass
class OAResponse:
    """模拟内部系统回调。"""

    http_status: int
    ticket_id: str | None = None
    reason: str | None = None


class InMemoryOAEndpoint:
    """内存模拟 OA 端点（可注入桩：默认成功桩；fail_status=500 为 500 桩）。

    issued_tickets 记录全量已发工单号，供闭环断言（ticket_id 与回调一致 · SPEC A5）。
    """

    def __init__(self, fail_status: int | None = None, fail_reason: str = "模拟内部系统内部错误") -> None:
        self.fail_status = fail_status
        self.fail_reason = fail_reason
        self.issued_tickets: list[str] = []
        self.received: list[dict] = []

    def handle_post(self, conclusion: dict) -> OAResponse:
        self.received.append(conclusion)
        if self.fail_status is not None:
            _logger.warning("模拟回填失败桩：HTTP %d（%s）", self.fail_status, self.fail_reason)
            return OAResponse(http_status=self.fail_status, reason=self.fail_reason)
        ticket_id = f"MOCK-{uuid.uuid4().hex[:8].upper()}"
        self.issued_tickets.append(ticket_id)
        return OAResponse(http_status=200, ticket_id=ticket_id)


class MockWritebackClient:
    """模拟回填客户端：推送结论 JSON，捕获回调状态（成功/失败/工单号）。"""

    def __init__(self, endpoint: InMemoryOAEndpoint | None = None) -> None:
        self.endpoint = endpoint or InMemoryOAEndpoint()

    def post(self, conclusion: Conclusion) -> Receipt:
        resp = self.endpoint.handle_post(conclusion.model_dump())
        if resp.http_status == 200 and resp.ticket_id:
            _logger.info("模拟回填成功：工单号 %s", resp.ticket_id)
            return Receipt(status="success", ticket_id=resp.ticket_id, reason=None, mock=True)
        reason = resp.reason or f"HTTP {resp.http_status}"
        _logger.warning("模拟写入失败：%s", reason)
        return Receipt(status="failed", ticket_id=None, reason=reason, mock=True)
