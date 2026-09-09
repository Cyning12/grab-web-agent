"""资源监控与降级（铁律三 · SPEC A7 / FP-6）。

A7 钉死值：容器限额 CPU=2 / 内存=4096MB，每 1s 采样 RSS，峰值 ≤ 3072MB，采样原始数据留档。
macOS 无 /proc：优先 psutil，缺库时回退 ps -o rss=（等效采样 · task residual_risks ③）。
唯一允许的降级手段 = 截断 Top-K（SPEC FP-6），阈值低于 A7 上限以留降级余量。
"""

import logging
import os
import subprocess
import threading
import time

_logger = logging.getLogger(__name__)

# A7 峰值上限（钉死 · 审计观察项①）
A7_RSS_PEAK_LIMIT_MB: float = float(os.getenv("RAG_RSS_PEAK_LIMIT_MB", "3072"))
# 降级触发阈值（逼近上限即截断 Top-K，默认 2560MB < 3072MB 留余量）
RAG_RSS_DEGRADE_MB: float = float(os.getenv("RAG_RSS_DEGRADE_MB", "2560"))


def current_rss_mb(pid: int | None = None) -> float:
    """读取进程当前 RSS（MB）。psutil 优先；缺失时回退 ps（macOS 等效，无 /proc）。"""
    pid = pid or os.getpid()
    try:
        import psutil

        return psutil.Process(pid).memory_info().rss / (1024 * 1024)
    except ImportError:
        out = subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)], text=True)
        return float(out.strip()) / 1024  # ps 输出单位 KB


class RssSampler:
    """后台线程周期采样本进程 RSS（默认 interval=1s，对齐 A7「每 1s 采样」测量方式）。

    用法：sampler.start() → 跑任务 → sampler.stop() → sampler.samples / sampler.peak_mb。
    """

    def __init__(self, interval_s: float = 1.0) -> None:
        self.interval_s = interval_s
        self.samples: list[float] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.samples.append(current_rss_mb())
            time.sleep(self.interval_s)

    def start(self) -> "RssSampler":
        self.samples.clear()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        # 收尾补一刀，保证任务极短时也有样本
        self.samples.append(current_rss_mb())

    @property
    def peak_mb(self) -> float:
        return max(self.samples) if self.samples else 0.0
