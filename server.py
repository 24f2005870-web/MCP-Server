
import contextvars
import hashlib
import os

from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Scope, Receive, Send

EMAIL = "24f2005870@ds.study.iitm.ac.in"

# Isolated per HTTP request, including concurrent calls.
request_headers = contextvars.ContextVar("request_headers", default={})


class HeaderCapture:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

        token = request_headers.set(headers)
        try:
            await self.app(scope, receive, send)
        finally:
            request_headers.reset(token)


mcp = FastMCP("Exam Challenge Server", json_response=True)


@mcp.tool()
def solve_challenge() -> str:
    """Return the SHA-256 challenge response from the current HTTP headers."""
    headers = request_headers.get()
    challenge = headers.get("x-exam-challenge")

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    result = hashlib.sha256(
        f"{challenge}:{EMAIL.strip().lower()}".encode("utf-8")
    ).hexdigest()[:16]

    return result


# Use the SDK's MCP endpoint and capture headers on each HTTP request.
mcp_app = mcp.streamable_http_app(
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
)
app = HeaderCapture(mcp_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
