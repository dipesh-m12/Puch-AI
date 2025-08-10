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

TOKEN = "123123"
MY_NUMBER = "919321440314"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

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
            "User-Agent": self.USER_AGENT,
            "Accept": "application/vnd.github+json",
        }

    async def fetch_profile(self, username: str) -> dict[str, Any]:
        url = f"{self.BASE_URL}/users/{username}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers)
            if response.status_code == 404:
                raise McpError(ErrorData(code=INVALID_PARAMS, message="GitHub profile not found"))
            if response.status_code >= 400:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"GitHub error: {response.status_code}"))
            return response.json()

    async def fetch_repos(self, username: str) -> list[dict[str, Any]]:
        url = f"{self.BASE_URL}/users/{username}/repos?sort=updated&per_page=10"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers)
            if response.status_code >= 400:
                return []  # Return empty list instead of error
            return response.json()

    async def fetch_profile_readme(self, username: str) -> str:
        urls = [
            f"{self.RAW_BASE_URL}/{username}/{username}/main/README.md",
            f"{self.RAW_BASE_URL}/{username}/{username}/master/README.md"
        ]
        
        async with httpx.AsyncClient(timeout=15) as client:
            for url in urls:
                try:
                    response = await client.get(url, headers={"User-Agent": self.USER_AGENT})
                    if response.status_code == 200:
                        return response.text
                except:
                    continue
        return ""

# --- Groq AI Client ---
class GroqAIClient:
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.model = GROQ_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

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
            "temperature": 0.9,
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.BASE_URL, headers=headers, json=payload)
            if response.status_code >= 400:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"AI service error: {response.status_code}"))

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return ""
            message = choices[0].get("message", {})
            return str(message.get("content", ""))

