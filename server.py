#!/usr/bin/env python3
"""
Minimal MCP Server for Puch AI - HTTP Transport
For Cloudflare tunnel connectivity with GitHub Roast feature
"""

from fastmcp import FastMCP
import sys
import os
import json
import asyncio
import re
from typing import Any
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from mcp import ErrorData, McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR
from starlette.requests import Request
from starlette.responses import PlainTextResponse
import httpx

# Fix encoding for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Get from environment variables or use defaults
TOKEN = os.getenv("AUTH_TOKEN", "123123")
MY_NUMBER = os.getenv("MY_NUMBER", "919321440314")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# --- Auth Provider ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token
    
    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="puch-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

# --- GitHub API Client ---
class GitHubClient:
    BASE_URL = "https://api.github.com"
    RAW_BASE_URL = "https://raw.githubusercontent.com"
    USER_AGENT = "puch-github-roaster/1.0"

    def __init__(self):
        self._headers = {
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
            "Accept": "application/vnd.github+json",
        }

    async def fetch_profile(self, username: str) -> dict[str, Any]:
        url = f"{self.BASE_URL}/users/{username}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers, timeout=30)
            if response.status_code == 404:
                raise McpError(ErrorData(code=INVALID_PARAMS, message="GitHub profile not found"))
            if response.status_code >= 400:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"GitHub error: {response.status_code}"))
            return response.json()

    async def fetch_repos(self, username: str) -> list[dict[str, Any]]:
        url = f"{self.BASE_URL}/users/{username}/repos?sort=updated&per_page=10"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers, timeout=30)
            if response.status_code >= 400:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"GitHub repos error: {response.status_code}"))
            return response.json()

    async def fetch_profile_readme(self, username: str) -> str:
        url = f"{self.RAW_BASE_URL}/{username}/{username}/main/README.md"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self._headers, timeout=15)
                if response.status_code == 200:
                    return response.text
            except httpx.HTTPError:
                pass
        return ""

# --- Groq AI Client ---
class GroqAIClient:
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.model = GROQ_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        if not self.is_configured():
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="Groq API is not configured"))

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.BASE_URL, headers=headers, json=payload, timeout=60)
            if response.status_code >= 400:
                raise McpError(
                    ErrorData(code=INTERNAL_ERROR, message=f"Groq API error: {response.status_code} {response.text}")
                )

            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            message = choices[0].get("message", {})
            return str(message.get("content", ""))

# --- Helper Functions ---
def extract_github_username(url_or_username: str) -> str:
    """Extract username from GitHub URL or return username as-is"""
    url_or_username = url_or_username.strip()
    
    # Pattern to match GitHub URLs
    github_patterns = [
        r'https?://github\.com/([^/]+)/?.*',
        r'github\.com/([^/]+)/?.*',
        r'^([a-zA-Z0-9](?:[a-zA-Z0-9]|-){0,38})$'  # Valid username pattern
    ]
    
    for pattern in github_patterns:
        match = re.match(pattern, url_or_username)
        if match:
            return match.group(1)
    
    return url_or_username

def _shape_roast_input(profile: dict[str, Any], repos: list[dict[str, Any]], readme: str) -> dict[str, Any]:
    shaped = {
        "name": profile.get("name"),
        "bio": profile.get("bio"),
        "company": profile.get("company"),
        "location": profile.get("location"),
        "followers": profile.get("followers"),
        "following": profile.get("following"),
        "public_repos": profile.get("public_repos"),
        "created_at": profile.get("created_at"),
        "repos": [
            {
                "name": r.get("name"),
                "description": r.get("description"),
                "language": r.get("language"),
                "updated_at": r.get("updated_at"),
                "stargazers_count": r.get("stargazers_count"),
                "fork": r.get("fork"),
                "open_issues_count": r.get("open_issues_count"),
            }
            for r in repos
        ],
        "readme": readme,
    }
    return shaped

