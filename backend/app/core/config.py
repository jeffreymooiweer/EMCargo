from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    app_name: str = "EMCargo"
    app_env: str = "production"
    #: Initial shipment retention setting, overridden by saved settings.
    #: EMCARGO_MODE is retired: every installation requires an account.
    emcargo_history: bool = False
    app_secret_key: str = "change-me"
    database_url: str = "sqlite:////data/emcargo.db"
    data_dir: Path = Path("/data")
    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    log_level: str = "INFO"
    cargo_max_units: int = 2000
    cargo_max_allocations: int = 50000
    cargo_max_depth: int = 20
    # The bundled interface uses the same origin as its API and needs no
    # cross-origin permission. External interfaces must be named explicitly.
    cors_allowed_origins: str = ""
    # Directly exposed instances must not let a caller choose its rate-limit
    # bucket or the URLs sent in password-reset mail through forwarded headers.
    trusted_proxy_headers: bool = False
    #: How many reverse proxies stand in front of the application. It decides
    #: which entry of ``X-Forwarded-For`` a rate limit is counted against: one
    #: position from the right per proxy, because a proxy appends what it saw
    #: and everything further left was put there by the caller. One nginx or
    #: Traefik in front is 1, which is the common case; a CDN in front of that
    #: is 2. Too low a number keys the limit on a value the caller chooses.
    trusted_proxy_count: int = 1
    access_token_expire_minutes: int = 480
    cookie_secure: bool | None = None
    catalog_auto_sync: bool = True
    catalog_sync_timeout_seconds: float = 20.0
    update_check_enabled: bool = True
    update_check_timeout_seconds: float = 8.0
    #: In-app updates are always enabled for administrators. Capability depends
    #: on the installation and Docker socket access, not an environment switch.
    update_apply_pull_timeout_seconds: float = 600.0
    #: How this installation was put on its host: ``docker`` (the image, the
    #: default), ``native`` (the systemd service of deploy/native) or
    #: ``kubernetes`` (deploy/kubernetes). It decides nothing but what the
    #: settings screen says about updating: the in-app updater replaces a
    #: container through the Docker socket, and the other two routes have
    #: their own — the update script, the rollout — which the screen names
    #: instead of offering a button that cannot work.
    install_method: str = "docker"
    geo_address_api_url: str = "https://photon.komoot.io/api"
    geo_address_timeout_seconds: float = 8.0
    #: The mail server, for installations that would rather configure it in
    #: the environment than in the screen. Empty host means no mail server is
    #: configured, which is the default: EMCargo sends nothing until an
    #: administrator says where to send it.
    smtp_host: str = ""
    smtp_port: int = 587
    #: "starttls" (the usual port 587), "ssl" (the implicit TLS of port 465),
    #: or "none" for a relay on the local network that expects no encryption.
    smtp_security: str = "starttls"
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = ""
    smtp_timeout_seconds: float = 15.0
    #: The switches an administrator would otherwise flip on the settings
    #: screen. Environment variables provide the starting values until
    #: an administrator saves an override.
    default_language: str = "nl"
    default_theme: str = "dark"
    address_lookup_enabled: bool = True
    un_cards_enabled: bool = True
    #: Whether documents carry a QR code that opens this installation's UN
    #: cards without signing in. Off by default; see ``docs/privacy.md``.
    card_links_enabled: bool = False
    #: The address the installation is reached on, for the links in those QR
    #: codes and in outgoing mail. Empty means: read it from the request.
    public_url: str = ""
    #: What the screen calls itself. Empty means EMCargo. The logo and the
    #: tile images beside it are files in ``DATA_DIR/branding``, uploaded from
    #: the settings screen or placed there by the operator.
    brand_name: str = ""

    @property
    def templates_dir(self) -> Path:
        return self.data_dir / "templates"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def seed_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "seed"

    @property
    def config_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "config"

    @property
    def static_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "static"

    @property
    def repo_templates_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / ".." / "templates"

    @property
    def cors_origins(self) -> list[str]:
        if self.cors_allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def secure_cookies(self) -> bool:
        """Use Secure cookies by default outside local development and tests.

        ``COOKIE_SECURE`` remains an explicit escape hatch for unusual reverse
        proxy setups, but a production installation no longer silently emits a
        session cookie that browsers may send over plain HTTP.
        """
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.app_env.strip().lower() not in {"test", "development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
