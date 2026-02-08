"""
CORPUS/BRAIN/GATTACA.PY - CENTRAL ROUTER
══════════════════════════════════════════════════════════════════════════════
Routes 1-9 & 12-13: Standard API Key
══════════════════════════════════════════════════════════════════════════════
"""

import os
import re
import base64
import json
import time
import asyncio

from pathlib import Path
from datetime import datetime
from typing import Optional

from loguru import logger
from google import genai
import httpx

from corpus.dna.secrets import vault
from corpus.dna.genome import ROOT_DIR, LOGS_DIR

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE CONSTANTS (1-6 SCHEMA SOTA 2026)
# ═══════════════════════════════════════════════════════════════════════════════

# CORE (1-3)
ROUTE_PRO = 1  # 🧠 Reasoning (Hybrid: CLI GCA -> Studio Fallback)
ROUTE_FLASH = 2  # ⚡ Fast (Studio -> CLI Fallback)
ROUTE_IMAGE = 3  # 🎨 Vision Gen (Gemini 3 Image)

# SPECIALIZED (4-6)
ROUTE_GROUNDING = 4  # 🔍 Live Knowledge (Flash+Search -> CLI Fallback)
ROUTE_VOICE = 5  # 🗣️ TTS (Gemini 2.5)
ROUTE_MEMORY = 6  # 💾 Embeddings (Gemini Embedding)

# VIDEO ROUTES (7) - VEO 3.1
ROUTE_SOCIAL = 7  # 🎬 Video Fast (veo-3.1-fast-generate-preview)

# AGENTIC (9) - Chat with Tool Use
ROUTE_CHAT = 9  # 💬 Agentic Chat (Tools + Multi-turn)

# Aliases for internal compatibility
ROUTE_CLI = ROUTE_PRO
ROUTE_CREATE = ROUTE_IMAGE
ROUTE_SEARCH = ROUTE_GROUNDING
ROUTE_DESIGN = ROUTE_IMAGE  # Merged
ROUTE_VIDEO = ROUTE_SOCIAL  # Default video route
ROUTE_LIVE = ROUTE_GROUNDING  # Alias for Live Knowledge

# Route Metadata (Icons & Colors for Logs)
ROUTE_METADATA = {
    1: {"icon": "🧠", "color": "green", "name": "PRO"},
    2: {"icon": "⚡", "color": "yellow", "name": "FLASH"},
    3: {"icon": "🎨", "color": "cyan", "name": "IMAGE"},
    4: {"icon": "🔍", "color": "blue", "name": "GROUNDING"},
    5: {"icon": "🗣️", "color": "magenta", "name": "VOICE"},
    6: {"icon": "💾", "color": "green", "name": "MEMORY"},
    7: {"icon": "🎬", "color": "red", "name": "VIDEO"},
    9: {"icon": "💬", "color": "white", "name": "CHAT"},
}

# Models per Route (STANDARD CONFIGURATION: Gemini 3 Family + Support)
MODELS = {
    1: "gemini-3-pro-preview",  # PRO (Reasoning)
    2: "gemini-3-flash-preview",  # FLASH (Speed)
    3: "gemini-3-pro-image-preview",  # IMAGE (Gemini 3 Native - per synapses.md)
    4: "gemini-3-flash-preview",  # GROUNDING (Search Base)
    5: "gemini-2.5-pro-preview-tts",  # VOICE (Legacy/Support)
    6: "gemini-embedding-001",  # MEMORY (SOTA)
    7: "veo-3.1-fast-generate-preview",  # VIDEO (VEO 3.1 Fast)
    9: "gemini-3-flash-preview",  # CHAT (Agentic with Tools)
}

# API Keys (FREE + quota) for routes 2-8



# Direct function access (no property needed at module level)


# Cloud Configs Removed

TOKENS_LOG = LOGS_DIR / "tokens.jsonl"