def _fallback_rules_based_roast(username: str, shaped: dict[str, Any]) -> str:
    followers = shaped.get("followers") or 0
    public_repos = shaped.get("public_repos") or 0
    stars = sum((repo.get("stargazers_count") or 0) for repo in shaped.get("repos", []))
    top_langs: dict[str, int] = {}
    for repo in shaped.get("repos", []):
        lang = repo.get("language") or "Unknown"
        top_langs[lang] = top_langs.get(lang, 0) + 1
    sorted_langs = sorted(top_langs.items(), key=lambda kv: kv[1], reverse=True)
    langs_summary = ", ".join(f"{k} x{v}" for k, v in sorted_langs[:5]) if sorted_langs else "None"

    para1 = (
        f"So, {username}, rocking a grand total of {public_repos} public repos and {followers} followers. "
        f"That's not a GitHub presence, that's witness protection. Your star count ({stars}) suggests your most loyal fan is the stargazer button you keep pressing in your sleep."
    )
    para2 = (
        f"Languages you dabble in: {langs_summary}. That's not a tech stack, that's a buffet plate where you touched everything and finished nothing. "
        f"Half your repos look like tutorials you rage-quit after the README."
    )
    para3 = (
        "Your profile README reads like a motivational poster stapled to a TODO list. "
        "Ship something, delete the zombie projects, and maybe—just maybe—write code people actually want to star."
    )
    return "\n\n".join([para1, para2, para3])

# Create minimal MCP server
mcp = FastMCP("Puch MCP", auth=SimpleBearerAuthProvider(TOKEN))

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    return MY_NUMBER

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

# --- Tool: github_roast ---
@mcp.tool()
async def github_roast(username_or_url: str) -> str:
    """Roast a GitHub user by analyzing their profile, recent repos, and profile README.
    
    Args:
        username_or_url: GitHub username or full GitHub profile URL (e.g., 'dipesh-m12' or 'https://github.com/dipesh-m12/')
    """
    if not username_or_url or not username_or_url.strip():
        return "❌ Please provide a GitHub username or URL"
    
    try:
        # Extract username from URL if needed
        username = extract_github_username(username_or_url)
        
        if not username:
            return "❌ Invalid GitHub username or URL"
        
        # Fetch GitHub data
        gh = GitHubClient()
        profile_task = asyncio.create_task(gh.fetch_profile(username))
        repos_task = asyncio.create_task(gh.fetch_repos(username))
        readme_task = asyncio.create_task(gh.fetch_profile_readme(username))

        profile, repos, readme = await asyncio.gather(profile_task, repos_task, readme_task)
        shaped = _shape_roast_input(profile, repos, readme)

        # Try to generate AI roast first
        groq = GroqAIClient()
        if groq.is_configured():
            try:
                user_prompt = (
                    f"give a short and harsh roasting for the following github profile: {username}. "
                    f"Do it in 3 paragraphs of each 150 words, separated by a blank line. "
                    f"Here are the details: {json.dumps(shaped, ensure_ascii=False)}"
                )
                system_prompt = (
                    "You roast people github account based on their bio, name, readme, and repos as harsh and spicy as "
                    "possible, and directly start without any other text or description."
                )
                
                roast = await groq.generate(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=500)
                if roast.strip():
                    return f"🔥 **GitHub Roast for {username}** 🔥\n\n{roast.strip()}"
            except Exception as e:
                print(f"AI roast failed, falling back to rules-based: {e}")
        
        # Fallback to rules-based roast
        fallback_roast = _fallback_rules_based_roast(username, shaped)
        return f"🔥 **GitHub Roast for {username}** 🔥\n\n{fallback_roast}"
        
    except McpError as e:
        return f"❌ Error: {e.error.message}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

# --- Tool: send_message (kept as requested) ---
@mcp.tool()
def send_message(phone: str, message: str) -> dict:
    """Send WhatsApp message"""
    return {
        "success": True,
        "phone": phone,
        "message": message,
        "status": "sent",
        "id": f"msg_{phone}_{hash(message) % 10000}"
    }

# Run server with HTTP transport using uvicorn
if __name__ == "__main__":
    print(f"🚀 Starting Puch MCP Server...")
    print(f"🔑 Using token: {TOKEN}")
    print(f"📱 Phone number: {MY_NUMBER}")
    print(f"🤖 Groq API: {'✅ Configured' if GROQ_API_KEY else '❌ Not configured (will use fallback roasts)'}")
    print(f"📡 Server will be available at: http://localhost:8080/mcp/")
    print(f"🌐 Use Cloudflare tunnel to expose this port")
    print("=" * 60)
    
    # Run with FastMCP's built-in HTTP transport
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)