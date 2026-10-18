
import contextvars
import hashlib
import os

from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Scope, Receive, Send

EMAIL = "24f2005870@ds.study.iitm.ac.in"

request_headers = contextvars.ContextVar("request_headers", default={})


class HeaderCapture:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
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


# In MCP SDK 1.30, configure these options on FastMCP.
mcp = FastMCP(
    "Exam Challenge Server",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def solve_challenge() -> str:
    """Hash the fresh challenge provided in the HTTP request headers."""
    challenge = request_headers.get().get("x-exam-challenge")

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    message = f"{challenge}:{EMAIL.strip().lower()}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


# The app method receives the host, not stateless_http.
mcp_app = mcp.streamable_http_app(host="0.0.0.0")
app = HeaderCapture(mcp_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
