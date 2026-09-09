"""n1 validate_url：目标 URL 协议白名单 + SSRF 内网段拒绝（SPEC R3 安全约束）。

规则（架构 §1.3 n1 三行式 / task 范围 SSRF 行）：
- 仅允许 http / https；file://、ftp://、无 scheme 一律拒绝；
- hostname 为 IP 字面量时，拒绝环回 / 私网 / 链路本地 / 保留段
  （覆盖 10.x、172.16.x、192.168.x、127.x、169.254.x、::1 等）；
- hostname 为域名时拒绝 localhost 与 *.local / *.internal，不做 DNS 解析
  （DNS rebinding 防护属 V2 反爬/代理池范畴，见 task 非范围）。
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

from app.services.acquisition.errors import UrlRejected

logger = logging.getLogger(__name__)

_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}
_BLOCKED_SUFFIXES = (".local", ".internal", ".lan", ".corp")


def _is_forbidden_ip(host: str) -> bool:
    """IP 字面量命中内网/环回/保留段即 True（SSRF 防护）。

    inet_aton 归一化兼容 127.1 / 0x7f.1 / 纯十进制等短写形态。
    """
    candidate = host.strip("[]")
    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        try:
            ip = ipaddress.ip_address(socket.inet_aton(candidate))
        except (OSError, ValueError):
            return False
    return bool(
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_target_url(url: str) -> str:
    """校验通过返回规范化 URL；违例抛 UrlRejected 并落 SSRF 拦截日志。"""
    candidate = (url or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https"):
        logger.warning("SSRF 拦截：非法协议 url=%r", candidate)
        raise UrlRejected(f"仅允许 http/https 协议：{candidate!r}", url=candidate)
    host = parsed.hostname
    if not host:
        logger.warning("SSRF 拦截：缺 hostname url=%r", candidate)
        raise UrlRejected(f"URL 缺少 hostname：{candidate!r}", url=candidate)
    host_l = host.lower()
    if (
        host_l in _BLOCKED_HOSTNAMES
        or host_l.endswith(_BLOCKED_SUFFIXES)
        or _is_forbidden_ip(host_l)
    ):
        logger.warning("SSRF 拦截：内网/环回地址 url=%r host=%r", candidate, host_l)
        raise UrlRejected(f"目标 URL 指向内网/环回地址：{candidate!r}", url=candidate)
    return candidate
