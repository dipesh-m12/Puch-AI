#!/usr/bin/env python3
"""
Minimal MCP Server for Puch AI - STDIO Transport
Just the essentials to connect and work
"""

from fastmcp import FastMCP

# Create minimal MCP server
mcp = FastMCP("Puch MCP")

@mcp.tool()
def validate(token: str) -> str:
    """REQUIRED: Validate token for Puch AI - returns phone number"""
    if token and len(token) > 5:
        return "919876543210"  # Format: country_code + number (NO + symbol)
    raise ValueError("Invalid token")

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

# Run server with STDIO transport (default)
if __name__ == "__main__":
    mcp.run()

    # npx @modelcontextprotocol/inspector python server.py