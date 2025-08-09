#!/usr/bin/env python3
"""
Simple MCP HTTP Client Test - Connect to running HTTP server
"""

import asyncio
from fastmcp import Client

async def test_http_server():
    print("🧪 Simple MCP HTTP Test")
    print("=" * 30)
    
    # Connect to your running HTTP server
    client = Client("https://puch-ai-e110.onrender.com/mcp/", auth="123123")
    # client = Client("http://localhost:8080/mcp/")
    
    try:
        async with client:
            print("✅ Connected to MCP HTTP server")
            
            # Test server connectivity
            await client.ping()
            print("✅ Server is reachable")
            
            # List all available tools
            print("\n📋 Available tools:")
            tools = await client.list_tools()
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Test each tool
            print("\n🔧 Testing tools:")
            
            # 1. Test validate
            print("\n1. Testing validate...")
            result = await client.call_tool("validate")
            print(f"   Result: {result[0].text if result and len(result) > 0 else 'No content'}")
            
            # 2. Test send_message
            print("\n2. Testing send_message...")
            result = await client.call_tool("send_message", {
                "phone": "919876543210", 
                "message": "Hello from test!"
            })
            print(f"   Result: {result[0].text if result and len(result) > 0 else 'No content'}")
            
            # 3. Test get_contacts (no search)
            print("\n3. Testing get_contacts...")
            result = await client.call_tool("get_contacts")
            print(f"   Result: {result[0].text if result and len(result) > 0 else 'No content'}")
            
            # 4. Test get_contacts (with search)
            print("\n4. Testing get_contacts with search...")
            result = await client.call_tool("get_contacts", {"search": "John"})
            print(f"   Result: {result[0].text if result and len(result) > 0 else 'No content'}")
            
            # 5. Test get_analytics
            print("\n5. Testing get_analytics...")
            result = await client.call_tool("get_analytics")
            print(f"   Result: {result[0].text if result and len(result) > 0 else 'No content'}")
            
            print("\n✅ All tests completed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_http_server())