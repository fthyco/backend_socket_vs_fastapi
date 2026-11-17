"""End-to-end smoke test: start each server, exercise HTTP, then shut it down."""

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(port, method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def run_scenario(command):
    port = find_port()
    proc = subprocess.Popen(command(port), cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(60):
            if proc.poll() is not None:
                raise RuntimeError(f"Server exited early: {proc.stderr.read().decode()}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            raise RuntimeError("Server did not start")

        assert request(port, "GET", "/health") == (200, {"status": "ok"})
        assert request(port, "GET", "/users") == (200, {"users": []})
        assert request(port, "POST", "/users", {"name": "Ali", "age": 21}) == (
            201, {"id": 1, "name": "Ali", "age": 21}
        )
        assert request(port, "GET", "/users/1") == (200, {"id": 1, "name": "Ali", "age": 21})
        assert request(port, "GET", "/users") == (200, {"users": [{"id": 1, "name": "Ali", "age": 21}]})
        assert request(port, "GET", "/users/999") == (404, {"error": "User not found"})
        assert request(port, "POST", "/users", {"name": " ", "age": 21}) == (
            400, {"error": "name must be a non-empty string"}
        )
        print(f"PASS: {command(port)[1]}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        proc.stderr.close()


if __name__ == "__main__":
    run_scenario(lambda port: [sys.executable, "socket_server.py", "--port", str(port)])
    run_scenario(lambda port: [sys.executable, "-m", "uvicorn", "fastapi_server:app", "--port", str(port), "--host", "127.0.0.1"])
    print("All API tests passed")
