"""
CORPUS/DNA/CONFIG.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: TRINITY CONFIGURATION 🎛️
PURPOSE: Centralized, typed configuration for Trinity core.
      Persisted in memories/trinity/config.json.
      Exposed via API for Web/Android interfaces.
══════════════════════════════════════════════════════════════════════════════
"""

import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger

from corpus.dna.genome import MEMORIES_DIR

# ════════════════════════════════════════════════════════════════════════════
# CONFIG FILE PATH
# ════════════════════════════════════════════════════════════════════════════

CONFIG_DIR = MEMORIES_DIR / "trinity"
CONFIG_FILE = CONFIG_DIR / "config.json"

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURATION MODELS
# ════════════════════════════════════════════════════════════════════════════


class BootConfig(BaseModel):
    """Configuration du démarrage Trinity."""

    send_greeting: bool = Field(
        default=True, description="Envoyer message de bonjour au démarrage"
    )
    greeting_use_ai: bool = Field(
        default=True, description="Utiliser l'IA pour le message (vs template)"
    )
    greeting_with_photo: bool = Field(
        default=False, description="Joindre une photo au message"
    )


class SchedulerConfig(BaseModel):
    """Configuration du scheduler (routines circadiennes)."""

    morning_reflection_enabled: bool = Field(
        default=True, description="Activer la réflexion matinale"
    )
    morning_reflection_hour: int = Field(
        default=6, description="Heure de la réflexion (0-23)"
    )
    wakeup_enabled: bool = Field(
        default=True, description="Activer le message de réveil"
    )
    wakeup_hour: int = Field(default=8, description="Heure du réveil")
    noon_check_enabled: bool = Field(default=True, description="Activer le check midi")
    night_mode_enabled: bool = Field(default=True, description="Activer le mode nuit")
    night_mode_hour: int = Field(default=22, description="Heure du coucher")
    periodic_reports_enabled: bool = Field(
        default=True, description="Activer les rapports périodiques jobs"
    )
    periodic_reports_interval_min: int = Field(
        default=89, description="Intervalle en minutes (F89)"
    )


class AvatarConfig(BaseModel):
    """Configuration des selfies/avatars."""

    selfie_enabled: bool = Field(
        default=True, description="Activer la génération de selfies"
    )
    selfie_weekly_limit: int = Field(
        default=1, description="Limite de selfies par semaine"
    )
    selfie_prompt_template: str = Field(
        default="Selfie de Trinity, cyberpunk aesthetic, digital art",
        description="Template prompt pour les selfies",
    )


class NotificationConfig(BaseModel):
    """Configuration des notifications."""

    send_urgent: bool = Field(default=True, description="Envoyer les alertes URGENT")
    send_errors: bool = Field(default=True, description="Envoyer les erreurs")
    send_success: bool = Field(default=True, description="Envoyer les succès")
    send_periodic: bool = Field(
        default=True, description="Envoyer les rapports périodiques"
    )
    quiet_hours_enabled: bool = Field(
        default=True, description="Mode silencieux la nuit"
    )
    quiet_hours_start: int = Field(default=23, description="Début heures calmes")
    quiet_hours_end: int = Field(default=7, description="Fin heures calmes")


class JobsConfig(BaseModel):
    """Configuration des jobs actifs."""

    active_jobs: List[str] = Field(
        default=["trader"], description="Jobs actuellement actifs"
    )
    available_jobs: List[str] = Field(
        default=["trader", "creator", "artisan"],
        description="Tous les jobs disponibles",
    )


class AxonConfig(BaseModel):
    """Configuration du dispatcher intelligent (routing messages)."""

    enabled: bool = Field(
        default=True, description="Activer le routing intelligent via Route 11"
    )
    use_classifier: bool = Field(
        default=True, description="Utiliser le classifier IA (vs keywords)"
    )
    fallback_to_info: bool = Field(
        default=True, description="Fallback vers INFO si erreur classifier"
    )
    action_confirmation: bool = Field(
        default=False, description="Demander confirmation avant action"
    )
    log_classifications: bool = Field(
        default=True, description="Logger les classifications"
    )


class TrinityConfig(BaseModel):
    """Configuration complète de Trinity."""

    version: str = Field(default="1.0.0", description="Version du schema config")
    angel_provider_url: str = Field(
        default="http://127.0.0.1:8089", description="URL du monitoring Angel"
    )
    language: str = Field("fr", description="Langue principale (fr/en)")
    boot: BootConfig = Field(default_factory=lambda: BootConfig())
    scheduler: SchedulerConfig = Field(default_factory=lambda: SchedulerConfig())
    avatar: AvatarConfig = Field(default_factory=lambda: AvatarConfig())
    notifications: NotificationConfig = Field(
        default_factory=lambda: NotificationConfig()
    )
    jobs: JobsConfig = Field(default_factory=lambda: JobsConfig())
    axon: AxonConfig = Field(default_factory=lambda: AxonConfig())


