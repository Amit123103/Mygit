import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="MyGit Server",
    description="Remote Server Backend & Web Protocol Endpoint for MyGit Version Control Ecosystem",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-Memory Mock Storage for Remote Server metadata ---
USERS_DB = {}
REPOS_DB = {}
PRS_DB = {}
ISSUES_DB = {}


# --- Pydantic Data Models ---
class UserRegister(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class RepoCreate(BaseModel):
    name: str
    description: str = ""
    is_private: bool = False


class PRCreate(BaseModel):
    title: str
    description: str
    head_branch: str
    base_branch: str


class IssueCreate(BaseModel):
    title: str
    body: str


# --- Health Endpoints ---
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "mygit-server", "timestamp": int(time.time())}


@app.get("/ready")
def readiness_check():
    return {"ready": True}


# --- Auth Endpoints ---
@app.post("/api/v1/auth/register")
def register(user: UserRegister):
    if user.username in USERS_DB:
        raise HTTPException(status_code=400, detail="Username already exists")
    USERS_DB[user.username] = {
        "username": user.username,
        "email": user.email,
        "password": user.password,
    }
    return {"message": "User registered successfully", "username": user.username}


@app.post("/api/v1/auth/login")
def login(credentials: UserLogin):
    user = USERS_DB.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": f"token-{credentials.username}", "token_type": "bearer"}


# --- Repositories Endpoints ---
@app.get("/api/v1/repos")
def list_repositories():
    return list(REPOS_DB.values())


@app.post("/api/v1/repos")
def create_repository(repo: RepoCreate):
    repo_key = f"default/{repo.name}"
    if repo_key in REPOS_DB:
        raise HTTPException(status_code=400, detail="Repository already exists")

    repo_data = {
        "id": len(REPOS_DB) + 1,
        "owner": "default",
        "name": repo.name,
        "description": repo.description,
        "is_private": repo.is_private,
        "stars": 0,
        "forks": 0,
        "default_branch": "main",
        "created_at": int(time.time()),
    }
    REPOS_DB[repo_key] = repo_data
    return repo_data


@app.get("/api/v1/repos/{owner}/{repo_name}")
def get_repository(owner: str, repo_name: str):
    repo_key = f"{owner}/{repo_name}"
    if repo_key not in REPOS_DB:
        # Default mock repo if not registered
        return {
            "id": 1,
            "owner": owner,
            "name": repo_name,
            "description": "MyGit Version Control Repository",
            "is_private": False,
            "stars": 12,
            "forks": 2,
            "default_branch": "main",
        }
    return REPOS_DB[repo_key]


# --- Remote Wire Protocol Endpoints ---
@app.get("/api/v1/repos/{owner}/{repo_name}/info/refs")
def info_refs(owner: str, repo_name: str):
    return {
        "protocol": "v1",
        "refs": {
            "refs/heads/main": "0000000000000000000000000000000000000000000000000000000000000000",
        },
    }


@app.post("/api/v1/repos/{owner}/{repo_name}/objects/push")
def push_objects(owner: str, repo_name: str, payload: dict):
    return {"success": True, "message": "Objects pushed successfully"}


@app.post("/api/v1/repos/{owner}/{repo_name}/objects/fetch")
def fetch_objects(owner: str, repo_name: str, payload: dict):
    return {"objects": []}


# --- Pull Requests Endpoints ---
@app.get("/api/v1/repos/{owner}/{repo_name}/pulls")
def list_pull_requests(owner: str, repo_name: str):
    return [
        {
            "id": 1,
            "title": "Add authentication module",
            "author": "developer",
            "state": "open",
            "head": "feature/auth",
            "base": "main",
            "created_at": int(time.time()) - 3600,
        }
    ]


@app.post("/api/v1/repos/{owner}/{repo_name}/pulls")
def create_pull_request(owner: str, repo_name: str, pr: PRCreate):
    pr_id = len(PRS_DB) + 1
    data = {
        "id": pr_id,
        "title": pr.title,
        "description": pr.description,
        "author": "developer",
        "state": "open",
        "head": pr.head_branch,
        "base": pr.base_branch,
        "created_at": int(time.time()),
    }
    PRS_DB[pr_id] = data
    return data


# --- Issues Endpoints ---
@app.get("/api/v1/repos/{owner}/{repo_name}/issues")
def list_issues(owner: str, repo_name: str):
    return [
        {
            "id": 101,
            "title": "Fix merge conflict edge case in 3-way engine",
            "author": "developer",
            "status": "open",
            "created_at": int(time.time()) - 7200,
        }
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
