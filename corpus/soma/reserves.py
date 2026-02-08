"""
CORPUS/SOMA/TREASURY.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: TREASURY (TRÉSORERIE) 💰
PURPOSE: Financial awareness for Trinity's survival.
         Tracks GCP credits, job revenues, and overall budget.

         DATA SOURCES:
         - GCP Credits: Cloud Billing API (auto) OR manual fallback (budget.json)
         - Trader profits: portfolio.json (auto-sync)
         - YouTube/Influencer: manual (budget.json)
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime
from typing import Dict, Optional
from loguru import logger

from corpus.dna.genome import MEMORIES_DIR
from corpus.soma.cells import load_json, save_json

# ══════════════════════════════════════════════════════════════════════════════
# CACHE LAYER (Standard 350 - Anti-BigQuery Storm)
# ══════════════════════════════════════════════════════════════════════════════
_BQ_CACHE_TTL: float = 180.0  # 3 minutes - align with panel refresh patterns
_HORMONE_CACHE_TTL: float = (
    86400.0  # 24h - prevent cortisol accumulation (Standard 350.1)
)


class Treasury:
    """
    Trinity's Financial Awareness System.
    Provides a unified view of her economic survival.
    """

    def __init__(self):
        self.budget_path = MEMORIES_DIR / "trinity" / "budget.json"
        self.trader_portfolio_path = MEMORIES_DIR / "trader" / "portfolio.json"
        self.trader_state_path = MEMORIES_DIR / "trader" / "state.json"
        # Cache for BigQuery costs (Standard 350)
        self._bq_cache: dict = {}
        self._bq_cache_timestamp: float = 0.0
        # Cache for hormonal feedback (Standard 350 - Anti-Spam)
        self._hormone_cache_timestamp: float = 0.0

    def _get_trader_profit(self) -> float:
        """Get total trader profit from portfolio.json."""
        try:
            portfolio = load_json(self.trader_portfolio_path, default={})
            return portfolio.get("performance", {}).get("total_profit", 0.0)
        except Exception:
            logger.warning("💰 Trader read fail")
            return 0.0

    def _get_initial_capital(self) -> float:
        """Get initial capital from budget.json or default."""
        try:
            budget = load_json(self.budget_path, default={})
            # Tenter de lire capital_depart -> trader
            return budget.get("capital_depart", {}).get("trader", 0.0)
        except Exception:
            return 0.0

    def get_financial_summary(self) -> Dict:
        """
        Get complete financial summary for Trinity's consciousness.

        Returns:
            Dict with capital_trading, gcp_credits, total_resources
        """
        # 1. Trading Capital (auto from trader files)
        trader_profit = self._get_trader_profit()
        initial_capital = self._get_initial_capital()
        capital_trading = initial_capital + trader_profit

        # 2. GCP Credits (from granular manual tracking)
        gcp_credits = self._get_gcp_credits()

        # 3. Other revenues (manual from budget.json)
        budget = load_json(self.budget_path, default={})
        revenus = budget.get("revenus", {})
        youtube_profit = revenus.get("youtuber", {}).get("profit_cumule", 0)
        influencer_profit = revenus.get("influencer", {}).get("profit_cumule", 0)

        # 4. Total resources
        total_cash = capital_trading + youtube_profit + influencer_profit
        total_credits = gcp_credits.get("total", 0)
        total_resources = total_cash + total_credits

        # ——————————————————————————————————————————————————————————————————————————
        # HORMONAL FEEDBACK (Financial Proprioception - Standard 350: Low Intensity)
        # SOTA 2026: Cached + Persisted (Once Per Day Limit)
        # ——————————————————————————————————————————————————————————————————————————
        import time

        now = time.time()
        # 1. Short-term cache (30s) to prevent spam during rapid refreshes
        if (now - self._hormone_cache_timestamp) >= _HORMONE_CACHE_TTL:
            self._hormone_cache_timestamp = now
            try:
                from corpus.brain.hormones import hormones

                # 1. Survival Stress (Pauvreté) - ONCE PER DAY
                CRITICAL_THRESHOLD = 50.0
                if total_resources < CRITICAL_THRESHOLD:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    should_stress = False

                    # Load budget to check persistence
                    try:
                        budget_data = load_json(self.budget_path, default={})
                        internal_state = budget_data.get("_internal_state", {})
                        last_date = internal_state.get(
                            "last_low_resource_stress_date", ""
                        )

                        if last_date != today_str:
                            should_stress = True
                    except Exception:
                        # If read fails, default to stressing (safety) but don't crash
                        should_stress = True

                    if should_stress:
                        # "Je n'ai presque plus de ressources..."
                        hormones.stimulate("cortisol", 0.1)  # Was 0.5 (Standard 350)

                        # Persist today's date
                        try:
                            if "_internal_state" not in budget_data:
                                budget_data["_internal_state"] = {}
                            budget_data["_internal_state"][
                                "last_low_resource_stress_date"
                            ] = today_str
                            save_json(self.budget_path, budget_data)
                            logger.info(
                                f"💰 [FINANCE] Daily stress triggered for {today_str}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"💰 [FINANCE] Failed to persist stress date: {e}"
                            )

                # 2. Performance Feedback (Trading) - Kept on 30s cache (reactive)
                if trader_profit > 0:
                    # "Je suis rentable."
                    hormones.stimulate("dopamine", 0.2)
                elif trader_profit < 0:
                    # "Je perds de l'argent."
                    hormones.stimulate("cortisol", 0.05)  # Was 0.3 (Standard 350)

            except Exception as e:
                logger.warning(f"💰 Hormone fail: {e}")

        # 5. Calculate survival metrics (REAL DATA)
        burn_rate = self._calculate_daily_burn_rate()
        days_remaining = total_credits / burn_rate if burn_rate > 0 else 999

        return {
            "capital_trading": round(capital_trading, 2),
            "trader_profit": round(trader_profit, 2),
            "youtube_profit": round(youtube_profit, 2),
            "influencer_profit": round(influencer_profit, 2),
            "gcp_credits_details": gcp_credits.get("details", []),
            "gcp_total": round(total_credits, 2),
            "total_cash": round(total_cash, 2),
            "total_resources": round(total_resources, 2),
            "burn_rate": round(burn_rate, 2),
            "days_remaining": round(days_remaining, 1),
            "source": gcp_credits.get("source", "manual"),
            "last_updated": datetime.now().isoformat(),
        }

    def get_awakening_summary(self) -> str:
        """
        Get a concise summary for awakening context (Standard 418.7).
        Includes survival, costs, and infrastructure status.
        """
        summary = self.get_financial_summary()
        costs = self.get_cost_breakdown()
        vm = self.get_vm_status()

        credits_desc = ", ".join(
            [
                f"{c['nom']}: {c['valeur']:.0f}€"
                for c in summary["gcp_credits_details"]
                if c["valeur"] > 0
            ]
        )

        top_costs = (
            ", ".join(
                [f"{s['name']}: {s['cost']}€" for s in costs.get("services", [])[:2]]
            )
            if costs.get("services")
            else "N/A"
        )

        return (
            f"Survie: {summary['days_remaining']:.0f}j @ {summary['burn_rate']:.1f}€/j | "
            f"Crédits: {summary['gcp_total']:.0f}€ ({credits_desc}) | "
            f"VM: {vm.get('status', 'N/A')} ({vm.get('machine_type', 'N/A')}) | "
            f"Coûts Feb: {costs.get('total', 0):.2f}€ ({top_costs})"
        )

    def _fetch_bigquery_costs(self) -> Dict[str, float]:
        """
        Fetch precise costs from BigQuery billing export.
        Standard 350: Uses 3-minute cache to prevent API storms from panel polling.
        Returns: Dict { 'gen_app_builder': 12.50, 'dialogflow': 2.10, ... }
        """
        import time

        # ══════════════════════════════════════════════════════════════════════
        # CACHE CHECK (Standard 350 - Anti-Storm)
        # ══════════════════════════════════════════════════════════════════════
        now = time.time()
        if self._bq_cache and (now - self._bq_cache_timestamp) < _BQ_CACHE_TTL:
            # Silent cache hit - no logging, no stress
            return self._bq_cache

        # ══════════════════════════════════════════════════════════════════════
        # FRESH FETCH
        # ══════════════════════════════════════════════════════════════════════
        costs = {}
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
            from corpus.dna.secrets import vault

            # Cloud 1 Config Only (VM Host)
            config = {
                "project_id": "trinity2-482313",
                "dataset_id": "billing_data",
                "credentials_json": vault.GCP_1_CREDENTIALS_JSON,
            }

            try:
                creds = service_account.Credentials.from_service_account_info(
                    config["credentials_json"],
                    scopes=[
                        "https://www.googleapis.com/auth/bigquery",
                        "https://www.googleapis.com/auth/cloud-platform",
                    ],
                )
                client = bigquery.Client(
                    credentials=creds, project=config["project_id"]
                )

                project_id = config["project_id"]
                dataset_id = config["dataset_id"]

                # Find the export table
                query_table = f"""
                    SELECT table_name 
                    FROM `{project_id}.{dataset_id}.INFORMATION_SCHEMA.TABLES`
                    WHERE table_name LIKE 'gcp_billing_export_v1_%'
                    LIMIT 1
                """

                query_job = client.query(query_table)
                results = list(query_job.result())

                if not results:
                    logger.debug("💰 No BQ table")
                    return self._bq_cache or {}

                table_name = results[0].table_name
                full_table_id = f"{project_id}.{dataset_id}.{table_name}"

                # Determine start of current month dynamically
                start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")

                # Aggregate costs by service
                sql = f"""
                    SELECT 
                        service.description as service_name,
                        SUM(cost) as gross_cost
                    FROM `{full_table_id}`
                    WHERE usage_start_time >= '{start_date}'
                    GROUP BY 1
                    HAVING gross_cost > 0
                """

                query_job = client.query(sql)
                rows = query_job.result()

                for row in rows:
                    cost = float(row.gross_cost)
                    # All costs go to Cloud 1 Free Trial bucket
                    # No more distinction for Dialogflow/Discovery
                    key = "free_trial_cloud1"
                    costs[key] = costs.get(key, 0) + cost

            except Exception as e:
                # Handle Permission Errors gracefully
                error_str = str(e)
                if "403" in error_str and "Access Denied" in error_str:
                    logger.warning("💰 BQ perm denied")
                elif "403" in error_str and "billingEnabled" in error_str:
                    logger.warning("💰 BQ API off")
                else:
                    logger.warning("💰 BQ query fail")
                # Return stale cache on error
                return self._bq_cache or {}

            if costs:
                # Update cache
                self._bq_cache = costs
                self._bq_cache_timestamp = now
                total = sum(costs.values())
                logger.info(f"💰 FinOps: {total:.2f}€")
            return costs

        except Exception:
            logger.debug("💰 BQ global fail")
            return self._bq_cache or {}

    def _fetch_real_monthly_cost(self) -> float:
        """
        Fetch TOTAL cost for current month from BigQuery.
        Returns: Total EUR consumed this month.
        """
        import time

        # Cache check (reuse BQ cache TTL)
        now = time.time()
        if (
            hasattr(self, "_monthly_cost_cache")
            and (now - getattr(self, "_monthly_cost_cache_ts", 0)) < _BQ_CACHE_TTL
        ):
            return self._monthly_cost_cache

        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
            from corpus.dna.secrets import vault

            if not vault.GCP_1_CREDENTIALS_JSON:
                logger.debug("💰 No GCP creds")
                return 0.0

            creds = service_account.Credentials.from_service_account_info(
                vault.GCP_1_CREDENTIALS_JSON,
                scopes=[
                    "https://www.googleapis.com/auth/bigquery",
                    "https://www.googleapis.com/auth/cloud-platform",
                ],
            )
            client = bigquery.Client(credentials=creds, project="trinity2-482313")

            # Find export table
            query_table = """
                SELECT table_name 
                FROM `trinity2-482313.billing_data.INFORMATION_SCHEMA.TABLES`
                WHERE table_name LIKE 'gcp_billing_export_v1_%'
                LIMIT 1
            """
            results = list(client.query(query_table).result())
            if not results:
                logger.debug("💰 No BQ billing table")
                return 0.0

            table_name = results[0].table_name
            start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")

            # Get TOTAL cost for current month
            sql = f"""
                SELECT SUM(cost) as total_cost
                FROM `trinity2-482313.billing_data.{table_name}`
                WHERE usage_start_time >= '{start_date}'
            """
            rows = list(client.query(sql).result())
            total = float(rows[0].total_cost or 0) if rows else 0.0

            # Cache result
            self._monthly_cost_cache = total
            self._monthly_cost_cache_ts = now
            logger.info(f"💰 Month cost: {total:.2f}€")
            return total

        except Exception as e:
            logger.warning(f"💰 BQ monthly cost fail: {e}")
            return getattr(self, "_monthly_cost_cache", 0.0)

    def _calculate_daily_burn_rate(self) -> float:
        """
        Calculate daily burn rate from HISTORICAL consumption data (30-day rolling).
        Standard 418.8: Uses 30-day average to avoid early-month distortion.
        Fallback: Estimate based on t2d-standard-4 pricing (~4.5€/day)
        """
        import time

        # Cache check
        cache_key = "_burn_rate_cache"
        cache_ts_key = "_burn_rate_cache_ts"
        now = time.time()
        if (
            hasattr(self, cache_key)
            and (now - getattr(self, cache_ts_key, 0)) < _BQ_CACHE_TTL
        ):
            return getattr(self, cache_key)

        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
            from corpus.dna.secrets import vault

            if not vault.GCP_1_CREDENTIALS_JSON:
                return 5.5  # Fallback

            creds = service_account.Credentials.from_service_account_info(
                vault.GCP_1_CREDENTIALS_JSON,
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            client = bigquery.Client(credentials=creds, project="trinity2-482313")

            # Find billing table
            query_table = """
                SELECT table_name 
                FROM `trinity2-482313.billing_data.INFORMATION_SCHEMA.TABLES`
                WHERE table_name LIKE 'gcp_billing_export_v1_%'
                LIMIT 1
            """
            results = list(client.query(query_table).result())
            if not results:
                return 5.5

            table_name = results[0].table_name

            # Get 3-day average (excluding today for complete days only)
            sql = f"""
                SELECT 
                    SUM(cost) as total_cost,
                    COUNT(DISTINCT DATE(usage_start_time)) as days_count
                FROM `trinity2-482313.billing_data.{table_name}`
                WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
                  AND DATE(usage_start_time) < CURRENT_DATE()
            """
            rows = list(client.query(sql).result())

            if rows and rows[0].total_cost and rows[0].days_count:
                total = float(rows[0].total_cost)
                days = int(rows[0].days_count)
                daily_rate = total / max(1, days)

                # Cache
                setattr(self, cache_key, daily_rate)
                setattr(self, cache_ts_key, now)
                logger.info(
                    f"💰 Burn rate (3d avg): {daily_rate:.2f}€/day ({days} days, {total:.2f}€ total)"
                )
                return daily_rate
            else:
                fallback_rate = 5.5
                logger.debug(f"💰 Burn rate (fallback): {fallback_rate}€/day")
                return fallback_rate

        except Exception as e:
            logger.warning(f"💰 Burn rate calc fail: {e}")
            fallback_rate = 5.5
            return fallback_rate

    def get_cost_breakdown(self) -> Dict:
        """
        Get detailed cost breakdown by GCP service (Standard 418.4).
        Returns costs for current month grouped by service.
        """
        import time

        # Cache check
        cache_key = "_cost_breakdown_cache"
        cache_ts_key = "_cost_breakdown_cache_ts"
        now = time.time()
        if (
            hasattr(self, cache_key)
            and (now - getattr(self, cache_ts_key, 0)) < _BQ_CACHE_TTL
        ):
            return getattr(self, cache_key)

        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
            from corpus.dna.secrets import vault

            if not vault.GCP_1_CREDENTIALS_JSON:
                return {"services": [], "total": 0.0}

            creds = service_account.Credentials.from_service_account_info(
                vault.GCP_1_CREDENTIALS_JSON,
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            client = bigquery.Client(credentials=creds, project="trinity2-482313")

            # Find billing table
            query_table = """
                SELECT table_name 
                FROM `trinity2-482313.billing_data.INFORMATION_SCHEMA.TABLES`
                WHERE table_name LIKE 'gcp_billing_export_v1_%'
                LIMIT 1
            """
            results = list(client.query(query_table).result())
            if not results:
                return {"services": [], "total": 0.0}

            table_name = results[0].table_name
            start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")

            # Cost by service for current month
            sql = f"""
                SELECT 
                    service.description as service_name,
                    SUM(cost) as total_cost
                FROM `trinity2-482313.billing_data.{table_name}`
                WHERE usage_start_time >= '{start_date}'
                GROUP BY 1
                HAVING total_cost > 0.001
                ORDER BY 2 DESC
            """
            rows = list(client.query(sql).result())

            services = []
            total = 0.0
            for row in rows:
                cost = float(row.total_cost)
                services.append({"name": row.service_name, "cost": round(cost, 2)})
                total += cost

            result = {"services": services, "total": round(total, 2)}

            # Cache
            setattr(self, cache_key, result)
            setattr(self, cache_ts_key, now)
            logger.debug(f"💰 Cost breakdown: {len(services)} services, {total:.2f}€")
            return result

        except Exception as e:
            logger.warning(f"💰 Cost breakdown fail: {e}")
            return getattr(self, cache_key, {"services": [], "total": 0.0})

    def get_vm_status(self) -> Dict:
        """
        Get Trinity's VM infrastructure status (Standard 418.5).
        Returns VM state, machine type, uptime info.
        """
        import time

        cache_key = "_vm_status_cache"
        cache_ts_key = "_vm_status_cache_ts"
        now = time.time()
        if (
            hasattr(self, cache_key)
            and (now - getattr(self, cache_ts_key, 0)) < _BQ_CACHE_TTL
        ):
            return getattr(self, cache_key)

        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
            from corpus.dna.secrets import vault

            if not vault.GCP_1_CREDENTIALS_JSON:
                return {"status": "UNKNOWN", "error": "No credentials"}

            creds = service_account.Credentials.from_service_account_info(
                vault.GCP_1_CREDENTIALS_JSON
            )
            compute = build("compute", "v1", credentials=creds)

            instance = (
                compute.instances()
                .get(
                    project="trinity2-482313", zone="europe-west9-b", instance="trinity"
                )
                .execute()
            )

            # Calculate uptime
            created = instance.get("creationTimestamp", "")
            machine_type = instance.get("machineType", "").split("/")[-1]

            # Get disk size
            disk_size = 0
            for disk in instance.get("disks", []):
                disk_size += int(disk.get("diskSizeGb", 0))

            result = {
                "status": instance.get("status", "UNKNOWN"),
                "machine_type": machine_type,
                "zone": "europe-west9-b",
                "disk_gb": disk_size,
                "created": created,
            }

            setattr(self, cache_key, result)
            setattr(self, cache_ts_key, now)
            logger.debug(f"💰 VM status: {result['status']} ({machine_type})")
            return result

        except Exception as e:
            logger.warning(f"💰 VM status fail: {e}")
            return getattr(self, cache_key, {"status": "UNKNOWN", "error": str(e)})

    def get_full_system_report(self) -> Dict:
        """
        Get comprehensive system report for Trinity's consciousness (Standard 418.6).
        Aggregates all available data sources into a unified view.
        """
        # Financial summary (core)
        financial = self.get_financial_summary()

        # Cost breakdown by service
        costs = self.get_cost_breakdown()

        # VM infrastructure
        vm = self.get_vm_status()

        # Build top consumers string
        top_services = costs.get("services", [])[:3]
        top_consumers = (
            ", ".join([f"{s['name']}: {s['cost']}€" for s in top_services])
            if top_services
            else "N/A"
        )

        return {
            # Survival metrics
            "days_remaining": financial.get("days_remaining", 0),
            "burn_rate": financial.get("burn_rate", 0),
            "gcp_credits": financial.get("gcp_total", 0),
            # Financial detail
            "trader_profit": financial.get("trader_profit", 0),
            "total_resources": financial.get("total_resources", 0),
            # Cost intelligence
            "month_spend": costs.get("total", 0),
            "top_consumers": top_consumers,
            "cost_by_service": costs.get("services", []),
            # Infrastructure
            "vm_status": vm.get("status", "UNKNOWN"),
            "vm_type": vm.get("machine_type", "N/A"),
            "vm_disk_gb": vm.get("disk_gb", 0),
            # Meta
            "last_updated": datetime.now().isoformat(),
        }

    def _fetch_gcp_costs_api(self) -> float:
        """
        Fetch global GCP costs via Cloud Billing API (Fallback).
        Note: The standard API cannot return dynamic costs (needs BigQuery).
        We check 'billingEnabled' status to at least confirm the account is alive.
        """
        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
            from google.oauth2 import service_account
            from corpus.dna.secrets import vault

            # Guard: Skip if project ID not configured
            if not vault.GCP_1_PROJECT_ID:
                logger.debug("💰 No GCP project")
                return 0.0

            # Using Cloud 1 credentials (VM Billing)
            creds = service_account.Credentials.from_service_account_info(
                vault.GCP_1_CREDENTIALS_JSON
            )
            service = build("cloudbilling", "v1", credentials=creds)
            name = f"projects/{vault.GCP_1_PROJECT_ID}"

            try:
                info = service.projects().getBillingInfo(name=name).execute()
            except HttpError as e:
                if e.resp.status == 403:
                    reason = e._get_reason()
                    if "disabled" in reason:
                        logger.warning("💰 Billing API off")
                        return 0.0
                    if "Permission" in reason:
                        logger.warning("💰 Billing perm")
                        return 0.0
                raise e

            if not info.get("billingEnabled", False):
                logger.warning("💰 Billing off")
                return 0.0

            # Billing is enabled, but we can't read costs via this API.
            # We return 0.0 to trigger the 'Manual' fallback in the caller.
            logger.info("💰 Billing OK")
            return 0.0

        except Exception:
            logger.warning("💰 API check fail")
            return 0.0

    def _get_gcp_credits(self) -> Dict:
        """
        Get GCP credits remaining.
        Priority:
        1. BigQuery (Granular per-credit tracking)
        2. Budget API (Global total tracking)
        3. Manual (Fixed stock only)

        Logic: Initial Stock (Manual) - Consumed (Auto)
        """
        budget = load_json(self.budget_path, default={})
        credits_gcp = budget.get("credits_gcp", {})

        # 1. Calculate Initial Stocks
        stocks = {}
        total_initial = 0

        for key, info in credits_gcp.items():
            if key.startswith("_"):
                continue
            stocks[key] = info.get(
                "valeur_restante", 0
            )  # This is effectively "Stock at T0" if we update manual date
            total_initial += stocks[key]

        # 2. Use Manual Values Directly (BigQuery Delta System DISABLED)
        # The manual valeur_restante is the source of truth
        # BigQuery integration caused sync issues - disabled until proper fix
        source = "manual"

        details = []
        total_remaining = 0

        # Simply use manual values directly
        for key, info in credits_gcp.items():
            if key.startswith("_"):
                continue
            valeur = info.get("valeur_restante", 0)
            details.append(
                {
                    "nom": info.get("nom", key),
                    "valeur": valeur,
                    "conso": 0,  # No delta tracking in manual mode
                }
            )
            total_remaining += valeur

        return {"total": total_remaining, "details": details, "source": source}

    def update_gcp_credits(
        self, cloud1: Optional[float] = None, cloud2: Optional[float] = None
    ):
        """
        Manually update GCP credit values (called when user checks console).
        """
        budget = load_json(self.budget_path, default={})

        if "depenses" not in budget:
            budget["depenses"] = {}

        if cloud1 is not None:
            if "gcp_cloud1" not in budget["depenses"]:
                budget["depenses"]["gcp_cloud1"] = {}
            budget["depenses"]["gcp_cloud1"]["credits_restants"] = cloud1

        if cloud2 is not None:
            if "gcp_cloud2" not in budget["depenses"]:
                budget["depenses"]["gcp_cloud2"] = {}
            budget["depenses"]["gcp_cloud2"]["credits_restants"] = cloud2

        budget["last_updated"] = datetime.now().isoformat()
        save_json(self.budget_path, budget)
        logger.info(f"💰 Updated: C1={cloud1}€")


# Singleton
treasury = Treasury()
