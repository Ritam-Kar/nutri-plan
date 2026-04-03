import asyncio
import json
import os
import time
import base64
from datetime import datetime, timedelta
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("calendar-mcp-server")

async def get_access_token():
    creds_path = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", "/app/service-account.json"
    )
    with open(creds_path) as f:
        creds = json.load(f)

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    now = int(time.time())
    payload = base64.urlsafe_b64encode(
        json.dumps({
            "iss": creds["client_email"],
            "scope": "https://www.googleapis.com/auth/calendar",
            "aud": "https://oauth2.googleapis.com/token",
            "exp": now + 3600,
            "iat": now
        }).encode()
    ).rstrip(b"=").decode()

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key = serialization.load_pem_private_key(
        creds["private_key"].encode(), password=None
    )
    signature = private_key.sign(
        f"{header}.{payload}".encode(), padding.PKCS1v15(), hashes.SHA256()
    )
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    jwt_token = f"{header}.{payload}.{sig_b64}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": jwt_token
            }
        )
        token_data = resp.json()
        if "access_token" not in token_data:
            raise Exception(f"Token error: {token_data}")
        return token_data["access_token"]


@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="create_calendar_event",
            description="Create a Google Calendar event for grocery shopping",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format. Today is 2026-04-03. Calculate the correct date from this."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in HH:MM 24-hour format IST"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "default": 60
                    },
                    "location": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["title", "date", "start_time", "location", "description"]
            }
        ),
        types.Tool(
            name="get_today_date",
            description="Get today's date in IST to help calculate future dates correctly",
            inputSchema={"type": "object", "properties": {}}
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_today_date":
        from datetime import timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        today = datetime.now(ist)
        return [types.TextContent(
            type="text",
            text=f"Today is {today.strftime('%Y-%m-%d')} ({today.strftime('%A')}) in IST"
        )]

    if name == "create_calendar_event":
        try:
            token = await get_access_token()
            calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

            date = arguments["date"]
            start_time = arguments["start_time"]
            duration = arguments.get("duration_minutes", 60)

            start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=duration)

            event = {
                "summary": arguments["title"],
                "location": arguments.get("location", ""),
                "description": arguments.get("description", ""),
                "start": {
                    "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "timeZone": "Asia/Kolkata"
                },
                "end": {
                    "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "timeZone": "Asia/Kolkata"
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [{"method": "popup", "minutes": 30}]
                }
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                    headers={"Authorization": f"Bearer {token}"},
                    json=event
                )
                result = resp.json()

            if "id" in result:
                return [types.TextContent(
                    type="text",
                    text=f"✅ Event created! Date: {date}, Time: {start_time} IST, Link: {result.get('htmlLink', 'N/A')}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"❌ API Error: {json.dumps(result)}"
                )]

        except Exception as e:
            return [types.TextContent(type="text", text=f"❌ Exception: {str(e)}")]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())