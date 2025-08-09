#!/usr/bin/env python3
"""
Minimal MCP Server for Puch AI - HTTP Transport
For Cloudflare tunnel connectivity
"""

from fastmcp import FastMCP
import sys
import os
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken

# Fix encoding for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

TOKEN="123123"
MY_NUMBER="919321440314"

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

# Create minimal MCP server
mcp = FastMCP("Puch MCP",  auth=SimpleBearerAuthProvider(TOKEN),)

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    return MY_NUMBER

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

@mcp.tool()
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

@mcp.tool()
def get_analytics() -> dict:
    """Get basic analytics"""
    return {
        "totalMessages": 156,
        "activeChats": 23,
        "responseRate": "94%",
        "topContact": "John Doe (45 messages)"
    }

# Run server with HTTP transport using uvicorn
if __name__ == "__main__":
    try:
        print("🚀 Starting Puch MCP Server...")
        print("📡 Server will be available at: http://localhost:8080/mcp/")
        print("🌐 Use Cloudflare tunnel to expose this port")
        print("🔗 Connect to Puch with: /mcp connect https://your-tunnel.trycloudflare.com/mcp/ your_token")
        print("=" * 60)
    except UnicodeEncodeError:
        # Fallback for terminals that don't support Unicode
        print("* Starting Puch MCP Server...")
        print("* Server will be available at: http://localhost:8080/mcp/")
        print("* Use Cloudflare tunnel to expose this port")
        print("* Connect to Puch with: /mcp connect https://your-tunnel.trycloudflare.com/mcp/ your_token")
        print("=" * 60)
    
    # Run with FastMCP's built-in HTTP transport
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)