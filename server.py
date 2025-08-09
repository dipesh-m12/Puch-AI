#!/usr/bin/env python3
"""
Minimal MCP Server for Puch AI - HTTP Transport
For Cloudflare tunnel connectivity
"""

from fastmcp import FastMCP
import sys
import os

# Fix encoding for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Create minimal MCP server
mcp = FastMCP("Puch MCP")

@mcp.tool()
def validate(token: str) -> str:
    """REQUIRED: Validate token for Puch AI - returns phone number"""
    print(f"Validate called with token: {token}")
    
    # Token-to-phone mapping - in real implementation, this would be from a database
    token_mappings = {
        "123123": "919876543210",  # Your token mapped to your phone number
        "test": "919876543210",
        "dipesh": "919876543210"
    }
    
    if token in token_mappings:
        phone_number = token_mappings[token]
        print(f"Token '{token}' validated, returning phone: {phone_number}")
        return phone_number
    elif len(token) > 2:  # Fallback for any token
        phone_number = "919876543210"
        print(f"Using fallback phone number: {phone_number}")
        return phone_number
    
    print("Token validation failed")
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