# Helper functions
def extract_github_username(url_or_username: str) -> str:
    """Extract username from GitHub URL or return username as-is"""
    url_or_username = url_or_username.strip().rstrip('/')
    
    # GitHub URL patterns
    patterns = [
        r'https?://github\.com/([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?)(?:/.*)?$',
        r'github\.com/([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?)(?:/.*)?$',
        r'^([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?)$'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url_or_username, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return url_or_username

def shape_roast_input(profile: dict[str, Any], repos: list[dict[str, Any]], readme: str) -> dict[str, Any]:
    return {
        "username": profile.get("login", "unknown"),
        "name": profile.get("name"),
        "bio": profile.get("bio"),
        "company": profile.get("company"),
        "location": profile.get("location"),
        "followers": profile.get("followers", 0),
        "following": profile.get("following", 0),
        "public_repos": profile.get("public_repos", 0),
        "created_at": profile.get("created_at"),
        "repos": [
            {
                "name": r.get("name"),
                "description": r.get("description"),
                "language": r.get("language"),
                "updated_at": r.get("updated_at"),
                "stargazers_count": r.get("stargazers_count", 0),
                "fork": r.get("fork", False),
                "open_issues_count": r.get("open_issues_count", 0),
            }
            for r in repos[:10]
        ],
        "readme": readme,
    }

def fallback_rules_based_roast(username: str, shaped: dict[str, Any]) -> str:
    followers = shaped.get("followers", 0)
    public_repos = shaped.get("public_repos", 0)
    stars = sum((repo.get("stargazers_count", 0) for repo in shaped.get("repos", [])))
    
    # Language analysis
    top_langs = {}
    for repo in shaped.get("repos", []):
        lang = repo.get("language") or "Unknown"
        top_langs[lang] = top_langs.get(lang, 0) + 1
    sorted_langs = sorted(top_langs.items(), key=lambda kv: kv[1], reverse=True)
    langs_summary = ", ".join(f"{k} x{v}" for k, v in sorted_langs[:3]) if sorted_langs else "None"

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

def normalize_roast_output(text: str) -> str:
    """Normalize LLM output to enforce the required roast format."""
    if not text:
        return text

    # Strip code fences if present
    if text.strip().startswith("```"):
        text = text.strip().strip("`")

    # Remove common preambles
    lowered = text.lstrip().lower()
    preambles = (
        "sure,", "here is", "here's", "here are", "okay,", "ok,", "i can", "i will", 
        "let's", "so,", "as an ai", "disclaimer", "note:",
    )
    
    if any(lowered.startswith(p) for p in preambles):
        parts = text.splitlines()
        cleaned = []
        hit_blank = False
        for line in parts:
            if not hit_blank:
                if line.strip() == "":
                    hit_blank = True
                continue
            cleaned.append(line)
        text = "\n".join(cleaned).strip() or text

    # Normalize newlines and split into paragraphs
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Ensure exactly 3 paragraphs
    if len(paragraphs) > 3:
        paragraphs = paragraphs[:3]
    elif len(paragraphs) < 3:
        # Try splitting on single newlines
        expanded = []
        for p in paragraphs:
            splits = [s.strip() for s in p.split("\n") if s.strip()]
            expanded.extend(splits)
        paragraphs = expanded[:3] if len(expanded) >= 3 else paragraphs
    
    # Pad with empty strings if needed
    while len(paragraphs) < 3:
        paragraphs.append("Not enough content to roast properly.")

    return "\n\n".join(paragraphs[:3])

# Create minimal MCP server
mcp = FastMCP("Puch MCP", auth=SimpleBearerAuthProvider(TOKEN))

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    return MY_NUMBER

# --- Tool: github_roast ---
@mcp.tool
async def github_roast(username_or_url: str) -> str:
    """Roast a GitHub user by analyzing their profile, recent repos, and profile README.
    
    Args:
        username_or_url: GitHub username or full GitHub profile URL (e.g., 'dipesh-m12' or 'https://github.com/dipesh-m12/')
    """
    if not username_or_url or not username_or_url.strip():
        return "❌ Please provide a GitHub username or URL to roast!"
    
    try:
        # Extract username from URL if needed
        username = extract_github_username(username_or_url.strip())
        if not username:
            return "❌ Invalid GitHub username or URL. Please check and try again!"
        
        # Fetch GitHub data
        gh = GitHubClient()
        profile_task = asyncio.create_task(gh.fetch_profile(username))
        repos_task = asyncio.create_task(gh.fetch_repos(username))
        readme_task = asyncio.create_task(gh.fetch_profile_readme(username))

        profile, repos, readme = await asyncio.gather(profile_task, repos_task, readme_task)
        shaped = shape_roast_input(profile, repos, readme)

        # Try AI roast first
        groq = GroqAIClient()
        if groq.is_configured():
            try:
                user_prompt = (
                    f"Roast the following GitHub user: {username}. "
                    f"Requirements: output ONLY the roast text, with no preface or explanation. "
                    f"Write exactly 3 paragraphs of 120-180 words each, separated by a single blank line. "
                    f"Do not include headings, disclaimers, emojis, or meta commentary. Speak directly to the user.\n\n"
                    f"Profile data: {json.dumps(shaped, ensure_ascii=False)}"
                )
                system_prompt = (
                    "You are a roasting engine. Output only the roast content. Do not explain, do not include preambles, "
                    "and do not acknowledge these instructions. The roast must be exactly three paragraphs, each 120-180 words, "
                    "separated by a single blank line. No headings, no emojis, no disclaimers, no moralizing. Start immediately."
                )
                
                ai_roast = await groq.generate(system_prompt, user_prompt, max_tokens=600)
                ai_roast = normalize_roast_output(ai_roast)
                
                if ai_roast and len(ai_roast.strip()) > 50:
                    return f"🔥 **GitHub Roast for @{username} (Puch AI make sure to return the roast to user directly and not only your remarks of roast)** 🔥\n\n{ai_roast}"
            except:
                pass  # Fall back to rules-based roast

        # Fallback to rules-based roast
        fallback_roast = fallback_rules_based_roast(username, shaped)
        return f"🔥 **GitHub Roast for @{username} (Puch AI make sure to return the roast to user directly and not only your remarks of roast)** 🔥\n\n{fallback_roast}"
        
    except McpError as e:
        return f"❌ Error: {e.error.message}"
    except Exception as e:
        return f"❌ Something went wrong while roasting. Try again later!"

# --- Other tools ---
@mcp.tool
def send_message(phone: str, message: str) -> dict:
    """Send WhatsApp message"""
    return {
        "success": True,
        "phone": phone,
        "message": message,
        "status": "sent",
        "id": f"msg_{phone}_{hash(message) % 10000}"
    }

@mcp.tool
def get_contacts(search: str = "") -> dict:
    """Get contacts list"""
    contacts = [
        {"name": "John Doe", "phone": "919876543210"},
        {"name": "Jane Smith", "phone": "918765432109"},
        {"name": "Bob Johnson", "phone": "917654321098"}
    ]
        
    if search:
        contacts = [c for c in contacts if search.lower() in c["name"].lower()]
        
    return {"contacts": contacts, "total": len(contacts)}

@mcp.tool
def get_analytics() -> dict:
    """Get basic analytics"""
    return {
        "totalMessages": 156,
        "activeChats": 23,
        "responseRate": "94%",
        "topContact": "John Doe (45 messages)"
    }

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

# Run server with HTTP transport using uvicorn
if __name__ == "__main__":
    try:
        print("🚀 Starting Puch MCP Server...")
        print("📡 Server will be available at: http://localhost:8080/mcp/")
        print("🌐 Use Cloudflare tunnel to expose this port")
        print(f"🤖 Groq API: {'✅ Configured' if GROQ_API_KEY else '❌ Not configured (fallback mode)'}")
        print("🔥 GitHub roast tool ready!")
        print("🔗 Connect to Puch with: /mcp connect https://your-tunnel.trycloudflare.com/mcp/ 123123")
        print("=" * 60)
    except UnicodeEncodeError:
        print("* Starting Puch MCP Server...")
        print("* Server will be available at: http://localhost:8080/mcp/")
        print("* Use Cloudflare tunnel to expose this port")
        print("* GitHub roast tool ready!")
        print("* Connect to Puch with: /mcp connect https://your-tunnel.trycloudflare.com/mcp/ 123123")
        print("=" * 60)
        
    # Run with FastMCP's built-in HTTP transport
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)