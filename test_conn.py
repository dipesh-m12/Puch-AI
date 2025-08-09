# ngrok config add-authtoken 311HulgHcBcWInkm2jUPJUegpee_3ervPbZTGQhynGcKFs6Af
# npx ngrok http 8000
import requests
import json

MCP_SERVER_URL = "https://01c75753b9bf.ngrok-free.app/mcp"

BEARER_TOKEN = "abc123token"


PAYLOAD = {
    "tool_calls": [
        {
            "tool_name": "validate",
            "tool_input": {}
        }
    ]
}

# --- Main Logic ---
def test_connection():
    """
    Sends a POST request to the MCP server to test the 'validate' tool.
    """
    print(f"Attempting to connect to MCP server at: {MCP_SERVER_URL}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }

    try:
        response = requests.post(
            MCP_SERVER_URL,
            headers=headers,
            data=json.dumps(PAYLOAD)
        )

        # Check the status code and content of the response.
        response.raise_for_status()  # This will raise an exception for HTTP errors (4xx or 5xx).

        # Parse the JSON response.
        response_data = response.json()

        print("\n--- Success! ---")
        print("Response status code:", response.status_code)
        print("Response body:")
        print(json.dumps(response_data, indent=4))
        print("\nConnection successful. The server validated the token.")

    except requests.exceptions.HTTPError as http_err:
        # Handle HTTP-specific errors.
        print(f"\n--- HTTP Error! ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        print(f"An HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        # Handle connection-specific errors (e.g., server not running).
        print(f"\n--- Connection Error! ---")
        print(f"Could not connect to the server. Please check:")
        print(f"  - Is your server running (e.g., `uvicorn main:app --reload`)?")
        print(f"  - Is ngrok running and providing a public URL?")
        print(f"  - Is the `MCP_SERVER_URL` in this script correct?")
        print(f"An error occurred: {conn_err}")
    except Exception as err:
        # Handle all other potential errors.
        print(f"\n--- An Unexpected Error Occurred ---")
        print(f"An unexpected error occurred: {err}")

# To run the test, make sure to execute this script directly.
if __name__ == "__main__":
    test_connection()
