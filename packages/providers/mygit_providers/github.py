from typing import Dict, List, Optional
import httpx


class GitHubProvider:
    """GitHub API integration provider."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MyGit-App",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    def get_user_info(self) -> Dict:
        """Fetch current authenticated GitHub user profile."""
        with httpx.Client(headers=self.headers, timeout=10.0) as client:
            resp = client.get(f"{self.base_url}/user")
            if resp.status_code == 200:
                return resp.json()
            raise RuntimeError(f"GitHub Auth Error: HTTP {resp.status_code}")

    def create_repository(self, name: str, description: str = "", private: bool = False) -> Dict:
        """Create a new repository on GitHub."""
        payload = {"name": name, "description": description, "private": private}
        with httpx.Client(headers=self.headers, timeout=10.0) as client:
            resp = client.post(f"{self.base_url}/user/repos", json=payload)
            if resp.status_code == 201:
                return resp.json()
            raise RuntimeError(f"Failed to create GitHub repository: {resp.text}")

    def list_repositories(self) -> List[Dict]:
        """List authenticated user's repositories."""
        with httpx.Client(headers=self.headers, timeout=10.0) as client:
            resp = client.get(f"{self.base_url}/user/repos?sort=updated")
            if resp.status_code == 200:
                return resp.json()
            return []
