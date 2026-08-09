from typing import Dict, List, Optional
import httpx


class HuggingFaceProvider:
    """Hugging Face Hub provider for Code, Model, and Dataset repos."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://huggingface.co/api"
        self.headers = {"User-Agent": "MyGit-App"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def create_repo(self, repo_name: str, repo_type: str = "model", private: bool = False) -> Dict:
        """repo_type can be 'model', 'dataset', or 'space'."""
        url = f"{self.base_url}/repos/create"
        payload = {"name": repo_name, "type": repo_type, "private": private}
        with httpx.Client(headers=self.headers, timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code in (200, 201):
                return resp.json()
            raise RuntimeError(f"Failed to create Hugging Face repo: {resp.text}")
