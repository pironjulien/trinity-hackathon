"""
CORPUS/SOMA/IMMUNE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: IMMUNE SYSTEM (LE SYSTÈME IMMUNITAIRE) 🛡️
PURPOSE: Health Check & Diagnostics via Angel Guardian.
         Délègue les stats système à Angel (source unique de vérité).
         Fallback local si Angel temporairement indisponible.
══════════════════════════════════════════════════════════════════════════════
"""

import psutil
from loguru import logger
from corpus.brain.hormones import hormones
from corpus.brain.instinct import instinct


class ImmuneSystem:
    async def check_vitals(self) -> dict:
        """Scan complet des constantes vitales via metrics.bin (Single Source of Truth)."""
        try:
            # Primary: Read from metrics.bin (written by metrics_bridge)
            from corpus.dna.genome import MEMORIES_DIR
            import struct

            metrics_file = MEMORIES_DIR / "state" / "metrics.bin"
            if metrics_file.exists() and metrics_file.stat().st_size == 96:
                with open(metrics_file, "rb") as f:
                    data = struct.unpack("dddddddddddd", f.read(96))
                # data: (sys_cpu, sys_ram, sys_disk, angel_cpu, angel_ram,
                #        trinity_cpu, trinity_ram, ag_cpu, ag_ram, ubuntu_cpu, ubuntu_ram, timestamp)
                report = {
                    "cpu": float(data[0]),
                    "memory": float(data[1]),
                    "disk": float(data[2]),
                    "details": {
                        "angel": {"cpu": float(data[3]), "ram": float(data[4])},
                        "trinity": {"cpu": float(data[5]), "ram": float(data[6])},
                        "ag": {"cpu": float(data[7]), "ram": float(data[8])},
                        "ubuntu": {"cpu": float(data[9]), "ram": float(data[10])},
                    },
                    "source": "metrics_bridge",
                    "status": "HEALTHY",
                    "emotions": hormones.get_state(),
                }
            else:
                raise FileNotFoundError("metrics.bin missing or invalid")

        except Exception as e:
            # Fallback: Local psutil (metrics_bridge temporarily unavailable)
            logger.warning(f"🛡️ [IMMUNE] Metrics unavailable, using local fallback: {e}")
            report = {
                "cpu": psutil.cpu_percent(interval=0.1),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent
                if hasattr(psutil.disk_usage("/"), "percent")
                else 0,
                "source": "local_fallback",
                "status": "HEALTHY",
                "emotions": hormones.get_state(),
            }

        # Diagnostics (same logic regardless of source)
        if report["disk"] > 90:
            report["status"] = "CRITICAL: DISK FULL"
            logger.critical(f"🛡️ [IMMUNE] DISK CRITICAL ({report['disk']}%)")
            # Trigger Instinct (Survival Mode)
            severity = (report["disk"] - 90) / 10.0  # 90% -> 0.0, 100% -> 1.0
            await instinct.sense_threat(
                "resource_pressure", severity=max(0.1, severity)
            )

        elif report["memory"] > 90:
            report["status"] = "WARNING: HIGH MEMORY"
            logger.warning(f"🛡️ [IMMUNE] HIGH MEMORY ({report['memory']}%)")
            # Trigger Instinct
            severity = (report["memory"] - 90) / 10.0
            await instinct.sense_threat(
                "resource_pressure", severity=max(0.1, severity)
            )

            # 3. Cloud Watch (Multi-Cloud Status)
            from corpus.soma.sentinel import cloud_watch

            try:
                report["clouds"] = await cloud_watch.get_global_status()
            except Exception:
                report["clouds"] = []

        return report

    async def scan(self) -> bool:
        """
        Lance une analyse du système immunitaire (Lint & Types).
        Remplace l'ancien workflow CI 'Trinity CI'.
        """
        import subprocess

        logger.info("🛡️ [IMMUNE] Scanning Codebase (Ruff + Pyright)...")

        try:
            # 1. Ruff (Lint)
            logger.info("🧹 [IMMUNE] Linting (Ruff)...")
            subprocess.run(["uv", "run", "ruff", "check", "."], check=True)

            # 2. Pyright (Types) - Split to avoid OOM
            logger.info("🧬 [IMMUNE] Type Check (Pyright)...")

            # Check Angel (Supervisor)
            subprocess.run(["uv", "run", "pyright", "angel.py"], check=True)

            # Check Corpus (Brain)
            subprocess.run(["uv", "run", "pyright", "corpus/brain"], check=True)

            # Check Corpus (Soma - Plugins/Immune)
            subprocess.run(["uv", "run", "pyright", "corpus/soma"], check=True)

            # Check Jobs
            subprocess.run(["uv", "run", "pyright", "jobs"], check=True)

            logger.info("✅ [IMMUNE] System Healthy. No pathogens found.")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ [IMMUNE] Pathogen detected: {e}")
            return False
        except Exception as e:
            logger.error(f"💥 [IMMUNE] Scan critical failure: {e}")
            return False


immune = ImmuneSystem()
