"""
API client for worldcup26.ir - Free World Cup 2026 data API.
Requires JWT authentication for data endpoints.
"""

import requests
from typing import Optional, List, Dict

BASE_URL = "https://worldcup26.ir"


class ApiClient:
    """Client for the worldcup26.ir API with auto-authentication."""

    def __init__(self, timeout: int = 15, email: str = None, password: str = None):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "WorldCupPredictor/1.0"})
        self._token: Optional[str] = None
        # Use provided credentials or auto-generate
        self._email = email or "predictor@fifa2026.com"
        self._password = password or "Predict2026!"

    def _ensure_auth(self):
        """Ensure we have a valid JWT token."""
        if self._token:
            return
        print("[INFO] Authenticating with worldcup26.ir API...")
        # Try to login first
        if not self._login():
            # Register if login fails
            self._register()
            self._login()

    def _register(self) -> bool:
        """Register a new user."""
        try:
            resp = self._session.post(
                f"{BASE_URL}/auth/register",
                json={
                    "name": "WorldCup Predictor Agent",
                    "email": self._email,
                    "password": self._password,
                },
                timeout=self.timeout,
            )
            if resp.status_code in (200, 201):
                print(f"[INFO] Registered user: {self._email}")
                return True
            else:
                print(f"[WARN] Registration returned {resp.status_code}: {resp.text[:100]}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Registration failed: {e}")
            return False

    def _login(self) -> bool:
        """Login and store JWT token."""
        try:
            resp = self._session.post(
                f"{BASE_URL}/auth/authenticate",
                json={
                    "email": self._email,
                    "password": self._password,
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                self._token = data.get("token")
                if self._token:
                    self._session.headers.update({
                        "Authorization": f"Bearer {self._token}"
                    })
                    print("[INFO] Authenticated successfully.")
                    return True
            print(f"[WARN] Login returned {resp.status_code}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Login failed: {e}")
            return False

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[Dict]:
        """Make an authenticated GET request."""
        self._ensure_auth()

        url = f"{BASE_URL}{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 401:
                # Token expired - re-authenticate and retry once
                print("[WARN] Token expired, re-authenticating...")
                self._token = None
                self._ensure_auth()
                resp = self._session.get(url, params=params, timeout=self.timeout)

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            print(f"[WARN] API timeout: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"[WARN] API HTTP error {e.response.status_code}: {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[WARN] API request failed: {url} - {e}")
            return None
        except ValueError as e:
            print(f"[WARN] API invalid JSON: {url} - {e}")
            return None

    # --- Data endpoints ---

    def get_groups(self) -> Optional[List]:
        """Get all groups (A-L)."""
        data = self._get("/get/groups")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("groups", data.get("data", []))
        return None

    def get_group(self, name: str) -> Optional[Dict]:
        """Get a specific group by name (A-L)."""
        return self._get("/get/group", params={"name": name.upper()})

    def get_teams(self, group: Optional[str] = None) -> Optional[List]:
        """Get all teams, optionally filtered by group."""
        params = {}
        if group:
            params["group"] = group.upper()
        data = self._get("/get/teams", params=params)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("teams", data.get("data", []))
        return None

    def get_team(self, identifier) -> Optional[Dict]:
        """Get team by ID or name."""
        if isinstance(identifier, str) and len(identifier) > 24:
            return self._get(f"/get/team/{identifier}")
        else:
            return self._get("/get/team", params={"name": identifier})

    def get_games(self) -> Optional[List]:
        """Get all games/matches."""
        data = self._get("/get/games")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("games", data.get("matches", data.get("data", [])))
        return None

    def get_game(self, game_id) -> Optional[Dict]:
        """Get a specific game by ID."""
        return self._get(f"/get/game/{game_id}")

    def get_stadiums(self) -> Optional[List]:
        """Get all stadiums."""
        data = self._get("/get/stadiums")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("stadiums", data.get("data", []))
        return None

    def health_check(self) -> Optional[Dict]:
        """Check API health."""
        try:
            resp = self._session.get(f"{BASE_URL}/health", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.exceptions.RequestException:
            return None

    def close(self):
        self._session.close()
