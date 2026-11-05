import json
import logging
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from health_app.config import settings

logger = logging.getLogger(__name__)

FITNESS_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
]


class GoogleOAuthManager:
    """Manages Google OAuth2 authentication flow and token exchange."""

    def __init__(self, client_secret_path: Optional[Path] = None):
        self.client_secret_path = client_secret_path or settings.find_client_secret_file()
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
        self.token_uri: str = "https://oauth2.googleapis.com/token"
        self.redirect_uri: str = f"http://{settings.dashboard_host}:{settings.dashboard_port}/api/auth/google/callback"
        self.configured: bool = False

        self._load_credentials()

    def _load_credentials(self) -> None:
        """Parse client secret JSON file if available."""
        if not self.client_secret_path or not self.client_secret_path.exists():
            logger.warning("No Google client secret file located.")
            return

        try:
            with open(self.client_secret_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both 'web' and 'installed' OAuth client types
            conf = data.get("web") or data.get("installed") or {}
            self.client_id = conf.get("client_id")
            self.client_secret = conf.get("client_secret")
            self.auth_uri = conf.get("auth_uri", self.auth_uri)
            self.token_uri = conf.get("token_uri", self.token_uri)

            # Select matching redirect URI from configured redirect_uris
            configured_uris = conf.get("redirect_uris", [])
            for uri in configured_uris:
                if str(settings.dashboard_port) in uri:
                    self.redirect_uri = uri
                    break
            else:
                if configured_uris:
                    self.redirect_uri = configured_uris[0]

            if self.client_id and self.client_secret:
                self.configured = True
                logger.info(f"Google OAuth initialized with Client ID: {self.client_id[:20]}...")
        except Exception as e:
            logger.error(f"Failed to parse Google client secret JSON: {e}")

    def get_authorization_url(self, state: str = "default_state", force_consent: bool = False) -> str:
        """Construct the Google OAuth2 authorization URL.
        Defaults to prompt='select_account' so users choose their account without repeatedly re-granting
        permissions they already granted in the past.
        """
        if not self.configured:
            raise ValueError(
                "Google OAuth is not configured. Please ensure your client secret JSON is placed in the project root."
            )

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(FITNESS_SCOPES),
            "access_type": "offline",
            "prompt": "consent" if force_consent else "select_account",
            "state": state,
        }
        return f"{self.auth_uri}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        if not self.configured:
            raise ValueError("Google OAuth credentials are not configured.")

        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        resp = requests.post(self.token_uri, data=data, timeout=12)
        if resp.status_code != 200:
            error_msg = resp.text
            try:
                error_msg = resp.json().get("error_description", resp.text)
            except Exception:
                pass
            raise RuntimeError(f"Google Token Exchange Failed: {error_msg}")

        return resp.json()

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch basic Google user profile (name, email, picture)."""
        url = "https://www.googleapis.com/oauth2/v2/userinfo"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=8
        )
        if resp.status_code == 200:
            return resp.json()
        return {
            "name": "Health App User",
            "email": "user@example.com",
            "picture": "https://lh3.googleusercontent.com/a/default-user"
        }
