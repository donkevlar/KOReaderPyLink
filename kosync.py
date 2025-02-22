# -*- coding: utf-8 -*-
import time
import uuid
from os import getenv

from dotenv import load_dotenv
from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tinydb import TinyDB, Query

app = FastAPI(openapi_url=None, redoc_url=None)
db = TinyDB("data/db.json")
users = db.table("users")
documents = db.table("documents")
load_dotenv()


def str_to_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")


class KosyncUser(BaseModel):
    username: str
    password: str


class KosyncDocument(BaseModel):
    document: str
    progress: str
    percentage: float
    device: str
    device_id: str


def get_auth_headers(
        x_auth_user: str = Header(...), x_auth_key: str = Header(...)
):
    """Dependency to extract authentication headers and validate user."""
    query = Query()
    user_exists = users.contains((query.username == x_auth_user) & (query.password == x_auth_key))
    if not user_exists:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_auth_user


@app.post("/users/create")
def register(kosync_user: KosyncUser):
    """Registers a new user if registration is allowed."""
    if not str_to_bool(getenv("OPEN_REGISTRATIONS", "True")):
        raise HTTPException(status_code=403, detail="Registrations are disabled.")

    query = Query()
    if users.contains(query.username == kosync_user.username):
        raise HTTPException(status_code=409, detail="Username is already registered.")

    users.insert({"username": kosync_user.username, "password": kosync_user.password})
    return JSONResponse(status_code=201, content={"username": kosync_user.username})


@app.get("/users/auth")
def authorize(auth_user: str = Depends(get_auth_headers)):
    """Validates user credentials."""
    return JSONResponse(status_code=200, content={"authorized": "OK"})


@app.put("/syncs/progress")
def update_progress(
        kosync_document: KosyncDocument,
        auth_user: str = Depends(get_auth_headers)
):
    """Updates document progress for a user."""
    timestamp = int(time.time())

    query = Query()
    documents.upsert(
        {
            "username": auth_user,
            "document": kosync_document.document,
            "progress": kosync_document.progress,
            "percentage": kosync_document.percentage,
            "device": kosync_document.device,
            "device_id": kosync_document.device_id,
            "timestamp": timestamp,
        },
        (query.username == auth_user) & (query.document == kosync_document.document),
    )

    return JSONResponse(status_code=200, content={"document": kosync_document.document, "timestamp": timestamp})


@app.get("/syncs/progress/{document}")
def get_progress(
        document: str,
        auth_user: str = Depends(get_auth_headers)
):
    """Retrieves progress of a document."""
    query = Query()
    result = documents.get((query.username == auth_user) & (query.document == document))

    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    # Determine device_id based on environment setting
    if str_to_bool(getenv("RECEIVE_RANDOM_DEVICE_ID", "False")):
        device_id = uuid.uuid4().hex.upper()
    else:
        device_id = result["device_id"]

    return JSONResponse(
        status_code=200,
        content={
            "username": auth_user,
            "document": result["document"],
            "progress": result["progress"],
            "percentage": result["percentage"],
            "device": result["device"],
            "device_id": device_id,
            "timestamp": result["timestamp"],
        },
    )


@app.get("/healthstatus")
def get_healthstatus():
    """Health check endpoint."""
    return JSONResponse(status_code=200, content={"message": "healthy"})
