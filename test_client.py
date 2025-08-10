#!/usr/bin/env python3
"""
Simple MCP HTTP Client Test - Connect to running HTTP server
"""

import asyncio
import json
from fastmcp import Client

def format_result(result):
    """Format the result from tool call properly"""
    if hasattr(result, 'content') and result.content:
        # Handle content array
        texts = []
        for content_item in result.content:
            if hasattr(content_item, 'text'):
                texts.append(content_item.text)
            elif isinstance(content_item, dict) and 'text' in content_item:
                texts.append(content_item['text'])
            else:
                texts.append(str(content_item))
        return '\n'.join(texts)
    elif hasattr(result, 'text'):
        return result.text
    elif isinstance(result, dict):
        return json.dumps(result, indent=2)
    else:
        return str(result)

async def test_http_server():
    print("🧪 FastMCP HTTP Client Test")
    print("=" * 50)
    
    # Test both local and deployed versions
    servers = [
        ("Local Server", "http://localhost:8080/mcp/", "123123"),
        # ("Deployed Server", "https://puch-ai-e110.onrender.com/mcp/", "123123"),
    ]
    
    for server_name, url, token in servers:
        print(f"\n🔗 Testing {server_name}: {url}")
        print("-" * 40)
        
        try:
            # Create client with auth
            client = Client(url, auth=token)
            
            async with client:
                print("✅ Connected to MCP HTTP server")
                
                # Test server connectivity
                try:
                    await client.ping()
                    print("✅ Server ping successful")
                except Exception as ping_error:
                    print(f"⚠️  Ping failed: {ping_error}")
                
                # List all available tools
                print("\n📋 Available tools:")
                try:
                    tools = await client.list_tools()
                    if tools:
                        for tool in tools:
                            desc = getattr(tool, 'description', 'No description')
                            print(f"  - {tool.name}: {desc}")
                    else:
                        print("  No tools found")
                except Exception as e:
                    print(f"  ❌ Error listing tools: {e}")
                
                # Test each tool
                print("\n🔧 Testing tools:")
                print("=" * 30)
                
                # 1. Test validate
                print("\n1️⃣ Testing validate...")
                try:
                    result = await client.call_tool("validate")
                    formatted_result = format_result(result)
                    print(f"   ✅ Result: {formatted_result}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                
                # 2. Test send_message
                print("\n2️⃣ Testing send_message...")
                try:
                    result = await client.call_tool("send_message", {
                        "phone": "919876543210",
                        "message": "Hello from FastMCP test client!"
                    })
                    formatted_result = format_result(result)
                    print(f"   ✅ Result: {formatted_result}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                
                # 3. Test get_contacts
                print("\n3️⃣ Testing get_contacts...")
                try:
                    result = await client.call_tool("get_contacts", {"search": "John"})
                    formatted_result = format_result(result)
                    print(f"   ✅ Result: {formatted_result}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                
                # 4. Test get_analytics
                print("\n4️⃣ Testing get_analytics...")
                try:
                    result = await client.call_tool("get_analytics")
                    formatted_result = format_result(result)
                    print(f"   ✅ Result: {formatted_result}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                
                # 5. Test github_roast with different formats
                print("\n5️⃣ Testing github_roast...")
                
                test_cases = [
                    ("Username only", "dipesh-m12"),
                    ("Full GitHub URL", "https://github.com/dipesh-m12"),
                    ("GitHub URL with trailing slash", "https://github.com/dipesh-m12/"),
                ]
                
                for case_name, username in test_cases:
                    print(f"\n   🔥 {case_name}: {username}")
                    try:
                        result = await client.call_tool("github_roast", {
                            "username_or_url": username
                        })
                        formatted_result = format_result(result)
                        # Truncate long results for readability
                        if len(formatted_result) > 300:
                            print(f"   ✅ Result: {formatted_result}...")
                        else:
                            print(f"   ✅ Result: {formatted_result}")
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
                
                print(f"\n✅ {server_name} tests completed!")
                
        except Exception as e:
            print(f"❌ Failed to connect to {server_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎉 All server tests completed!")

async def test_single_tool():
    """Interactive single tool test"""
    print("🎯 Single Tool Test Mode")
    print("Available tools:")
    print("1. validate")
    print("2. send_message") 
    print("3. get_contacts")
    print("4. get_analytics")
    print("5. github_roast")
    
    choice = input("\nEnter tool number (1-5): ").strip()
    server_url = input("Enter server URL (default: http://localhost:8080/mcp/): ").strip()
    if not server_url:
        server_url = "http://localhost:8080/mcp/"
    
    token = input("Enter auth token (default: 123123): ").strip()
    if not token:
        token = "123123"
    
    client = Client(server_url, auth=token)
    
    try:
        async with client:
            print(f"✅ Connected to {server_url}")
            
            if choice == "1":
                result = await client.call_tool("validate")
                print(f"Result: {format_result(result)}")
            
            elif choice == "2":
                phone = input("Enter phone number: ").strip()
                message = input("Enter message: ").strip()
                result = await client.call_tool("send_message", {
                    "phone": phone, 
                    "message": message
                })
                print(f"Result: {format_result(result)}")
            
            elif choice == "3":
                search = input("Enter search term (optional): ").strip()
                args = {"search": search} if search else {}
                result = await client.call_tool("get_contacts", args)
                print(f"Result: {format_result(result)}")
            
            elif choice == "4":
                result = await client.call_tool("get_analytics")
                print(f"Result: {format_result(result)}")
            
            elif choice == "5":
                username = input("Enter GitHub username or URL: ").strip()
                result = await client.call_tool("github_roast", {
                    "username_or_url": username
                })
                print(f"Result: {format_result(result)}")
            
            else:
                print("❌ Invalid choice")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function with mode selection"""
    print("FastMCP Client Test Utility")
    print("1. Test all tools on all servers")
    print("2. Test single tool interactively")
    
    choice = input("Choose mode (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_http_server())
    elif choice == "2":
        asyncio.run(test_single_tool())
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    # Uncomment the line below to use interactive mode selection
    # main()
    
    # Or run full test directly
    asyncio.run(test_http_server())