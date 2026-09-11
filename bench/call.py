"""Calling an application without a web server in the way.

A server would measure the server. Each stack is called at its own
native interface instead -- WSGI applications directly, ASGI ones
through a plain loop -- so what is timed is the framework and what it
does with the database.
"""

import asyncio
import io


def wsgi(app, method, path, body=b""):
    environ = {
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "PATH_INFO": path.split("?")[0],
        "QUERY_STRING": path.split("?")[1] if "?" in path else "",
        "SERVER_NAME": "bench",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_HOST": "bench",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": io.BytesIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "CONTENT_LENGTH": str(len(body)),
    }
    if body:
        environ["CONTENT_TYPE"] = "application/json"

    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = int(status.split()[0])

    chunks = app(environ, start_response)
    try:
        payload = b"".join(chunks)
    finally:
        if hasattr(chunks, "close"):
            chunks.close()
    return captured["status"], payload


class AsgiCaller(object):
    """One loop, reused: a fresh loop per call would time the loop."""

    def __init__(self, app):
        self._app = app
        self._loop = asyncio.new_event_loop()

    def startup(self):
        self._loop.run_until_complete(self._lifespan("startup"))

    def shutdown(self):
        try:
            self._loop.run_until_complete(self._lifespan("shutdown"))
        finally:
            self._loop.close()

    async def _lifespan(self, event):
        received = [{"type": "lifespan.%s" % event}]
        done = asyncio.Event()

        async def receive():
            if received:
                return received.pop()
            await done.wait()
            return {"type": "lifespan.shutdown"}

        async def send(message):
            if message["type"].endswith((".complete", ".failed")):
                done.set()

        try:
            await asyncio.wait_for(
                self._app(
                    {"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send
                ),
                timeout=5,
            )
        except Exception:
            # A stack with no lifespan of its own is not a failure.
            pass

    def __call__(self, method, path, body=b""):
        return self._loop.run_until_complete(self._call(method, path, body))

    async def _call(self, method, path, body):
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path.split("?")[0],
            "raw_path": path.split("?")[0].encode(),
            "query_string": (path.split("?")[1] if "?" in path else "").encode(),
            "root_path": "",
            "headers": [(b"host", b"bench")]
            + ([(b"content-type", b"application/json")] if body else [])
            + [(b"content-length", str(len(body)).encode())],
            "client": ("127.0.0.1", 1234),
            "server": ("bench", 80),
        }
        sent = {"status": None, "body": bytearray()}
        request_body = [{"type": "http.request", "body": body, "more_body": False}]

        async def receive():
            if request_body:
                return request_body.pop()
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.start":
                sent["status"] = message["status"]
            elif message["type"] == "http.response.body":
                sent["body"] += message.get("body", b"")

        await self._app(scope, receive, send)
        return sent["status"], bytes(sent["body"])
