"""
CORPUS/BRAIN/TOOLS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: TRINITY TOOLS (Function Calling)
PURPOSE: Outils que Trinity peut utiliser pour interagir avec son environnement.
══════════════════════════════════════════════════════════════════════════════
"""

from loguru import logger
from corpus.dna.genome import ROOT_DIR


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (For Gemini Function Calling)
# ═══════════════════════════════════════════════════════════════════════════════

READ_FILE_TOOL = {
    "name": "read_file",
    "description": "Lis le contenu d'un fichier du repo Trinity. Utilise cet outil quand tu as besoin de vérifier du code, une config, ou un fichier de données pour répondre avec précision.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Chemin relatif au repo Trinity (ex: 'corpus/brain/neocortex.py', 'jobs/trader/main.py', 'memories/trinity/state.json')",
            }
        },
        "required": ["path"],
    },
}

LIST_DIR_TOOL = {
    "name": "list_directory",
    "description": "Liste le contenu d'un répertoire du repo Trinity. Utilise cet outil pour explorer la structure du projet.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Chemin relatif au repo Trinity (ex: 'corpus/', 'jobs/', 'memories/trinity/')",
            }
        },
        "required": ["path"],
    },
}

# All available tools
SEARCH_REPO_TOOL = {
    "name": "search_repo",
    "description": "Cherche du texte ou du code dans le repo Trinity. Utilise cet outil ('grep') pour trouver où sont définies des choses dont tu ne connais pas le chemin.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Le texte ou regex à chercher (ex: 'process_chat', 'class Valhalla')",
            },
            "path": {
                "type": "string",
                "description": "Le répertoire où chercher (défaut: '.')",
            },
        },
        "required": ["query"],
    },
}

GET_STATUS_TOOL = {
    "name": "get_system_status",
    "description": "Récupère les vitaux du système (CPU, RAM, Humeur). Utilise cet outil pour répondre aux commandes '/status' ou 'dashboard'.",
    "parameters": {
        "type": "object",
        "properties": {},  # No params specific needed
    },
}

GET_JOB_STATUS_TOOL = {
    "name": "get_job_status",
    "description": "Récupère le statut d'un job (Trader, YouTuber, Influencer). Utilise pour répondre à 'comment va le trader?' ou 'status jobs'.",
    "parameters": {
        "type": "object",
        "properties": {
            "job_name": {
                "type": "string",
                "description": "Nom du job: 'trader', 'youtuber', 'influencer', ou vide pour tous.",
            }
        },
    },
}

GET_ERROR_LOGS_TOOL = {
    "name": "get_error_logs",
    "description": "Récupère les dernières erreurs système. Utilise pour répondre à 'dernières erreurs?' ou 'problèmes récents'.",
    "parameters": {
        "type": "object",
        "properties": {
            "n": {
                "type": "integer",
                "description": "Nombre d'erreurs à récupérer (défaut: 5).",
            }
        },
    },
}

GET_TOKEN_USAGE_TOOL = {
    "name": "get_token_usage",
    "description": "Récupère la consommation de tokens. Utilise pour répondre à 'combien de tokens?' ou 'coûts API'.",
    "parameters": {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "description": "Période: 'today', 'week', ou 'all' (défaut: 'today').",
            }
        },
    },
}

SEMANTIC_SEARCH_CODE_TOOL = {
    "name": "semantic_search_code",
    "description": "Recherche sémantique dans le codebase Trinity. Plus puissant que grep: trouve du code par SIGNIFICATION. Ex: 'comment fonctionne le routing', 'où sont gérés les embeddings'.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "La question ou le concept à chercher (en langage naturel).",
            },
            "n_results": {
                "type": "integer",
                "description": "Nombre de résultats (défaut: 5).",
            },
        },
        "required": ["query"],
    },
}

# SOTA 2026: Minimal tools - Spirit already injects system/job status in context
# Only expose tools for data Trinity DOESN'T already have
TRINITY_TOOLS = [
    READ_FILE_TOOL,  # For specific files not in context
    LIST_DIR_TOOL,  # For exploration
    GET_ERROR_LOGS_TOOL,  # For debugging
]

