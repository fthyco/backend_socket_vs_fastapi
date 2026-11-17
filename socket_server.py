"""Educational HTTP/1.1 server built directly on TCP sockets; no web framework.

Supports only small, non-chunked requests and closes each connection after one
response. Intentionally not production-ready.
"""

import argparse
import json
import re
import socket
from http import HTTPStatus
from urllib.parse import urlsplit

from app_logic import InputError, UserStore

MAX_HEADER = 16 * 1024
MAX_BODY = 1024 * 1024
store = UserStore()


class HTTPError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


def read_request(connection):
    reader = connection.makefile("rb")
    try:
        line = reader.readline(8193)
        if not line or len(line) > 8192:
            raise HTTPError(400, "Invalid request line")
        try:
            method, target, version = line.decode("ascii").strip().split()
        except (UnicodeDecodeError, ValueError):
            raise HTTPError(400, "Invalid request line") from None
        if version not in ("HTTP/1.0", "HTTP/1.1"):
            raise HTTPError(400, "Unsupported HTTP version")

        headers = {}
        size = 0
        while True:
            line = reader.readline(8193)
            size += len(line)
            if not line or size > MAX_HEADER or len(line) > 8192:
                raise HTTPError(431, "Invalid or oversized headers")
            if line in (b"\r\n", b"\n"):
                break
            if b":" not in line:
                raise HTTPError(400, "Malformed header")
            key, value = line.split(b":", 1)
            try:
                key = key.decode("ascii").strip().lower()
                value = value.decode("latin-1").strip()
            except UnicodeDecodeError:
                raise HTTPError(400, "Malformed header") from None
            if key in headers:
                raise HTTPError(400, "Duplicate header is not supported")
            headers[key] = value

        if "transfer-encoding" in headers:
            raise HTTPError(501, "Transfer-Encoding is not supported")

        length_text = headers.get("content-length")
        if method == "POST" and length_text is None:
            raise HTTPError(411, "Content-Length is required")
        if length_text is not None and not length_text.isascii():
            raise HTTPError(400, "Invalid Content-Length")
        if length_text is not None and not length_text.isdecimal():
            raise HTTPError(400, "Invalid Content-Length")
        length = int(length_text) if length_text is not None else 0
        if length > MAX_BODY:
            raise HTTPError(413, "Request body too large")
        body = reader.read(length)
        if len(body) != length:
            raise HTTPError(400, "Incomplete request body")
        path = urlsplit(target).path
        return method, path, headers, body
    finally:
        reader.close()


def route(method, path, headers, body):
    if method == "GET" and path == "/health":
        return 200, {"status": "ok"}
    if method == "GET" and path == "/users":
        return 200, store.list_users()

    match = re.fullmatch(r"/users/([0-9]+)", path)
    if method == "GET" and match:
        user = store.get_user(int(match.group(1)))
        if user is None:
            raise HTTPError(404, "User not found")
        return 200, user

    if method == "POST" and path == "/users":
        if headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise HTTPError(415, "Content-Type must be application/json")
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPError(400, "Invalid JSON body") from None
        try:
            return 201, store.create_user(payload)
        except InputError as exc:
            raise HTTPError(400, str(exc)) from exc

    if method not in ("GET", "POST"):
        raise HTTPError(405, "Method not allowed")
    if path in ("/health", "/users") or match:
        raise HTTPError(405, "Method not allowed")
    raise HTTPError(404, "Route not found")


def send_json(connection, status, payload):
    content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    reason = HTTPStatus(status).phrase
    response_head = (
        f"HTTP/1.1 {status} {reason}\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(content)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")
    connection.sendall(response_head + content)


def main(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen(5)
        print(f"Raw socket HTTP server: http://127.0.0.1:{port}", flush=True)
        try:
            while True:
                connection, _address = server.accept()
                with connection:
                    connection.settimeout(5)
                    try:
                        method, path, headers, body = read_request(connection)
                        status, payload = route(method, path, headers, body)
                    except HTTPError as exc:
                        status, payload = exc.status, {"error": exc.message}
                    except (OSError, TimeoutError):
                        status, payload = 400, {"error": "Connection error"}
                    try:
                        send_json(connection, status, payload)
                    except OSError:
                        pass  # The client disconnected before the response was sent.
        except KeyboardInterrupt:
            print("\nStopping server")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    main(parser.parse_args().port)
