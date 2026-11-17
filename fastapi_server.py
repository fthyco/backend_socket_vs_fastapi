"""The same API using FastAPI, with the same application logic."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app_logic import InputError, UserStore

app = FastAPI(title="Users API - FastAPI")
store = UserStore()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/users")
def list_users():
    return store.list_users()


@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = store.get_user(user_id)
    if user is None:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    return user


@app.post("/users", status_code=201)
def create_user(payload: dict[str, Any]):
    try:
        return store.create_user(payload)
    except InputError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
