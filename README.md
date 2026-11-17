# HTTP from raw TCP sockets vs. FastAPI

Both servers implement the same endpoints and import the same Python business logic (`app_logic.py`):

| Method | Path | Result |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` |
| GET | `/users` | List of users |
| POST | `/users` | Create a user from JSON `{"name":"Ali","age":21}` |
| GET | `/users/{id}` | Fetch a user by ID |

Data is held in memory: restarting a server resets its users. The two servers use separate process memory.

## Run the socket version (stdlib only)

```bash
python3 socket_server.py --port 8080
```

## Run the FastAPI version (separate terminal)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn fastapi_server:app --host 127.0.0.1 --port 8000
```

## Test with curl

Change `8080` to `8000` to test the FastAPI version.

```bash
curl -i http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/users
curl -i -X POST http://127.0.0.1:8080/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ali","age":21}'
curl -i http://127.0.0.1:8080/users/1
curl -i http://127.0.0.1:8080/users/999
```

Automatic OpenAPI documentation for FastAPI: http://127.0.0.1:8000/docs

## Test both (needs FastAPI and Uvicorn installed)

```bash
python test_api.py
```

## Deliberate limits of the educational socket server

- Single-threaded: one client is served at a time
- One HTTP request per TCP connection (`Connection: close`)
- Requires `Content-Length` for POST; no chunked Transfer-Encoding
- At most 16 KiB headers, 1 MiB body
- No TLS/HTTPS, authentication, streaming, production hardening, or HTTP/2
- Bind only to localhost; not suitable for exposure to the public internet

Some framework-generated errors (such as a malformed path parameter or unsupported content type) differ. The shared app-level routes and successful responses are the same.