# ════════════════════════════════════════════════════════════════════════════
# CONFIG MANAGER
# ════════════════════════════════════════════════════════════════════════════


class ConfigManager:
    """
    Gestionnaire de configuration Trinity.
    Charge, sauvegarde et expose la configuration.
    """

    def __init__(self):
        self._config: TrinityConfig = TrinityConfig(
            version="1.0.0", angel_provider_url="http://127.0.0.1:8089", language="fr"
        )
        self._load()

    def _load(self):
        """Charge la config depuis le fichier JSON."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config = TrinityConfig(**data)
                logger.info("🎛️ Config loaded")
            except Exception as e:
                logger.warning(f"🎛️ [CONFIG] Failed to load, using defaults: {e}")
                self._config = TrinityConfig(
                    version="1.0.0",
                    angel_provider_url="http://127.0.0.1:8089",
                    language="fr",
                )
                self._save()
        else:
            logger.info("🎛️ [CONFIG] No config file, creating defaults")
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self._config = TrinityConfig(
                version="1.0.0",
                angel_provider_url="http://127.0.0.1:8089",
                language="fr",
            )
            self._save()

    def _save(self):
        """Sauvegarde la config dans le fichier JSON."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config.model_dump(), f, indent=2, ensure_ascii=False)
            logger.debug(f"🎛️ [CONFIG] Saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"🎛️ [CONFIG] Save failed: {e}")

    def reload(self):
        """Recharge la config depuis le fichier."""
        self._load()

    @property
    def config(self) -> TrinityConfig:
        """Retourne la config courante."""
        return self._config

    # ════════════════════════════════════════════════════════════════════════
    # SECTION GETTERS
    # ════════════════════════════════════════════════════════════════════════

    @property
    def boot(self) -> BootConfig:
        return self._config.boot

    @property
    def scheduler(self) -> SchedulerConfig:
        return self._config.scheduler

    @property
    def avatar(self) -> AvatarConfig:
        return self._config.avatar

    @property
    def notifications(self) -> NotificationConfig:
        return self._config.notifications

    @property
    def jobs(self) -> JobsConfig:
        return self._config.jobs

    @property
    def axon(self) -> AxonConfig:
        return self._config.axon

    @property
    def angel_provider_url(self) -> str:
        return self._config.angel_provider_url

    # ════════════════════════════════════════════════════════════════════════
    # SECTION UPDATERS
    # ════════════════════════════════════════════════════════════════════════

    def update_boot(self, **kwargs) -> BootConfig:
        """Met à jour la section boot."""
        self._config.boot = self._config.boot.model_copy(update=kwargs)
        self._save()
        return self._config.boot

    def update_scheduler(self, **kwargs) -> SchedulerConfig:
        """Met à jour la section scheduler."""
        self._config.scheduler = self._config.scheduler.model_copy(update=kwargs)
        self._save()
        return self._config.scheduler

    def update_avatar(self, **kwargs) -> AvatarConfig:
        """Met à jour la section avatar."""
        self._config.avatar = self._config.avatar.model_copy(update=kwargs)
        self._save()
        return self._config.avatar

    def update_notifications(self, **kwargs) -> NotificationConfig:
        """Met à jour la section notifications."""
        self._config.notifications = self._config.notifications.model_copy(
            update=kwargs
        )
        self._save()
        return self._config.notifications

    def update_jobs(self, **kwargs) -> JobsConfig:
        """Met à jour la section jobs."""
        self._config.jobs = self._config.jobs.model_copy(update=kwargs)
        self._save()
        return self._config.jobs

    # ════════════════════════════════════════════════════════════════════════
    # JOBS HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def is_job_active(self, job_name: str) -> bool:
        """Vérifie si un job est actif."""
        return job_name in self._config.jobs.active_jobs

    def activate_job(self, job_name: str) -> bool:
        """Active un job."""
        if job_name not in self._config.jobs.available_jobs:
            return False
        if job_name not in self._config.jobs.active_jobs:
            self._config.jobs.active_jobs.append(job_name)
            self._save()
        return True

    def deactivate_job(self, job_name: str) -> bool:
        """Désactive un job."""
        if job_name in self._config.jobs.active_jobs:
            self._config.jobs.active_jobs.remove(job_name)
            self._save()
            return True
        return False

    # ════════════════════════════════════════════════════════════════════════
    # API HELPERS (for FastAPI endpoints)
    # ════════════════════════════════════════════════════════════════════════

    def to_dict(self) -> Dict[str, Any]:
        """Export config as dict (for API)."""
        return self._config.model_dump()

    def update_section(self, section: str, data: Dict[str, Any]) -> bool:
        """Update a specific section by name."""
        updaters = {
            "boot": self.update_boot,
            "scheduler": self.update_scheduler,
            "avatar": self.update_avatar,
            "notifications": self.update_notifications,
            "jobs": self.update_jobs,
        }
        if section in updaters:
            updaters[section](**data)
            return True
        return False


# ════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════════

trinity_config = ConfigManager()
