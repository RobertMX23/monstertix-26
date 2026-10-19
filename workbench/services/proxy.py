"""/svc/<name>/… → the service's own port (or, for a venue on Cloud Run, its URL).

Every app framed on the page comes through here, so the frames are same-origin
and Cloud Shell's Web Preview only needs the workbench's one port. Responses
are streamed, because the ADK web UI talks to its server over SSE.

The pages behind it ask for relative URLs, which resolve under the prefix.
A redirect to an absolute path (the venue's / → /panel) is given the prefix
on the way back.
"""

from __future__ import annotations

import httpx
from fastapi import Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from workbench.services import procs

HOP = {"connection", "keep-alive", "transfer-encoding", "upgrade", "proxy-authenticate",
       "proxy-authorization", "te", "trailer", "host", "content-length", "accept-encoding"}

_client = httpx.AsyncClient(timeout=httpx.Timeout(None, connect=5.0), follow_redirects=False)


async def forward(name: str, path: str, request: Request):
    if name not in procs.SERVICES or not procs.SERVICES[name].framable:
        return PlainTextResponse(f"no service named {name}", status_code=404)
    target = f"{procs.origin(name)}/{path}"
    if request.url.query:
        target += f"?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP}
    body = await request.body()
    try:
        upstream = await _client.send(
            _client.build_request(request.method, target, headers=headers, content=body or None),
            stream=True)
    except httpx.HTTPError:
        return PlainTextResponse(f"{procs.SERVICES[name].label} is not running", status_code=503)

    passed = {k: v for k, v in upstream.headers.items()
              if k.lower() not in HOP | {"content-encoding"}}
    location = upstream.headers.get("location")
    if location and location.startswith("/"):
        passed["location"] = f"/svc/{name}{location}"
    passed["cache-control"] = upstream.headers.get("cache-control", "no-store")

    async def body_stream():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()

    return StreamingResponse(body_stream(), status_code=upstream.status_code, headers=passed)