class GattacaRouter:
    """Unified Neural Router - 8 Routes (1-8 including VEO Video)."""

    # Expose Constants for instance access
    ROUTE_PRO = ROUTE_PRO
    ROUTE_FLASH = ROUTE_FLASH
    ROUTE_IMAGE = ROUTE_IMAGE
    ROUTE_GROUNDING = ROUTE_GROUNDING
    ROUTE_VOICE = ROUTE_VOICE
    ROUTE_MEMORY = ROUTE_MEMORY
    ROUTE_SOCIAL = ROUTE_SOCIAL  # VEO Fast
    ROUTE_CHAT = ROUTE_CHAT  # Agentic Chat

    # Aliases
    ROUTE_CLI = ROUTE_PRO
    ROUTE_CREATE = ROUTE_IMAGE
    ROUTE_SEARCH = ROUTE_GROUNDING
    ROUTE_VIDEO = ROUTE_SOCIAL  # Default video route

    def __init__(self):
        self.active_routes = {i: True for i in range(1, 10)}  # 1-9

        self.env_path = ROOT_DIR / ".env"
        # Neural Cache (LRU/TTLish)
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    async def route(self, prompt: str, route_id: int = ROUTE_FLASH, **kwargs) -> str:
        """
        Main routing entry point.

        Args:
            prompt: The input prompt
            route_id: Route to use (1-6)
            **kwargs: Optional params:
                - response_schema: Pydantic model or dict for structured output
        """
        if not self.active_routes.get(route_id):
            logger.warning(f"🚫 Route {route_id} blocked, falling back to FLASH")
            route_id = ROUTE_FLASH

        # 🧠 NEURAL CACHE (1h TTL)
        # Exclude Creative Routes (IMAGE) to keep variety
        cache_key = None
        use_cache = kwargs.pop("use_cache", True)  # SOTA 2026: Allow explicit bypass
        if use_cache and route_id not in [self.ROUTE_IMAGE]:
            import hashlib

            # Create a deterministic key from route + prompt
            raw_key = f"{route_id}:{prompt}"
            cache_key = hashlib.md5(raw_key.encode()).hexdigest()

            if cache_key in self._cache:
                stored_time, stored_response = self._cache[cache_key]
                if (time.time() - stored_time) < self._cache_ttl:
                    logger.info("⚡ [GATTACA] Cache hit!")
                    return stored_response
                else:
                    # Expired
                    del self._cache[cache_key]

        try:
            response = None
            match route_id:
                case self.ROUTE_PRO:  # 1
                    # 🆓 PRO (Hybrid: CLI GCA -> Studio Fallback)
                    # We start with CLI because it's free/high quota
                    response = await self._route_cli(prompt, **kwargs)

                case self.ROUTE_FLASH:  # 2
                    # ⚡ Studio Flash
                    response = await self._route_text(
                        prompt,
                        MODELS[self.ROUTE_FLASH],
                        route_id=self.ROUTE_FLASH,
                        **kwargs,
                    )

                case self.ROUTE_IMAGE:  # 3
                    # 🎨 Vision Gen (Gemini 3 Image)
                    response = await self._route_create(prompt)

                case self.ROUTE_GROUNDING:  # 4
                    # 🔍 Grounding (Flash + Search)
                    response = await self._route_search(prompt)

                case self.ROUTE_VOICE:  # 5
                    # 🗣️ TTS Pro
                    response = await self._route_voice(
                        prompt, lang=kwargs.get("lang", "en-US")
                    )

                case self.ROUTE_MEMORY:  # 6
                    # 💾 Embeddings
                    response = await self._route_memory(prompt)

                case self.ROUTE_SOCIAL:  # 7
                    # 🎬 Video Fast (VEO 3.1)
                    response = await self._route_video(
                        prompt, model=MODELS[self.ROUTE_SOCIAL], **kwargs
                    )

                case self.ROUTE_CHAT:  # 9
                    # 💬 Agentic Chat (Tools + Multi-turn)
                    response = await self._route_chat(prompt, **kwargs)

                case _:
                    logger.error(f"❌ Unknown Route ID: {route_id}")
                    response = f"ERROR: Unknown route {route_id}"

            # 💾 Store in Cache
            if (
                cache_key
                and response
                and "ERROR" not in str(response)
                and '"error":' not in str(response)
            ):
                self._cache[cache_key] = (time.time(), response)

            # 🛡️ Anti-Arrhythmia Guard: NEVER return None (Standard 352)
            if response is None:
                logger.error(
                    f"💥 [GATTACA] Route {route_id} returned None (Code Path Bug)"
                )
                return f"ERROR: Route {route_id} failed (null response)"

            return response

        except Exception as e:
            logger.error(f"💥 Route {route_id} error: {e}")
            return f"ERROR: {e}"

    async def think(self, prompt: str, route_id: int = ROUTE_FLASH, **kwargs) -> str:
        """Alias for route()."""
        return await self.route(prompt, route_id, **kwargs)

    async def smart_route(
        self, prompt: str, complexity_score: float = 0.5, **kwargs
    ) -> str:
        """
        Adaptive Intelligence Routing.
        Optimizes cost/performance based on complexity.

        Args:
            prompt: The input prompt
            complexity_score: 0.0 (Simple) to 1.0 (Complex)
        """
        # Default to requested route or FLASH
        target_route = kwargs.get("route_id", ROUTE_FLASH)

        # 1. Simple queries -> Force FLASH
        if complexity_score < 0.3:
            target_route = ROUTE_FLASH

        # 2. Complex queries -> Force PRO
        elif complexity_score > 0.7:
            target_route = ROUTE_PRO

        # Execute determined route
        return await self.route(prompt, route_id=target_route, **kwargs)

    def _parse_error(self, e: Exception) -> str:
        """Extract clean error message from verbose API exceptions."""
        s = str(e)
        # If it looks like a dict/json representation
        if "{'error':" in s or "'code': 429" in s:
            try:
                # Try to extract the 'message' part using regex to avoid full json parsing of partial strings
                import re

                match = re.search(r"'message':\s*'([^']+)'", s)
                if match:
                    return match.group(1)
            except Exception:
                pass
        # Fallback: simpler truncation
        if "Quota exceeded" in s:
            return "Quota exceeded for model (Rate Limit)"
        return s[:200] + "..." if len(s) > 200 else s

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 0: CLI GCA (Premium OAuth - Gemini 3 Pro - 1500/day FREE)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _route_cli(self, prompt: str, **kwargs) -> str:
        """
        CLI GCA Route - Uses Gemini CLI with Premium OAuth.

        Benefits:
        - Gemini 3 Pro (SOTA model)
        - 1500 requests/day FREE (Premium subscription)
        - 120 requests/minute
        - No API keys needed (OAuth Standard)
        - Workspace context injection supported

        Fallback: Routes to ROUTE_PRO if CLI fails.
        """
        import subprocess

        try:
            # 1. SOTA 2026: Multimodal CLI via Base64 Injection
            # Unlock Image capabilities even on CLI by encoding input
            final_prompt = prompt

            if kwargs.get("images"):
                logger.info(
                    "🧪 [GATTACA] Applying Multimodal CLI Optimization (Base64 Injection)..."
                )
                import base64

                # Encode all images and append to prompt
                img_parts = []
                for i, img_data in enumerate(kwargs["images"]):
                    # Handle raw bytes or file paths if they were passed differently
                    # Assuming we get bytes here as per standard _route_text interface
                    if isinstance(img_data, bytes):
                        b64_str = base64.b64encode(img_data).decode("utf-8")
                        img_parts.append(
                            f"\n\n[IMAGE_{i}_BASE64_WEBP_DATA_START]\n{b64_str}\n[IMAGE_{i}_DATA_END]"
                        )

                img_context = "".join(img_parts)
                final_prompt = f"{prompt}\n\nCONTEXTUAL DATA:\n{img_context}\n\nINSTRUCTION: The above data contains base64 encoded images. Decode them visually and answer the prompt based on their content."

            # 2. Prepare Model Instruction
            # We must still instruct the MODEL to output JSON if requested
            if kwargs.get("json_output"):
                final_prompt = f"{final_prompt}\n\nRéponds uniquement au format JSON brut sans balises markdown."

            # 3. Prepare Command (CLI Reliability)
            # FORCE Gemini 3 Pro (Verified Model)
            cmd = ["gemini", "-m", MODELS[ROUTE_CLI], "-o", "json"]

            # 4. Execute via Stdin (Async)
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                input=final_prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=kwargs.get("timeout", 300),
                env={**os.environ, "GOOGLE_GENAI_USE_GCA": "true"},
            )

            if process.returncode == 0:
                try:
                    # Parse Native CLI JSON Output
                    result = json.loads(process.stdout)

                    # Extract text content
                    if "response" in result:
                        # CLI v0.24+ simplified structure
                        output = result["response"]
                    else:
                        # Standard API structure fallback
                        output = result["candidates"][0]["content"]["parts"][0]["text"]

                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    # Fallback if output structure changes or is just text
                    logger.warning(
                        f"⚠️ [GATTACA] CLI JSON Parse Error: {e} -> Returning raw stdout"
                    )
                    output = process.stdout.strip()
                    if "Loaded cached credentials." in output:
                        output = output.replace(
                            "Loaded cached credentials.", ""
                        ).strip()

                # 🧹 SANITIZE: Strip ANSI escape codes
                ansi_pattern = re.compile(r"\x1b[\[\(<][0-9;?]*[a-zA-Z<>=]?")
                output = ansi_pattern.sub("", output)

                logger.success("🆓 [GATTACA] CLI OK")

                self._log_tokens(
                    "CLI GCA (Premium)",
                    ROUTE_PRO,
                    prompt,
                    output[:100] + "..." if len(output) > 100 else output,
                    model=MODELS[ROUTE_PRO],
                )

                return output
            else:
                # CLI failed
                stderr = process.stderr or ""
                raise Exception(f"CLI exit code {process.returncode}: {stderr[:200]}")

        except subprocess.TimeoutExpired:
            logger.warning("⏱️ [GATTACA] CLI Timeout - Falling back to FLASH")
        except FileNotFoundError:
            logger.warning("📦 [GATTACA] CLI not installed - Falling back to FLASH")
        except Exception as e:
            logger.warning(f"⚠️ [GATTACA] CLI failed: {e} - Falling back to FLASH")

        # FALLBACK: Route 1 (CLI) -> Route 2 (Flash)
        # ANTI-LOOP: If we already tried fallback, stop here.
        if kwargs.get("fallback_attempted"):
            logger.error(
                "🛑 [GATTACA] Recursive Failover Detected (CLI -> Flash -> CLI). Aborting."
            )
            return "ERROR: All Routes Failed."

        logger.info(
            "🔄 [GATTACA] Falling back to ROUTE_FLASH (API Key does not support Pro)"
        )
        # Mark fallback as attempted to prevent Flash from calling us back
        kwargs["fallback_attempted"] = True
        kwargs.pop("route_id", None)

        return await self._route_text(
            prompt, MODELS[ROUTE_FLASH], route_id=ROUTE_FLASH, **kwargs
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTES 1-2: TEXT
    # ═══════════════════════════════════════════════════════════════════════════

    async def _route_text(self, prompt: str, model: str, **kwargs) -> str:
        """
        Text generation with API key + Cloud 2 fallback.
        Supports optional response_schema for structured JSON output.
        """
        # Build generation config
        config = {}
        response_schema = kwargs.get("response_schema")

        if response_schema:
            # Structured output mode
            config["response_mime_type"] = "application/json"
            # If it's a Pydantic model, convert to schema
            if hasattr(response_schema, "model_json_schema"):
                config["response_schema"] = response_schema.model_json_schema()
            else:
                config["response_schema"] = response_schema

        # ⚡ HORMONAL INFLUENCE (Bio-Feedback SOTA)
        try:
            from corpus.brain.hormones import hormones

            mood = hormones.get_state()
            dopa = mood.get("dopamine", 0.5)
            cort = mood.get("cortisol", 0.2)

            # Dynamic Temp
            base_temp = 0.7
            temp_shift = (dopa * 0.2) - (cort * 0.1)
            final_temp = max(0.1, min(1.0, base_temp + temp_shift))
            config["temperature"] = round(final_temp, 2)

        except ImportError:
            pass

        # 🔰 SOTA SDK CONFIG: MAX POWER (Safety Off / Native Instruct / Tools)
        from google.genai import types

        # 1. Unshackled Safety (Assume User is Responsible)
        config["safety_settings"] = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold="BLOCK_NONE",  # type: ignore
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold="BLOCK_NONE",  # type: ignore
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold="BLOCK_NONE",  # type: ignore
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold="BLOCK_NONE",  # type: ignore
            ),
        ]

        # 2. Native System Instruction (Cleaner than prompt injection)
        if "system_instruction" in kwargs:
            config["system_instruction"] = kwargs["system_instruction"]

        # 3. Tool Injection (e.g. Code Execution, Search)
        if "tools" in kwargs:
            config["tools"] = kwargs["tools"]

        # Prepare contents (Text + Images)
        contents: list = [prompt]
        if "files" in kwargs and kwargs["files"]:
            for file_data in kwargs["files"]:
                # file_data can be:
                # 1. bytes (raw data) -> needs 'mime_type' key in dict or passed separately?
                # Actually, let's assume standard format: {"mime_type": str, "data": bytes}
                if (
                    isinstance(file_data, dict)
                    and "data" in file_data
                    and "mime_type" in file_data
                ):
                    contents.append(
                        types.Part.from_bytes(
                            data=file_data["data"], mime_type=file_data["mime_type"]
                        )
                    )
                # 2. types.Part (already prepared)
                elif isinstance(file_data, types.Part):
                    contents.append(file_data)
                # 3. Legacy compatibility (raw bytes assumed to be jpeg if no info?) - deprecated
                elif isinstance(file_data, bytes):
                    contents.append(
                        types.Part.from_bytes(data=file_data, mime_type="image/jpeg")
                    )

        # STANDARD API CALL (Single Key)
        from corpus.brain.astrocyte import key_manager
        
        # Simple retry logic for transient errors (without key rotation)
        max_retries = 3
        
        for attempt in range(max_retries):
            key = key_manager.get_active_key()
            if not key:
                 return "ERROR: No API Key configured"

            try:
                client = genai.Client(api_key=key)

                # SOTA: Pass clean config to SDK
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,  # type: ignore
                )
                self._log_tokens(
                    "API Key",
                    kwargs.get("route_id", 1),
                    prompt,
                    response.text or "",
                    model=model,
                    source_override=kwargs.get("source"),
                )

                return response.text or ""

            except Exception as e:
                err_str = self._parse_error(e)
                # TRANSIENT ERRORS -> RETRY
                if (
                    "429" in err_str
                    or "503" in err_str
                    or "UNAVAILABLE" in err_str
                    or "overloaded" in err_str.lower()
                    or "exhausted" in err_str.lower()
                    or "Cannot connect" in err_str
                    or "DNS" in err_str
                ):
                    logger.info(
                        f"🔄 Transient Error (Attempt {attempt + 1}/{max_retries}) -> Retrying..."
                    )
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential-ish backoff
                    continue
                else:
                    # FATAL ERRORS -> FAIL
                    logger.error(f"❌ Text Gen Error: {e}")
                    return f"ERROR: {e}"

        return "ERROR: Max retries exceeded (Transient Errors)"

        # FALLBACK LOGIC (Route 3 & 5 -> Route 1)
        route_id = kwargs.get("route_id", self.ROUTE_PRO)
        if route_id in [self.ROUTE_FLASH, self.ROUTE_GROUNDING]:
            # ANTI-LOOP: If we already tried fallback, stop here.
            if kwargs.get("fallback_attempted"):
                logger.error(
                    "🛑 [GATTACA] Recursive Failover Detected (Flash -> CLI -> Flash). Aborting."
                )
                return "ERROR: All Routes Failed."

            logger.warning(
                f"⚠️ [GATTACA] Route {route_id} API Key Exhausted -> Fallback to ROUTE 1 (CLI)"
            )
            # Mark fallback as attempted
            kwargs["fallback_attempted"] = True
            kwargs.pop("route_id", None)
            return await self._route_cli(prompt, **kwargs)

        return "ERROR: All keys exhausted (Rate Limits)"

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 3: CREATE (Image Generation)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _route_create(self, prompt: str) -> str:
        """
        Image generation via gemini-3-pro-image-preview.
        SOTA 2026: Gemini 3 Native Image Generation.
        """
        import time
        from corpus.dna.genome import MEMORIES_DIR

        # STANDARD CONFIGURATION: Only Gemini 3 models active
        if not MODELS[self.ROUTE_IMAGE] or (
            "gemini-3" not in MODELS[self.ROUTE_IMAGE]
            and "imagen-4" not in MODELS[self.ROUTE_IMAGE]
        ):
            return json.dumps(
                {
                    "error": "Route Disabled",
                    "message": "Only Gemini 3 / Imagen 4 Family allowed for SOTA 2026.",
                }
            )

        output_dir = MEMORIES_DIR / "youtuber" / "images"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_dir.mkdir(parents=True, exist_ok=True)

        # STANDARD IMAGE GEN (Single Key)
        from corpus.brain.astrocyte import key_manager
        
        max_retries = 3
        
        for attempt in range(max_retries):
            key = key_manager.get_active_key()
            try:
                # Use standard Studio Client
                client = genai.Client(api_key=key)

                # Gemini 3 Image Gen Call
                response = await asyncio.to_thread(
                    client.models.generate_images,
                    model=MODELS[self.ROUTE_IMAGE],
                    prompt=prompt,
                    config=genai.types.GenerateImagesConfig(
                        number_of_images=4,
                        aspect_ratio="16:9",
                        safety_filter_level="BLOCK_NONE",  # type: ignore
                        person_generation="ALLOW_ADULT",  # type: ignore
                    ),
                )

                if response.generated_images:
                    paths = []
                    timestamp = int(time.time() * 1000)

                    for idx, img in enumerate(response.generated_images):
                        img_path = output_dir / f"gemini3_{timestamp}_{idx}.png"
                        if hasattr(img, "image") and img.image:
                            await asyncio.to_thread(
                                self._save_file, img_path, img.image.image_bytes
                            )
                            paths.append(str(img_path))

                    if paths:
                        self._log_tokens(
                            "API Key",
                            self.ROUTE_IMAGE,
                            prompt,
                            f"Generated {len(paths)} Gemini 3 Images",
                            model=MODELS[self.ROUTE_IMAGE],
                        )
                        return json.dumps({"status": "ok", "paths": paths})

            except Exception as e:
                err_str = self._parse_error(e)
                # TRANSIENT ERRORS -> RETRY
                if (
                    "429" in err_str
                    or "503" in err_str
                    or "UNAVAILABLE" in err_str
                    or "overloaded" in err_str.lower()
                    or "exhausted" in err_str.lower()
                    or "quota" in err_str.lower()
                ):
                    logger.info(
                        f"🔄 Transient Image Error (Attempt {attempt + 1}) -> Retrying..."
                    )
                    await asyncio.sleep(2)
                    continue

                logger.error(f"🎨 Gemini 3 Image Gen Failed: {e}")
                return json.dumps({"error": f"Image Gen Failed: {e}"})
                
        return json.dumps({"error": "Rate Limit Exceeded (Max Retries)"})

        return json.dumps({"error": "Rate Limit Exceeded"})

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 7: VOICE (SOTA TTS/ASR)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _route_voice(
        self, prompt: str, mode: str = "tts", lang: str = "en-US"
    ) -> str:
        """
        SOTA Audio API - TTS with gemini-2.5-pro-preview-tts.
        Saves audio to file and returns path.
        """
        from google.genai import types
        import time
        from corpus.dna.genome import MEMORIES_DIR

        # TTS Model config...

        output_dir = MEMORIES_DIR / "youtuber" / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 🧪 HORMONAL VOICE MODULATION
        # Inject tone instructions into the prompt for Gemini TTS
        try:
            from corpus.brain.hormones import hormones

            mood = hormones.get_state()
            dopamine = mood.get("dopamine", 0.5)
            cortisol = mood.get("cortisol", 0.2)
            serotonin = mood.get("serotonin", 0.5)

            tone_instruction = ""
            if dopamine > 0.7:
                tone_instruction = "Enthusiastic, fast paced"
            elif cortisol > 0.6:
                tone_instruction = "Urgent, serious"
            elif serotonin > 0.8:
                tone_instruction = "Calm, soothing"

            if tone_instruction:
                # Prepend instruction to prompt
                prompt = f"[{tone_instruction}] {prompt}"
                logger.debug(f"🗣️ [GATTACA] Bio-Voice: {tone_instruction}")

        except ImportError:
            pass

        # STANDARD VOICE GEN (Single Key)
        from corpus.brain.astrocyte import key_manager
        
        try:
            key = key_manager.get_active_key()
            client = genai.Client(api_key=key)
            response = await client.aio.models.generate_content(
                model=MODELS[self.ROUTE_VOICE],
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Kore"
                            )
                        ),
                        language_code=lang,
                    ),
                ),
            )

            if (
                response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts
            ):
                part = response.candidates[0].content.parts[0]
                if hasattr(part, "inline_data") and part.inline_data:
                    timestamp = int(time.time() * 1000)
                    audio_path = output_dir / f"tts_{timestamp}.wav"

                    await asyncio.to_thread(
                        self._save_file, audio_path, part.inline_data.data
                    )

                    logger.success(
                        f"✅ VOICE Studio: {audio_path.name}"
                    )

                    self._log_tokens(
                        "API Key",
                        self.ROUTE_VOICE,
                        prompt,
                        f"Generated TTS Audio: {audio_path.name}",
                        model=MODELS[self.ROUTE_VOICE],
                    )
                    return str(audio_path)
                    
        except Exception as e:
            logger.error(f"🗣️ TTS Failed: {e}")
            return f"ERROR: TTS Failed {e}"

        return "ERROR: TTS Failed (No Data)"
                            prompt,
                            f"Start: {prompt[:50]}... -> Audio: {audio_path.name} ({len(part.inline_data.data) if part.inline_data.data else 0} bytes)",
                            model=MODELS[self.ROUTE_VOICE],
                        )

                        return json.dumps(
                            {
                                "status": "ok",
                                "path": str(audio_path),
                                "mime_type": part.inline_data.mime_type,
                                "audio_size": len(part.inline_data.data)
                                if part.inline_data.data
                                else 0,
                            }
                        )
            except Exception as e:
                err_str = self._parse_error(e)
                # TRANSIENT ERRORS -> ROTATE
                if (
                    "429" in err_str
                    or "503" in err_str
                    or "UNAVAILABLE" in err_str
                    or "overloaded" in err_str.lower()
                    or "exhausted" in err_str.lower()
                    or "Cannot connect" in err_str
                    or "DNS" in err_str
                ):
                    key_manager.mark_429(key)
                    logger.info(
                        f"🔄 Transient VOICE Error (Attempt {attempt + 1}) -> Rotating..."
                    )
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error(f"☢️ VOICE Failed (TOXIC): {e}")
                    key_manager.quarantine_key(key, f"Voice Error: {e}")
                    continue

        return "ERROR: VOICE failed"

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 8: MEMORY (Embeddings)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _route_memory(self, text: str) -> str:
        """Generate embeddings via gemini-embedding-001."""
        # RETRY STRATEGY
        max_retries = min(len(_get_studio_keys()) * 2, 50)
        from corpus.brain.astrocyte import key_manager

        for attempt in range(max_retries):
            key = key_manager.get_active_key()
            try:
                client = genai.Client(api_key=key)
                response = await client.aio.models.embed_content(
                    model=MODELS[self.ROUTE_MEMORY], contents=text
                )
                if response.embeddings:
                    # ✅ SUCCESS -> ROTATE
                    key_manager.rotate()
                    return json.dumps(
                        {
                            "embedding": response.embeddings[0].values[:10]
                            if response.embeddings and response.embeddings[0].values
                            else [],
                            "dim": len(response.embeddings[0].values)
                            if response.embeddings and response.embeddings[0].values
                            else 0,
                        }
                    )
                return json.dumps({"error": "no embedding"})
            except Exception as e:
                err_str = str(e)
                if (
                    "429" in err_str
                    or "503" in err_str
                    or "exhausted" in err_str.lower()
                    or "Cannot connect" in err_str
                    or "DNS" in err_str
                    or "Service Unavailable" in err_str
                    or "overloaded" in err_str.lower()
                ):
                    key_manager.mark_429(key)
                    await asyncio.sleep(1)  # 🛑 BACKOFF: Prevent spin-lock
                    continue
                else:
                    logger.warning(f"⚠️ MEMORY failed: {e}")
                    key_manager.quarantine_key(key, f"Memory Error: {e}")
                    continue

        return json.dumps({"error": "MEMORY failed"})

    # ═══════════════════════════════════════════════════════════════════════════
    # FILES API HELPER (for VEO Face Lock)
    # ═══════════════════════════════════════════════════════════════════════════

    # Cache for uploaded file URI (valid 24h)
    _files_api_cache: dict = {}

    async def _upload_to_files_api(self, file_path: Path) -> Optional[str]:
        """
        SOTA 2026: Upload image to Gemini Files API for VEO referenceImages.
        Returns the file URI that can be used in Veo requests.

        Files API URIs expire after 24h but we re-upload before each generation.
        Cached within session to avoid duplicate uploads.
        """
        import time
        from corpus.brain.astrocyte import key_manager

        cache_key = str(file_path)
        cached = self._files_api_cache.get(cache_key)

        # Check cache (1h validity for safety margin)
        if cached and (time.time() - cached.get("timestamp", 0)) < 3600:
            logger.debug(f"📦 [FILES API] Using cached URI: {cached.get('uri')}")
            return cached.get("uri")

        if not file_path.exists():
            logger.error(f"❌ [FILES API] File not found: {file_path}")
            return None

        key = key_manager.get_active_key()

        try:
            # Use Gemini SDK for Files API
            from google import genai

            client = genai.Client(api_key=key)

            logger.info(f"📤 [FILES API] Uploading {file_path.name}...")
            uploaded = client.files.upload(file=str(file_path))

            if uploaded and uploaded.uri:
                # Cache the result
                self._files_api_cache[cache_key] = {
                    "uri": uploaded.uri,
                    "name": uploaded.name,
                    "timestamp": time.time(),
                }
                logger.success(f"✅ [FILES API] Uploaded: {uploaded.uri}")
                return uploaded.uri

        except Exception as e:
            logger.error(f"❌ [FILES API] Upload failed: {e}")

        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTES 7-8: VIDEO (VEO 3.1 with Native Audio)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _route_video(self, prompt: str, model: str, **kwargs) -> str:
        """
        Video generation via VEO 3.1 with native audio support.

        Features:
        - predictLongRunning async API
        - Native audio generation (generate_audio=True)
        - API key retry
        - SOTA 2026: Auto Face Lock via Files API

        Args:
            prompt: Video generation prompt (should include dialogue for audio)
            model: VEO model (veo-3.1-fast-generate-preview or veo-3.1-generate-preview)
            **kwargs: Optional params:
                - generate_audio: bool - Request native audio (default: True)
                - use_face_lock: bool - Auto-upload Trinity face for consistency (default: False)
        """
        import os
        import time
        from corpus.dna.genome import MEMORIES_DIR
        from google import genai
        from google.genai import types

        output_dir = MEMORIES_DIR / "youtuber" / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)

        use_face_lock = kwargs.get("use_face_lock", False)

        # SINGLE KEY MODE: VEO has limited credits - use env var if set
        veo_key_raw = os.environ.get("VEO_API_KEY")
        if not veo_key_raw:
            # CRITICAL: VEO MUST have dedicated keys (Standard 362.50.25)
            # NEVER fallback to internal key_manager - that causes cross-contamination
            logger.error("🚫 [VEO] VEO_API_KEY not set - VEO requires dedicated keys")
            return json.dumps(
                {
                    "status": "error",
                    "message": "VEO requires VEO_API_KEY environment variable",
                }
            )

        # SOTA 2026: Support multiple Veo keys (comma separated)
        if "," in veo_key_raw:
            import random

            veo_keys = [k.strip() for k in veo_key_raw.split(",") if k.strip()]
            veo_key = random.choice(veo_keys)
            logger.info(
                f"🎹 [VEO] Key Retry: {veo_key[:8]}... (Pool: {len(veo_keys)})"
            )
        else:
            veo_key = veo_key_raw

        try:
            client = genai.Client(api_key=veo_key)

            # Step 1: Upload/prepare reference images
            ref_images = []
            if use_face_lock:
                trinity_image = (
                    Path(__file__).parent.parent.parent
                    / "jobs"
                    / "youtuber"
                    / "assets"
                    / "trinity_9x16.jpg"
                )
                if trinity_image.exists():
                    logger.info(f"👤 [FACE LOCK] Loading {trinity_image.name}...")
                    try:
                        # Read image bytes directly - SDK properly handles this
                        image_bytes = trinity_image.read_bytes()
                        ref_images.append(
                            types.VideoGenerationReferenceImage(
                                image=types.Image(
                                    image_bytes=image_bytes, mime_type="image/jpeg"
                                ),
                                reference_type="asset",
                            )
                        )
                        logger.info("✅ [FACE LOCK] Reference image loaded")
                    except Exception as e:
                        logger.warning(
                            f"⚠️ [FACE LOCK] Load failed: {e} - continuing without"
                        )

            # Step 2: Generate video via SDK
            logger.info(
                f"🎬 [VEO 3.1] Starting generation with {len(ref_images)} reference images..."
            )

            config_kwargs = {"aspect_ratio": "9:16"}
            if ref_images:
                config_kwargs["reference_images"] = ref_images

            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                config=types.GenerateVideosConfig(**config_kwargs),
            )

            # Step 3: Poll for completion
            logger.info("🎬 [VEO 3.1] Operation started, polling...")
            max_polls = 60  # 5 minutes max

            for poll in range(max_polls):
                await asyncio.sleep(5)

                # Refresh operation status
                operation = client.operations.get(operation)

                if operation.done:
                    if operation.response and operation.response.generated_videos:
                        video = operation.response.generated_videos[0]
                        if video.video and video.video.uri:
                            # Download video
                            timestamp = int(time.time() * 1000)
                            video_path = output_dir / f"veo_{timestamp}.mp4"

                            async with httpx.AsyncClient(timeout=120) as http_client:
                                dl_resp = await http_client.get(
                                    video.video.uri,
                                    headers={"x-goog-api-key": veo_key},
                                    follow_redirects=True,
                                )
                                if dl_resp.status_code == 200:
                                    await asyncio.to_thread(
                                        self._save_file, video_path, dl_resp.content
                                    )
                                    logger.success(
                                        f"✅ [VEO 3.1] Video saved: {video_path.name}"
                                    )
                                    return json.dumps(
                                        {
                                            "status": "ok",
                                            "path": str(video_path),
                                            "has_audio": True,
                                        }
                                    )

                    logger.error("❌ [VEO 3.1] No video in response")
                    return json.dumps(
                        {"status": "error", "message": "No video generated"}
                    )

                if poll % 6 == 0:  # Log every 30s
                    logger.info(f"🎬 [VEO 3.1] Still generating... ({poll * 5}s)")

            logger.error("❌ [VEO 3.1] Timeout (5 min)")
            return json.dumps({"status": "error", "message": "VEO timeout"})

        except Exception as e:
            logger.error(f"🎬 [VEO] Failed: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    # ═══════════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 5: SEARCH (Google Search Grounding)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _route_search(self, prompt: str) -> str:
        """
        Text generation with Google Search grounding.
        Uses gemini-3-flash for speed + google_search tool for live data.
        """
        from google.genai.types import Tool, GoogleSearch

        model = MODELS[self.ROUTE_GROUNDING]  # gemini-3-flash-preview

        # RETRY STRATEGY (Persistent) - Aligned with other routes
        max_retries = min(len(_get_studio_keys()) * 2, 50)
        from corpus.brain.astrocyte import key_manager

        for attempt in range(max_retries):
            key = key_manager.get_active_key()
            try:
                client = genai.Client(api_key=key)
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={"tools": [Tool(google_search=GoogleSearch())]},  # type: ignore
                )
                result = response.text or ""
                self._log_tokens(
                    "API Key", self.ROUTE_GROUNDING, prompt, result, model=model
                )
                logger.success("🔍 [SEARCH] Grounded response via API Key")

                # ✅ SUCCESS -> ROTATE
                key_manager.rotate()
                return result

            except Exception as e:
                err_str = str(e)
                # TRANSIENT ERRORS -> ROTATE
                if (
                    "429" in err_str
                    or "503" in err_str
                    or "UNAVAILABLE" in err_str
                    or "overloaded" in err_str.lower()
                    or "exhausted" in err_str.lower()
                    or "Cannot connect" in err_str
                    or "DNS" in err_str
                ):
                    key_manager.mark_429(key)
                    logger.info(
                        f"🔄 Transient SEARCH Error (Attempt {attempt + 1}) -> Rotating... Error: {e}"
                    )
                    continue
                else:
                    logger.warning(f"⚠️ SEARCH failed: {e}")
                    key_manager.quarantine_key(key, f"Search Error: {e}")
                    continue

        # FALLBACK: Explicit Request -> Route 1
        logger.warning("⚠️ [GATTACA] SEARCH Keys Exhausted -> Fallback to ROUTE 1 (CLI)")
        # Note: Fallback loses "Live Search" capabilities
        return await self._route_cli(prompt)

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 9: CHAT (Agentic with Tools + Multi-turn)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _route_chat(self, prompt: str, **kwargs) -> str:
        """
        Agentic Chat Route with Tool Use (SOTA 2026).

        Features:
        - Multi-turn conversation support (via history)
        - Function calling / Tool use
        - Automatic token logging
        - Key retry

        Args:
            prompt: The user message
            **kwargs:
                - history: list[dict] - Conversation history
                - tools: list[dict] - Tool definitions (TRINITY_TOOLS format)
                - system_instruction: str - System context
                - files: list[dict] - Multimodal files
        """
        from google.genai import types
        from corpus.brain.astrocyte import key_manager

        model = MODELS[ROUTE_CHAT]
        history = kwargs.get("history", [])
        tools_config = kwargs.get("tools", [])
        system_instruction = kwargs.get("system_instruction", "")
        files = kwargs.get("files", [])

        max_retries = min(len(_get_studio_keys()) * 2, 50)
        max_tool_rounds = 5  # Allow more tool calls before forcing text response

        # === MEMORY COMPRESSION (SOTA 2026) ===
        # If history is long, summarize old messages to preserve context
        COMPRESSION_THRESHOLD = 20
        KEEP_RECENT = 10

        recent_history = history[-KEEP_RECENT:] if history else []
        compressed_summary = ""

        if len(history) > COMPRESSION_THRESHOLD:
            old_messages = history[:-KEEP_RECENT]

            # === COMPRESSION CACHE (SOTA 2026) ===
            # Hash old messages to check if we've already summarized this chunk
            import hashlib
            import json as json_module
            from corpus.dna.genome import MEMORIES_DIR

            cache_file = MEMORIES_DIR / "trinity" / "compression_cache.json"
            cache: dict = {}

            # Build hash of old messages
            old_text_for_hash = "".join(
                [
                    f"{m.get('role', '')}:{m.get('content', '')[:100]}"
                    for m in old_messages
                ]
            )
            message_hash = hashlib.sha256(old_text_for_hash.encode()).hexdigest()[:16]

            # Load existing cache
            try:
                if cache_file.exists():
                    cache = json_module.loads(cache_file.read_text())
            except Exception:
                cache = {}

            # Check cache first
            if message_hash in cache:
                compressed_summary = f"[CONTEXTE PRÉCÉDENT]: {cache[message_hash]}"
                logger.debug(f"💾 [CHAT] Cache hit for compression ({message_hash})")
            else:
                try:
                    # Build summary prompt
                    old_text = "\n".join(
                        [
                            f"[{m.get('role', '?')}]: {m.get('content', '')[:200]}"
                            for m in old_messages
                        ]
                    )
                    summary_prompt = (
                        "Résume cette conversation en 2-3 phrases. "
                        "Garde les informations importantes (noms, décisions, contexte):\n\n"
                        f"{old_text}"
                    )

                    # Use Flash (Route 2) for quick summarization
                    summary_response = await self._route_text(
                        summary_prompt,
                        model=MODELS[ROUTE_FLASH],
                        route_id=ROUTE_FLASH,
                        system_instruction="Tu es un assistant qui résume des conversations de manière concise.",
                    )

                    if summary_response and "ERROR" not in str(summary_response):
                        compressed_summary = f"[CONTEXTE PRÉCÉDENT]: {summary_response}"
                        logger.debug(
                            f"💾 [CHAT] Compressed {len(old_messages)} messages into summary"
                        )

                        # Save to cache (LRU: keep last 50 entries)
                        cache[message_hash] = summary_response
                        if len(cache) > 50:
                            # Remove oldest entries
                            keys = list(cache.keys())
                            for k in keys[: len(keys) - 50]:
                                del cache[k]

                        try:
                            cache_file.parent.mkdir(parents=True, exist_ok=True)
                            cache_file.write_text(json_module.dumps(cache, indent=2))
                        except Exception:
                            pass

                except Exception as e:
                    logger.warning(f"⚠️ [CHAT] Compression failed: {e}")
                    # Fallback: just use recent history

        # Build contents from history
        contents: list = []

        # Inject compressed summary first if available
        if compressed_summary:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=compressed_summary)],
                )
            )
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="Compris, j'ai le contexte.")],
                )
            )

        # Add recent history
        if recent_history:
            for msg in recent_history:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg.get("content", ""))],
                    )
                )

        # Add current message with potential files
        user_parts = [types.Part.from_text(text=prompt)]

        # Handle Multimodal Files
        if files:
            import base64

            for f in files:
                if isinstance(f, dict) and "data" in f and "mime_type" in f:
                    try:
                        data_bytes = base64.b64decode(f["data"])
                        user_parts.append(
                            types.Part.from_bytes(
                                data=data_bytes, mime_type=f["mime_type"]
                            )
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ [CHAT] File decode failed: {e}")

        contents.append(types.Content(role="user", parts=user_parts))

        # Convert tools to Gemini format
        function_declarations = []
        for tool in tools_config:
            function_declarations.append(
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=tool.get("parameters", {}),
                )
            )

        # Build config
        config_dict: dict = {"temperature": 0.7}
        if system_instruction:
            config_dict["system_instruction"] = system_instruction
        if function_declarations:
            config_dict["tools"] = [
                types.Tool(function_declarations=function_declarations)
            ]

        for attempt in range(max_retries):
            key = key_manager.get_active_key()
            try:
                client = genai.Client(api_key=key)

                # Initial request
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(**config_dict),
                )

                # Helper to extract text without triggering SDK warning
                def _extract_text_safe(resp) -> str:
                    """Extract text from response parts without triggering 'non-text parts' warning."""
                    if not resp.candidates:
                        return ""
                    candidate = resp.candidates[0]
                    if not candidate.content or not candidate.content.parts:
                        return ""
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            text_parts.append(part.text)
                    return "".join(text_parts)

                # Track tokens for this generation
                in_text = prompt
                out_text = _extract_text_safe(response)

                # Handle tool calls (agentic loop)
                tool_round = 0
                while response.candidates and tool_round < max_tool_rounds:
                    candidate = response.candidates[0]

                    # Check for function calls
                    function_calls = []
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, "function_call") and part.function_call:
                                function_calls.append(part.function_call)

                    if not function_calls:
                        break  # No tool calls, we're done

                    logger.info(
                        f"🔧 [CHAT] Tool calls: {[fc.name for fc in function_calls]}"
                    )

                    # Execute tools (import from neocortex tools)
                    from corpus.brain.effectors import execute_tool

                    tool_results = []
                    for fc in function_calls:
                        result = await execute_tool(fc.name, fc.args or {})
                        tool_results.append(
                            types.Part.from_function_response(
                                name=fc.name, response={"result": result}
                            )
                        )

                    # Add model response and tool results to conversation
                    contents.append(candidate.content)
                    contents.append(types.Content(role="user", parts=tool_results))

                    # Continue generation
                    response = await client.aio.models.generate_content(
                        model=model,
                        contents=contents,
                        config=types.GenerateContentConfig(**config_dict),
                    )

                    # Update output text for logging
                    out_text = _extract_text_safe(response) or out_text
                    tool_round += 1

                # SOTA 2026: If we hit max_tool_rounds without text, force a final text response
                final_text = _extract_text_safe(response)
                if not final_text and tool_round >= max_tool_rounds:
                    logger.warning(
                        "⚠️ [CHAT] Max tool rounds hit, forcing text response"
                    )
                    # Remove tools from config to force text-only response
                    force_text_config = {
                        k: v for k, v in config_dict.items() if k != "tools"
                    }
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(
                                    text="Réponds maintenant à ma question avec les informations obtenues."
                                )
                            ],
                        )
                    )
                    response = await client.aio.models.generate_content(
                        model=model,
                        contents=contents,
                        config=types.GenerateContentConfig(**force_text_config),
                    )
                    final_text = _extract_text_safe(response)
                    out_text = final_text or out_text

                # ✅ SUCCESS - Log tokens and rotate
                self._log_tokens(
                    provider="API Key",
                    route_id=ROUTE_CHAT,
                    input_text=in_text,
                    output_text=out_text,
                    model=model,
                    source_override=kwargs.get("source", "CHAT"),
                )
                key_manager.rotate()

                return final_text if final_text else "*Silence...*"

            except Exception as e:
                err_str = self._parse_error(e)
                if (
                    "429" in err_str
                    or "503" in err_str
                    or "UNAVAILABLE" in err_str
                    or "overloaded" in err_str.lower()
                    or "exhausted" in err_str.lower()
                ):
                    key_manager.mark_429(key)
                    logger.info(
                        f"🔄 Transient CHAT Error (Attempt {attempt + 1}) -> Rotating..."
                    )
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.warning(f"⚠️ CHAT failed: {e}")
                    key_manager.quarantine_key(key, f"Chat Error: {e}")
                    continue

        return "*Connexion impossible*"

    # ═══════════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 6: DESIGN (Banana Pro - Logic/Reasoning Image)
    # ═══════════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILS
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_file(self, path: Path, data: Optional[bytes]) -> None:
        """Helper to save binary files in a thread-safe way (via to_thread)."""
        if data is None:
            return
        with open(path, "wb") as f:
            f.write(data)

    def _get_credential_json(self, key_var: str) -> Optional[str]:
        """Extract credential JSON from .env."""
        try:
            if not self.env_path.exists():
                return None
            content = self.env_path.read_text(encoding="utf-8")
            match = re.search(f'{key_var}="?([^"\n]+)"?', content)
            if match:
                return base64.b64decode(match.group(1)).decode("utf-8")
        except Exception as e:
            logger.error(f"❌ Credential error: {e}")
        return None

    def _log_tokens(
        self,
        provider: str,
        route_id: int,
        input_text: str,
        output_text: str,
        model: str = "unknown",
        key_id: str = "N/A",
        source_override: Optional[str] = None,
    ):
        """Log token usage with harmonized metadata."""
        try:
            # 1. Resolve Metadata
            meta = ROUTE_METADATA.get(
                route_id, {"icon": "❓", "color": "white", "name": "UNKNOWN"}
            )

            # 2. Resolve Source (Caller) - SOTA 2026: File + Function tracking
            if source_override:
                source = source_override
            else:
                # Walk the stack to find the REAL caller (not gattaca internals or asyncio noise)
                source = "GATTACA"
                caller_func = ""
                try:
                    import inspect

                    stack = inspect.stack()
                    # Skip system/internal frames, find first meaningful caller
                    ignored_files = {
                        "gattaca.py",
                        "processing.py",
                        "logging.py",
                        "tasks.py",
                        "base_events.py",
                        "runners.py",
                        "events.py",
                        "__init__.py",
                    }

                    for i, frame in enumerate(stack):
                        filename = os.path.basename(frame.filename)
                        func_name = frame.function

                        # Skip internal gattaca methods
                        if filename == "gattaca.py" and func_name.startswith("_"):
                            continue

                        # Skip system/async noise
                        if filename in ignored_files or "asyncio" in frame.filename:
                            continue

                        # Found real caller!
                        source = filename.replace(".py", "").upper()
                        caller_func = func_name
                        break

                    # Append function name if found (e.g., "NERVES:pulse")
                    if caller_func and caller_func not in {
                        "<module>",
                        "route",
                        "think",
                    }:
                        source = f"{source}:{caller_func}"

                except Exception:
                    pass

            # 3. Calculate Tokens
            in_tok = len(input_text) // 4
            out_tok = len(output_text) // 4
            total = in_tok + out_tok

            # 4. JSONL Entry (SOTA 2026: Extension Compatible)
            entry = {
                "timestamp": datetime.now().isoformat(),  # CANONICAL: ISO 8601 unique key
                "level": "INFO",  # Required for extension log display
                "model": model,
                "route_id": route_id,
                "route": meta["name"],
                "icon": meta["icon"],
                "key": key_id if key_id != "N/A" else provider,
                "source": source,
                "in": in_tok,
                "out": out_tok,
                "total": total,
                "message": f"{meta['icon']} {model} | {meta['name']} | in:{in_tok} out:{out_tok} = {total}",
            }

            TOKENS_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKENS_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

            # 5. Console Log (DEBUG to avoid system.jsonl duplication)
            tag = f"[{meta['icon']} {meta['name']}]"
            safe_source = str(source).replace("<", "\\<").replace(">", "\\>")
            logger.opt(colors=True).debug(
                f"<{meta['color']}>{tag:<12}</{meta['color']}> │ "
                f"<cyan>{model:<20}</cyan> │ "
                f"Src: {safe_source:<10} │ "
                f"In: {in_tok} Out: {out_tok} = <bold>{total}</bold>"
            )

        except Exception as e:
            logger.error(f"Log Error: {e}")


# Singleton
gattaca = GattacaRouter()

# Legacy aliases
ROUTE_THOUGHT = ROUTE_FLASH
ROUTE_SIGHT = ROUTE_IMAGE
ROUTE_INSIGHT = ROUTE_IMAGE
