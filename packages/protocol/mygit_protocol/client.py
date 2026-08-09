from typing import Dict, List, Optional, Tuple
import httpx

from mygit_core.objects import GitObject, ObjectStore
from mygit_core.repository import Repository


class ProtocolClient:
    """Client for MyGit remote protocol v1 object transfer."""

    def __init__(self, remote_url: str, token: Optional[str] = None):
        self.remote_url = remote_url.rstrip("/")
        self.headers = {
            "User-Agent": "MyGit-Client/1.0",
            "X-MyGit-Protocol-Version": "1",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def discover_refs(self) -> Dict[str, str]:
        """Fetch advertised remote references."""
        url = f"{self.remote_url}/info/refs"
        with httpx.Client(headers=self.headers, timeout=10.0) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to discover remote refs: HTTP {resp.status_code} {resp.text}")
            return resp.json().get("refs", {})

    def push_objects(self, repo: Repository, missing_shas: List[str], target_branch: str, target_sha: str) -> bool:
        """Upload missing objects and update remote ref atomically."""
        object_store = ObjectStore(repo.objects_dir)

        # 1. Package missing objects
        payload_objects = []
        for sha in missing_shas:
            type_name, data = object_store.read_object(sha)
            payload_objects.append({
                "sha": sha,
                "type": type_name,
                "data_hex": data.hex()
            })

        # 2. Transmit pack payload
        url = f"{self.remote_url}/objects/push"
        request_body = {
            "ref": f"refs/heads/{target_branch}",
            "target_sha": target_sha,
            "objects": payload_objects
        }

        with httpx.Client(headers=self.headers, timeout=30.0) as client:
            resp = client.post(url, json=request_body)
            if resp.status_code == 200 and resp.json().get("success"):
                return True
            raise RuntimeError(f"Push rejected by server: HTTP {resp.status_code} {resp.text}")

    def fetch_objects(self, want_sha: str) -> List[Dict[str, str]]:
        """Download objects required for want_sha."""
        url = f"{self.remote_url}/objects/fetch"
        with httpx.Client(headers=self.headers, timeout=30.0) as client:
            resp = client.post(url, json={"want_sha": want_sha})
            if resp.status_code != 200:
                raise RuntimeError(f"Fetch failed: HTTP {resp.status_code}")
            return resp.json().get("objects", [])
