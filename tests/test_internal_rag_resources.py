"""A7 资源上限测试（审计 R1 观察项① · 已钉死）。

测量方式（task 验收 A7 行）：任务运行期间周期采样对内进程 RSS，取全程峰值，
阈值 ≤ 3072MB，采样原始数据留档。本机 macOS 无 /proc 且 docker 不可用 → 以 psutil
采样为等效（task residual_risks ③ 允许），采样间隔收紧至 50ms 以覆盖短任务全程
（验收语义「每 1s 采样」为上限要求，更密采样更严格）。原始数据落盘：
docs/harness/invokes/by-task/internal_rag_subgraph/rss_samples_internal_rag.json
"""

import json
from pathlib import Path

from internal_rag_fakes import make_deps, make_payload
from app.graphs.internal_rag import run_internal_rag
from app.services.rag.resources import A7_RSS_PEAK_LIMIT_MB, RssSampler

ARTIFACT = (
    Path(__file__).resolve().parents[1]
    / "docs/harness/invokes/by-task/internal_rag_subgraph/rss_samples_internal_rag.json"
)


def test_a7_rss_peak_within_3072mb_full_task():
    sampler = RssSampler(interval_s=0.05).start()
    try:
        for _ in range(3):  # 连续完整任务（Mock Payload → 结论 → 模拟回填）
            result = run_internal_rag(make_payload(), deps=make_deps())
            assert "error" not in result
            assert result["receipt"].status == "success"
    finally:
        sampler.stop()

    assert sampler.samples, "采样为空：A7 测量未执行"
    peak = sampler.peak_mb
    ARTIFACT.write_text(
        json.dumps(
            {
                "method": "psutil（macOS 无 /proc、docker 不可用 → 等效采样 · task residual_risks ③）",
                "interval_s": 0.05,
                "sample_count": len(sampler.samples),
                "peak_mb": round(peak, 2),
                "limit_mb": A7_RSS_PEAK_LIMIT_MB,
                "samples_mb": [round(s, 2) for s in sampler.samples],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    assert peak <= A7_RSS_PEAK_LIMIT_MB, (
        f"A7 超限：RSS 峰值 {peak:.0f}MB > {A7_RSS_PEAK_LIMIT_MB:.0f}MB"
    )
