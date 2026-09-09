"""对外子图统一错误（错误码词汇表对齐架构 §1.5 状态机迁移触发表）。"""

from typing import Any


class AcquisitionError(Exception):
    """对外子图错误基类；code 即 §1.5 error 事件 code。"""

    code = "ACQUISITION_FAILED"
    retryable = True
    user_message = "采集失败，请稍后重试"

    def __init__(self, message: str = "", **context: Any) -> None:
        super().__init__(message or self.user_message)
        self.context = context


class UrlRejected(AcquisitionError):
    """n1：非法目标 URL（非 http/https、file://、内网地址段）。"""

    code = "URL_REJECTED"
    user_message = "目标 URL 不被允许"


class FetchTimeout(AcquisitionError):
    """n2：Playwright 超时阈值内未完成渲染。"""

    code = "FETCH_TIMEOUT"
    user_message = "目标页面抓取超时，请稍后重试"


class FetchFailed(AcquisitionError):
    """n2：浏览器不可用 / 导航失败等非超时抓取异常。"""

    code = "FETCH_FAILED"
    user_message = "目标页面抓取失败，请稍后重试"


class AntiBotDetected(AcquisitionError):
    """n2：反爬拦截（403 / 验证码 / 验证页重定向）。"""

    code = "ANTI_BOT"
    user_message = "目标站点拒绝访问（反爬拦截）"


class EmbedError(AcquisitionError):
    """n5：Embedding 服务调用失败。"""

    code = "EMBED_FAILED"
    user_message = "向量化失败，请稍后重试"


class PayloadInvalid(AcquisitionError):
    """n6：组装的 Payload 未通过 §1.5 Schema 校验（按构造不应发生）。"""

    code = "CONTRACT_VIOLATION"
    retryable = False
    user_message = "数据契约异常"


def make_error(exc: AcquisitionError, node: str) -> dict[str, Any]:
    """把异常转成 state/SSE 共用的 error dict（含用户可见文案）。"""
    return {
        "code": exc.code,
        "message": str(exc),
        "user_message": exc.user_message,
        "retryable": exc.retryable,
        "node": node,
        **{k: v for k, v in exc.context.items() if isinstance(v, (str, int, bool))},
    }
