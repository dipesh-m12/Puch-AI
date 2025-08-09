# Import necessary libraries from FastAPI
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uvicorn
import json
import os

# --- Pydantic Models for Request and Response ---
# These models define the structure of the data we'll be sending and receiving.

# The ToolCall model represents a single tool call from the client (Puch AI).
class ToolCall(BaseModel):
    tool_name: str
    tool_input: dict

# The MCPRequest model represents the entire request body sent from the client.
class MCPRequest(BaseModel):
    tool_calls: list[ToolCall]

# The ToolOutput model represents the response from a single tool call.
class ToolOutput(BaseModel):
    tool_name: str
    tool_output: dict

# The MCPResponse model represents the server's final response to the client.
class MCPResponse(BaseModel):
    tool_outputs: list[ToolOutput]

# --- FastAPI App Setup ---
app = FastAPI(title="Basic MCP Server")

# Define a simple home endpoint for a health check.
@app.get("/")
def read_root():
    return {"message": "MCP Server is running!"}

# --- Core MCP Logic ---
@app.post("/mcp", response_model=MCPResponse)
async def mcp_endpoint(request: Request):
    """
    Handles incoming MCP tool calls from Puch AI.
    It processes each tool call and returns the appropriate output.

    NOTE: The request body is now processed manually to handle cases where
    no JSON body is present, such as with the initial /mcp connect command.
    """
    tool_outputs = []
    
    # Get the bearer token from the request headers
    # This token is used to authenticate the user and is required by the `validate` tool.
    bearer_token = request.headers.get("Authorization")
    if bearer_token:
        # The bearer token is expected in the format "Bearer <token>"
        bearer_token = bearer_token.split(" ")[1] if " " in bearer_token else None
        
    # We now handle the request body more defensively to avoid crashes.
    request_body = {}
    try:
        # Try to read the raw request body as JSON.
        raw_body = await request.json()
        # If it's a dictionary, we can use it.
        # This check prevents an AttributeError when the body is empty.
        if isinstance(raw_body, dict):
            request_body = raw_body
    except json.JSONDecodeError:
        # If the body is not valid JSON, we'll proceed with an empty dictionary.
        pass
        
    # We expect a list of tool calls under the key "tool_calls"
    tool_calls = request_body.get("tool_calls", [])

    # Loop through each tool call in the request
    for tool_call in tool_calls:
        try:
            tool_name = tool_call.get("tool_name")
            tool_input = tool_call.get("tool_input", {})
            
            # Check which tool is being requested and call the corresponding function
            if tool_name == "validate":
                # The 'validate' tool is mandatory for authentication.
                output = await validate_tool(bearer_token)
            elif tool_name == "get_time":
                # This is a custom tool example.
                output = await get_time_tool()
            else:
                # Handle cases where the requested tool is not found
                output = {"error": f"Unknown tool: {tool_name}"}

            # Add the output to our list of tool responses
            tool_outputs.append(ToolOutput(tool_name=tool_name, tool_output=output))
        except Exception as e:
            # Catch any errors during tool execution and provide an error output
            tool_outputs.append(ToolOutput(tool_name=tool_name, tool_output={"error": str(e)}))

    # Return the complete list of tool outputs in the required format
    return MCPResponse(tool_outputs=tool_outputs)

# --- Tool Implementations ---
async def validate_tool(bearer_token: str):
    """
    Validates the bearer token and returns the user's phone number.
    This is a critical, required tool for the MCP server.
    """
    # For this basic demo, we'll hardcode a token and a phone number.
    # In a real-world application, you would use this token to look up the
    # user's information from your database.
    VALID_TOKEN = "abc123token"
    VALID_PHONE_NUMBER = "919876543210" # Example for an Indian number

    if bearer_token == VALID_TOKEN:
        # If the token is valid, return the user's phone number
        return {"user_id": VALID_PHONE_NUMBER}
    else:
        # If the token is invalid, raise an exception to indicate failure.
        raise HTTPException(status_code=401, detail="Invalid bearer token")

async def get_time_tool():
    """
    A simple custom tool that returns the current time.
    """
    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"current_time": current_time}

# --- Server Startup Command ---
# This block allows you to run the server directly from the Python file.
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
