"""Thin requests wrappers around Microsoft Graph API and Teams internal API."""
import requests

from m365.auth import token_store
from m365 import fmt


class GraphClient:
    BASE = "https://graph.microsoft.com/v1.0"

    def _headers(self) -> dict:
        tok = token_store.get_token()
        if not tok:
            raise SystemExit("Not logged in. Run: m365 login")
        if token_store.is_expired():
            raise SystemExit("Token expired. Run: m365 login")
        return {"Authorization": f"Bearer {tok}"}

    def get(self, path: str, params: dict = None) -> dict:
        resp = requests.get(f"{self.BASE}{path}", headers=self._headers(), params=params)
        return self._handle(resp)

    def post(self, path: str, json: dict = None) -> dict:
        resp = requests.post(f"{self.BASE}{path}", headers=self._headers(), json=json)
        return self._handle(resp)

    def patch(self, path: str, json: dict = None) -> dict:
        resp = requests.patch(f"{self.BASE}{path}", headers=self._headers(), json=json)
        return self._handle(resp)

    def put(self, path: str, data: bytes = None, json: dict = None) -> dict:
        headers = self._headers()
        if data is not None:
            headers["Content-Type"] = "application/octet-stream"
            resp = requests.put(f"{self.BASE}{path}", headers=headers, data=data)
        else:
            resp = requests.put(f"{self.BASE}{path}", headers=headers, json=json)
        return self._handle(resp)

    def _handle(self, resp: requests.Response) -> dict:
        if resp.status_code == 401:
            raise SystemExit("Token expired or invalid. Run: m365 login")
        if resp.status_code == 403:
            raise SystemExit(
                f"Insufficient permissions: {resp.json().get('error', {}).get('message', resp.text)}"
            )
        if resp.status_code == 404:
            raise SystemExit(
                f"Not found: {resp.json().get('error', {}).get('message', resp.text)}"
            )
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()


class TeamsClient:
    """Client for the Teams internal chatsvc API — same API the Teams web app uses."""

    REGIONS = ["emea", "amer", "apac", "noam"]

    def _base(self) -> str:
        region = token_store.load().get("teams_region", "amer") if token_store.load() else "amer"
        return f"https://teams.microsoft.com/api/chatsvc/{region}/v1"

    def _headers(self) -> dict:
        tok = token_store.get_teams_token()
        if not tok:
            raise SystemExit(
                "No Teams IC3 token found. Run: m365 login (on teams.microsoft.com)"
            )
        return {
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "clientinfo": "os=mac; osVer=10.15; proc=x86; lcid=en-us; deviceType=1; country=us; clientName=skypeteams; clientVer=1415/26011511119; utcOffset=-07:00; timezone=America/Los_Angeles",
            "behavioroverride": "redirectAs404",
            "x-ms-migration": "True",
            "Origin": "https://teams.microsoft.com",
            "Referer": "https://teams.microsoft.com/",
        }

    def get(self, path: str, params: dict = None) -> dict:
        # Try stored region first, fall back through all regions on 404
        data = token_store.load() or {}
        stored_region = data.get("teams_region")
        regions = [stored_region] + [r for r in self.REGIONS if r != stored_region] if stored_region else self.REGIONS

        for region in regions:
            base = f"https://teams.microsoft.com/api/chatsvc/{region}/v1"
            resp = requests.get(f"{base}{path}", headers=self._headers(), params=params)
            if resp.status_code == 200:
                if region != stored_region:
                    data["teams_region"] = region
                    token_store.save(data)
                return resp.json()
            if resp.status_code not in (404, 302):
                self._handle(resp)
        self._handle(resp)

    def post(self, path: str, json: dict = None) -> dict:
        base = self._base()
        resp = requests.post(f"{base}{path}", headers=self._headers(), json=json)
        self._handle(resp)
        return resp.json() if resp.text else {}

    def _handle(self, resp: requests.Response):
        if resp.status_code == 401:
            raise SystemExit("Teams token expired. Run: m365 login on teams.microsoft.com")
        if resp.status_code not in (200, 201):
            raise SystemExit(f"Teams API error {resp.status_code}: {resp.text[:500]}")