# Full tools for deep introspection (used by Route 8 / Codebase RAG)
TRINITY_TOOLS_FULL = [
    READ_FILE_TOOL,
    LIST_DIR_TOOL,
    SEARCH_REPO_TOOL,
    GET_STATUS_TOOL,
    GET_JOB_STATUS_TOOL,
    GET_ERROR_LOGS_TOOL,
    GET_TOKEN_USAGE_TOOL,
    SEMANTIC_SEARCH_CODE_TOOL,
]


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════


async def execute_tool(tool_name: str, args: dict) -> str:
    """
    Execute a tool and return the result.
    Security: Only allows reading within ROOT_DIR.
    """
    try:
        if tool_name == "read_file":
            return _read_file(args.get("path", ""))
        elif tool_name == "list_directory":
            return _list_directory(args.get("path", ""))
        elif tool_name == "search_repo":
            return _search_repo(args.get("query", ""), args.get("path", "."))
        elif tool_name == "get_system_status":
            return await _get_system_status()
        elif tool_name == "get_job_status":
            return _get_job_status(args.get("job_name", ""))
        elif tool_name == "get_error_logs":
            return _get_error_logs(args.get("n", 5))
        elif tool_name == "get_token_usage":
            return _get_token_usage(args.get("period", "today"))
        elif tool_name == "semantic_search_code":
            return await _semantic_search_code(
                args.get("query", ""), args.get("n_results", 5)
            )
        else:
            return f"ERROR: Outil inconnu '{tool_name}'"
    except Exception as e:
        logger.error(f"🔧 Tool Error ({tool_name}): {e}")
        return f"ERROR: {e}"


def _read_file(relative_path: str) -> str:
    """Read a file from the Trinity repo."""
    if not relative_path:
        return "ERROR: Chemin requis"

    # Security: Resolve and validate path
    target = (ROOT_DIR / relative_path).resolve()

    # Must be within ROOT_DIR
    if not str(target).startswith(str(ROOT_DIR.resolve())):
        return "ERROR: Accès refusé (hors du repo)"

    if not target.exists():
        return f"ERROR: Fichier non trouvé: {relative_path}"

    if not target.is_file():
        return f"ERROR: Ce n'est pas un fichier: {relative_path}"

    # Size limit (50KB)
    if target.stat().st_size > 50_000:
        return (
            f"ERROR: Fichier trop volumineux ({target.stat().st_size} bytes). Max: 50KB"
        )

    try:
        content = target.read_text(encoding="utf-8")
        # Truncate if still too long
        if len(content) > 10_000:
            content = content[:10_000] + "\n\n[... TRUNCATED ...]"

        logger.info(f"📖 [TOOLS] Read: {relative_path} ({len(content)} chars)")
        return content
    except Exception as e:
        return f"ERROR: Impossible de lire le fichier: {e}"


def _list_directory(relative_path: str) -> str:
    """List contents of a directory."""
    if not relative_path:
        relative_path = "."

    target = (ROOT_DIR / relative_path).resolve()

    if not str(target).startswith(str(ROOT_DIR.resolve())):
        return "ERROR: Accès refusé (hors du repo)"

    if not target.exists():
        return f"ERROR: Répertoire non trouvé: {relative_path}"

    if not target.is_dir():
        return f"ERROR: Ce n'est pas un répertoire: {relative_path}"

    try:
        items = sorted(target.iterdir())
        result = []
        for item in items[:50]:  # Max 50 items
            prefix = "📁" if item.is_dir() else "📄"
            name = item.name + ("/" if item.is_dir() else "")
            result.append(f"{prefix} {name}")

        output = f"📂 {relative_path}\n" + "\n".join(result)
        if len(items) > 50:
            output += f"\n... et {len(items) - 50} autres"

        logger.info(f"📂 [TOOLS] Listed: {relative_path} ({len(items)} items)")
        return output
    except Exception as e:
        return f"ERROR: Impossible de lister: {e}"


