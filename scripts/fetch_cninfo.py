"""cninfo 财报语料抓取脚本（人决 D6 / D6-修订兑现）。

按上市编号裸 6 位从巨潮资讯公告查询 API 抓取定期报告（年报/半年报）PDF，
落盘 company/<裸6位>/，供对内子图（Internal RAG · pypdf + FAISS）直接消费。

用法：
    python -m scripts.fetch_cninfo 000858 300810
    python -m scripts.fetch_cninfo sz000858 sh600519   # 前缀写法自动归一
    python -m scripts.fetch_cninfo 000858 --limit 3    # 每公司最新 3 份

配置（环境变量）：
    CNINFO_LIMIT     每公司抓取份数（默认 2，--limit 优先）
    CNINFO_INTERVAL  请求间隔秒数（默认 1.0，礼貌抓取）
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from pypdf import PdfReader

TOP_SEARCH_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
HIS_ANNOUNCEMENT_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC_BASE_URL = "http://static.cninfo.com.cn/"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# 定期报告类目：年报 + 半年报
REPORT_CATEGORY = "category_ndbg_szsh;category_bndbg_szsh"

# 标题剔除词：摘要/英文版/更新前/已取消等不作为语料正文
EXCLUDE_KEYWORDS = ("摘要", "英文", "更新前", "已取消", "取消")

MAX_RETRIES = 2  # 单文件失败后最多重试 2 次

CODE_PATTERN = re.compile(r"^(?:sz|sh|bj)?(\d{6})$", re.IGNORECASE)
PERIOD_PATTERN = re.compile(r"(\d{4})\s*年\s*(半)?\s*年度")
UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def normalize_code(raw: str) -> str:
    """归一化上市编号为裸 6 位；非法编号抛 ValueError（不建目录）。"""
    m = CODE_PATTERN.match(raw.strip())
    if not m:
        raise ValueError(f"非法上市编号: {raw!r}（接受 000858 / sz000858 / SH600519 等写法）")
    return m.group(1)


def make_client() -> httpx.Client:
    """离线直连客户端：不读代理环境变量，带浏览器 UA。"""
    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=30.0,
        trust_env=False,
        follow_redirects=True,
    )


def _column_for(code: str) -> str:
    """按编号段推断 cninfo column 参数（6 开头沪，其余深/京按 szse 实测可用）。"""
    return "sse" if code.startswith("6") else "szse"


def lookup_org_id(client: httpx.Client, code: str) -> str | None:
    """topSearch 建议接口拿 orgId；编号不存在返回 None。"""
    resp = client.post(TOP_SEARCH_URL, data={"keyWord": code, "maxSecNum": "10"})
    resp.raise_for_status()
    for item in resp.json():
        if item.get("code") == code:
            return item.get("orgId")
    return None


@dataclass
class Report:
    title: str
    adjunct_url: str
    announcement_time: int

    @property
    def period_key(self) -> str:
        """报告期键（如 2025年度 / 2026半年度），用于去重取最新。"""
        m = PERIOD_PATTERN.search(self.title)
        if not m:
            return self.title
        return f"{m.group(1)}{'半年度' if m.group(2) else '年度'}"


def query_reports(client: httpx.Client, code: str, org_id: str, limit: int) -> list[Report]:
    """查询定期报告列表：类目过滤 + 标题剔除 + 按报告期去重取最新 limit 份。"""
    resp = client.post(
        HIS_ANNOUNCEMENT_URL,
        data={
            "pageNum": "1",
            "pageSize": "30",
            "column": _column_for(code),
            "tabName": "fulltext",
            "plate": "",
            "stock": f"{code},{org_id}",
            "searchkey": "",
            "secid": "",
            "category": REPORT_CATEGORY,
            "trade": "",
            "seDate": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        },
    )
    resp.raise_for_status()
    announcements = (resp.json() or {}).get("announcements") or []

    latest_by_period: dict[str, Report] = {}
    for item in announcements:
        title = re.sub(r"<[^>]+>", "", item.get("announcementTitle") or "").strip()
        if not PERIOD_PATTERN.search(title):
            continue
        if any(kw in title for kw in EXCLUDE_KEYWORDS):
            continue
        report = Report(
            title=title,
            adjunct_url=item.get("adjunctUrl") or "",
            announcement_time=int(item.get("announcementTime") or 0),
        )
        prev = latest_by_period.get(report.period_key)
        if prev is None or report.announcement_time > prev.announcement_time:
            latest_by_period[report.period_key] = report

    reports = sorted(latest_by_period.values(), key=lambda r: r.announcement_time, reverse=True)
    return reports[:limit]


def _safe_filename(title: str) -> str:
    return UNSAFE_FILENAME_CHARS.sub("_", title) + ".pdf"


def _validate_pdf(path: Path) -> bool:
    """pypdf 可打开且能提取文本视为有效；否则删除并视为坏文件。"""
    try:
        reader = PdfReader(str(path))
        if not reader.pages:
            return False
        reader.pages[0].extract_text()
        return True
    except Exception:
        return False


def download_report(client: httpx.Client, report: Report, dest_dir: Path) -> tuple[bool, str]:
    """下载单份 PDF；失败重试 ≤2 次；坏文件删除。返回 (成功?, 信息)。"""
    dest = dest_dir / _safe_filename(report.title)
    url = STATIC_BASE_URL + report.adjunct_url.lstrip("/")
    last_err = ""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            if _validate_pdf(dest):
                return True, dest.name
            dest.unlink(missing_ok=True)
            last_err = "PDF 损坏（pypdf 无法解析），已删除"
        except Exception as exc:  # noqa: BLE001 - 单文件失败不中断整批
            last_err = f"{type(exc).__name__}: {exc}"
            dest.unlink(missing_ok=True)
        if attempt < MAX_RETRIES:
            time.sleep(0.5)
    return False, f"{report.title} -> {last_err}"


def fetch_company(
    client: httpx.Client,
    code: str,
    company_root: Path,
    limit: int,
    interval: float,
) -> tuple[int, list[str]]:
    """抓单家公司：返回 (成功份数, 失败清单)。"""
    failures: list[str] = []
    org_id = lookup_org_id(client, code)
    dest_dir = company_root / code
    if org_id is None:
        print(f"[{code}] 编号不存在或未在 cninfo 收录，未找到定期报告")
        return 0, [f"{code}: 编号不存在"]
    time.sleep(interval)

    reports = query_reports(client, code, org_id, limit)
    if not reports:
        print(f"[{code}] 未找到定期报告（年报/半年报）")
        return 0, [f"{code}: 未找到定期报告"]

    dest_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for report in reports:
        time.sleep(interval)
        success, info = download_report(client, report, dest_dir)
        if success:
            ok += 1
            print(f"[{code}] ✔ {info}")
        else:
            failures.append(f"{code}: {info}")
            print(f"[{code}] ✘ {info}")
    return ok, failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.fetch_cninfo",
        description="从巨潮资讯抓取定期报告（年报/半年报）PDF 到 company/<裸6位>/",
    )
    parser.add_argument("codes", nargs="+", help="上市编号（000858 / sz000858 均可，归一为裸 6 位）")
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.environ.get("CNINFO_LIMIT", "2")),
        help="每公司抓取最新份数（默认 2，env CNINFO_LIMIT）",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("CNINFO_INTERVAL", "1.0")),
        help="请求间隔秒数（默认 1.0，env CNINFO_INTERVAL）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("company"),
        help="语料根目录（默认 company/）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, client: httpx.Client | None = None) -> int:
    args = parse_args(argv)

    codes: list[str] = []
    for raw in args.codes:
        try:
            codes.append(normalize_code(raw))
        except ValueError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 2

    total_ok = 0
    all_failures: list[str] = []
    own_client = client is None
    client = client or make_client()
    try:
        for code in codes:
            ok, failures = fetch_company(client, code, args.out_dir, args.limit, args.interval)
            total_ok += ok
            all_failures.extend(failures)
    finally:
        if own_client:
            client.close()

    print(f"\n汇总：成功 {total_ok} 份；失败 {len(all_failures)} 项")
    for item in all_failures:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
