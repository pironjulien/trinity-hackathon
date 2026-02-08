#!/usr/bin/env python3
"""
Metrics Bridge (SOTA 2026 Refactored)
======================================
Standalone service for zero-latency system monitoring.
Writes packed binary data to a memory-mapped file.

Structure (struct.pack 'dddddddddddd') - 12 doubles = 96 bytes:
- 0:  System CPU (%)
- 8:  System RAM (%)
- 16: System DISK (%)
- 24: Angel CPU (%)
- 32: Angel RAM (MB)
- 40: Trinity CPU (%)
- 48: Trinity RAM (MB)
- 56: Chrome CPU (%)
- 64: Chrome RAM (MB)
- 72: Antigravity CPU (%)
- 80: Antigravity RAM (MB)
- 88: Timestamp (epoch)
"""

import time
import struct
import psutil
from pathlib import Path
from typing import Dict, Set, Tuple

# Config
BASE_DIR = Path(__file__).parent.resolve()
STATE_DIR = BASE_DIR / "memories" / "state"
METRICS_FILE = STATE_DIR / "metrics.bin"
UPDATE_INTERVAL = 0.987  # F16 Fibonacci (987ms)
FILE_SIZE = 96  # 12 doubles * 8 bytes (Added Ubuntu)


class MetricsEngine:
    """Handles process detection and resource calculation."""

    def __init__(self):
        self.process_cache: Dict[int, psutil.Process] = {}

    def gather(self) -> Tuple[float, ...]:
        """Gather all metrics in a single iteration."""
        # System Stats
        sys_cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        sys_ram_pct = mem.percent
        sys_ram_total_mb = mem.total / (1024 * 1024)
        sys_disk = psutil.disk_usage("/").percent

        # Breakdown Init
        angel_cpu, angel_ram = 0.0, 0.0
        trinity_cpu, trinity_ram = 0.0, 0.0
        ag_cpu, ag_ram = 0.0, 0.0

        current_pids: Set[int] = set()

        # Process Iteration
        for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
            try:
                pid = proc.pid
                current_pids.add(pid)

                # Cache Handling
                if pid in self.process_cache:
                    p = self.process_cache[pid]
                else:
                    p = proc
                    self.process_cache[pid] = p

                # Data Extraction
                name = (proc.info.get("name") or "").lower()
                cmd_list = proc.info.get("cmdline") or []
                cmd = " ".join(cmd_list).lower()
                mem_info = proc.info.get("memory_info")
                mem_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0

                # CPU Call (Stateful)
                cpu_usage = p.cpu_percent(interval=None)

                # Classification Logic
                if "angel.py" in cmd:
                    angel_cpu += cpu_usage
                    angel_ram += mem_mb

                elif "trinity.py" in cmd:
                    trinity_cpu += cpu_usage
                    trinity_ram += mem_mb

                elif (
                    "code" in name
                    or "vscode" in name
                    or "antigravity" in cmd
                    or "language_server" in name
                ):
                    ag_cpu += cpu_usage
                    ag_ram += mem_mb

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Cache Cleanup
        for pid in list(self.process_cache.keys()):
            if pid not in current_pids:
                del self.process_cache[pid]

        # Calculate Ubuntu (Remainder)
        # Note: psutil.cpu_percent is global, sum(proc_cpus) can exceed it on multicore or lag.
        # We clamp to 0 to avoid confusing negatives.

        # CPU Remainder
        # Used Logic: System Total - (Angel + Trinity + Agent)
        ubuntu_cpu = max(0.0, sys_cpu - (angel_cpu + trinity_cpu + ag_cpu))

        # RAM Remainder (in MB)
        # System Used MB = (Percent * Total)
        sys_used_mb = (sys_ram_pct / 100.0) * sys_ram_total_mb
        ubuntu_ram = max(0.0, sys_used_mb - (angel_ram + trinity_ram + ag_ram))

        return (
            sys_cpu,
            sys_ram_pct,
            sys_disk,
            angel_cpu,
            angel_ram,
            trinity_cpu,
            trinity_ram,
            ag_cpu,
            ag_ram,
            ubuntu_cpu,
            ubuntu_ram,
        )


class MetricsBridge:
    """Handles memory mapping and binary broadcasting."""

    def __init__(self):
        self.engine = MetricsEngine()
        self._ensure_file()

    def _ensure_file(self):
        """SOTA 2026: Atomic Init - Only create/truncate if invalid."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        should_create = False
        if not METRICS_FILE.exists():
            should_create = True
            print("📝 File missing. Creating new.")
        elif METRICS_FILE.stat().st_size != FILE_SIZE:
            should_create = True
            print(
                f"⚠️ File size mismatch ({METRICS_FILE.stat().st_size} != {FILE_SIZE}). Recreating."
            )

        if should_create:
            with open(METRICS_FILE, "wb") as f:
                f.write(b"\x00" * FILE_SIZE)
        else:
            print("✅ File exists and valid. Attaching.")

    def run(self):
        print("🚀 Metrics Bridge (SOTA 2026 - Atomic Write) Starting...")
        print(f"⏱️  Interval: {UPDATE_INTERVAL * 1000:.0f}ms")

        # Ensure file exists with correct size
        self._ensure_file()
        print("✅ Atomic Write Mode Active. Broadcasting...")

        while True:
            try:
                metrics = self.engine.gather()
                timestamp = time.time()

                # Pack: 11 metrics + timestamp = 12 doubles
                data = struct.pack("dddddddddddd", *metrics, timestamp)

                # SOTA 2026 FIX: r+b mode avoids truncation (0-byte race condition)
                # We seek to 0 to overwrite the existing 96 bytes in place.
                with open(METRICS_FILE, "r+b") as f:
                    f.write(data)

                time.sleep(UPDATE_INTERVAL)

            except KeyboardInterrupt:
                print("\n🛑 Stopping Metrics Bridge")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(1)


if __name__ == "__main__":
    bridge = MetricsBridge()
    bridge.run()