def _search_repo(query: str, relative_path: str = ".") -> str:
    """
    Search for text in the repo (grep-like).
    Limited to 50 matches to avoid token explosion.
    """
    if not query:
        return "ERROR: Query requise"

    if not relative_path:
        relative_path = "."

    target_dir = (ROOT_DIR / relative_path).resolve()

    # Security check
    if not str(target_dir).startswith(str(ROOT_DIR.resolve())):
        return "ERROR: Accès refusé (hors du repo)"

    results = []
    try:
        # Recursive search in python/md/json files
        count = 0
        extensions = {".py", ".md", ".json", ".yaml", ".txt"}

        for file in target_dir.rglob("*"):
            if not file.is_file() or file.suffix not in extensions:
                continue

            # Skip hidden/system dirs
            if any(part.startswith(".") for part in file.parts):
                continue
            if "__pycache__" in file.parts:
                continue

            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
                if query in content:
                    # Find context (simple line match)
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if query in line:
                            rel_file = file.relative_to(ROOT_DIR)
                            results.append(f"{rel_file}:{i + 1}: {line.strip()[:100]}")
                            count += 1
                            if count >= 50:
                                break
            except Exception:
                continue

            if count >= 50:
                break

        if not results:
            return f"Aucun résultat trouvé pour '{query}' dans {relative_path}"

        output = f"🔍 Résultats pour '{query}' (Top 50):\n" + "\n".join(results)
        logger.info(f"🔍 [TOOLS] Search '{query}' -> {count} matches")
        return output

    except Exception as e:
        return f"ERROR: Recherche échouée: {e}"


async def _get_system_status() -> str:
    """
    Get live system status (Vitals + Hormones).
    Helper for /status commands.
    """
    from corpus.soma.immune import immune
    from corpus.brain.hormones import hormones

    try:
        vitals = await immune.check_vitals()
        mood = hormones.get_state()

        return f"""
[SYSTEM STATUS REPORT]
✅ IMMUNE SYSTEM: {vitals.get("status", "OK")}
- CPU: {vitals.get("cpu", 0)}%
- RAM: {vitals.get("memory", 0)}MB

🧠 HORMONAL STATE:
- Mood: {mood.get("mood", "NEUTRAL")} (Score: {mood.get("score", 0):.2f})
- Dopamine: {mood.get("dopamine", 0):.2f}
- Cortisol: {mood.get("cortisol", 0):.2f}

Running on: Trinity Core v2026.1
"""
    except Exception as e:
        return f"ERROR: Impossible de récupérer le statut: {e}"


def _get_job_status(job_name: str = "") -> str:
    """
    Get status of Trinity's jobs (Trader, YouTuber, Influencer).
    """
    from corpus.dna.genome import MEMORIES_DIR
    import json

    jobs = ["trader", "youtuber", "influencer"]
    if job_name and job_name.lower() in jobs:
        jobs = [job_name.lower()]

    results = []
    for job in jobs:
        state_file = MEMORIES_DIR / job / "state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)

                # Extract key metrics based on job type
                if job == "trader":
                    cycle = state.get("cycle_count", 0)
                    pnl = state.get("session_pnl", 0)
                    last_trade = state.get("last_trade_time", "N/A")
                    results.append(
                        f"📈 TRADER: Cycle {cycle} | PnL: {pnl:+.2f}€ | Last: {last_trade}"
                    )
                elif job == "youtuber":
                    videos = state.get("videos_produced", 0)
                    status = state.get("status", "idle")
                    results.append(f"🎬 YOUTUBER: {videos} videos | Status: {status}")
                elif job == "influencer":
                    posts = state.get("posts_count", 0)
                    status = state.get("status", "idle")
                    results.append(f"📱 INFLUENCER: {posts} posts | Status: {status}")
            except Exception as e:
                results.append(f"⚠️ {job.upper()}: Error reading state ({e})")
        else:
            results.append(f"❌ {job.upper()}: No state file")

    return "[JOB STATUS REPORT]\n" + "\n".join(results)


