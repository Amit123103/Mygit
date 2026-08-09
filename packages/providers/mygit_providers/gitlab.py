from typing import Dict, List, Optional
import httpx


class GitLabProvider:
    """GitLab API v4 provider."""

    def __init__(self, token: Optional[str] = None, host: str = "https://gitlab.com"):
        self.token = token
        self.base_url = f"{host.rstrip('/')}/api/v4"
        self.headers = {"User-Agent": "MyGit-App"}
        if token:
            self.headers["PRIVATE-TOKEN"] = token

    def create_project(self, name: str, description: str = "", private: bool = True) -> Dict:
        visibility = "private" if private else "public"
        payload = {"name": name, "description": description, "visibility": visibility}
        with httpx.Client(headers=self.headers, timeout=10.0) as client:
            resp = client.post(f"{self.base_url}/projects", json=payload)
            if resp.status_code == 201:
                return resp.json()
            raise RuntimeError(f"Failed to create GitLab project: {resp.text}")