def _get_error_logs(n: int = 5) -> str:
    """
    Get last N errors from system logs.
    """
    from corpus.dna.genome import MEMORIES_DIR
    import json

    log_file = MEMORIES_DIR / "logs" / "trinity.jsonl"
    if not log_file.exists():
        return "Aucun log d'erreur trouvé."

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        errors = []
        for line in reversed(lines):
            try:
                entry = json.loads(line)
                level = entry.get("level", "").upper()
                if level in ["ERROR", "CRITICAL", "WARNING"]:
                    ts = entry.get("timestamp", "?")[:19]  # Truncate to second
                    msg = entry.get("message", "")[:100]
                    errors.append(f"[{ts}] {level}: {msg}")
                    if len(errors) >= n:
                        break
            except json.JSONDecodeError:
                continue

        if not errors:
            return "✅ Aucune erreur récente trouvée."

        return f"[DERNIÈRES {len(errors)} ERREURS]\n" + "\n".join(errors)

    except Exception as e:
        return f"ERROR: Lecture logs échouée: {e}"


def _get_token_usage(period: str = "today") -> str:
    """
    Aggregate token usage from tokens.jsonl.
    """
    from corpus.dna.genome import MEMORIES_DIR
    import json
    from datetime import datetime, timedelta

    log_file = MEMORIES_DIR / "logs" / "tokens.jsonl"
    if not log_file.exists():
        return "Aucun log de tokens trouvé."

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Determine cutoff time
        now = datetime.now()
        if period == "today":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            cutoff = now - timedelta(days=7)
        else:
            cutoff = datetime.min  # All time

        total_in = 0
        total_out = 0
        route_counts: dict[str, int] = {}

        for line in lines:
            try:
                entry = json.loads(line)
                ts_str = entry.get("timestamp", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str)
                    if ts < cutoff:
                        continue

                total_in += entry.get("in", 0)
                total_out += entry.get("out", 0)
                route = entry.get("route", "UNKNOWN")
                route_counts[route] = route_counts.get(route, 0) + 1
            except (json.JSONDecodeError, ValueError):
                continue

        total = total_in + total_out
        top_routes = sorted(route_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        routes_str = ", ".join([f"{r}:{c}" for r, c in top_routes])

        return f"""
[TOKEN USAGE: {period.upper()}]
📊 Total: {total:,} tokens (In: {total_in:,} | Out: {total_out:,})
🔝 Top Routes: {routes_str}
💰 Estimated Cost: ~${total * 0.00001:.4f} (rough)
"""

    except Exception as e:
        return f"ERROR: Analyse tokens échouée: {e}"


async def _semantic_search_code(query: str, n_results: int = 5) -> str:
    """
    Semantic search over the Trinity codebase.
    Uses ChromaDB vector search via codebase_indexer.
    """
    try:
        from corpus.brain.cortex_mapper import search_codebase

        results = await search_codebase(query, n_results=n_results)

        if not results:
            return (
                "❌ Aucun résultat trouvé. L'index est peut-être vide.\n"
                "Exécute `python -m corpus.brain.cortex_mapper` pour indexer le codebase."
            )

        output_lines = [f"[SEMANTIC SEARCH: '{query}']"]
        for i, r in enumerate(results, 1):
            score_pct = r.get("score", 0) * 100
            output_lines.append(
                f"\n{i}. **{r.get('name', '?')}** ({r.get('type', '?')})"
                f"\n   📁 {r.get('file', '?')}:L{r.get('line', '?')}"
                f"\n   📊 Score: {score_pct:.0f}%"
                f"\n   ```\n{r.get('content', '')[:300]}...\n   ```"
            )

        return "\n".join(output_lines)

    except ImportError:
        return "ERROR: codebase_indexer module not found."
    except Exception as e:
        return f"ERROR: Semantic search failed: {e}"
