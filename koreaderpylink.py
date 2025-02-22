# -*- coding: utf-8 -*-
import os
import time
import uuid
import logging
from os import getenv
from typing import Optional

from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, HttpUrl
from tinydb import Query, TinyDB

app = FastAPI(openapi_url=None, redoc_url=None)
db = TinyDB("data/db.json")
users = db.table("users")
documents = db.table("documents")
load_dotenv()

logging = logging.getLogger("uvicorn")


def str_to_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")


# User Model
class KosyncUser(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


# Document Model
class KosyncDocument(BaseModel):
    document: Optional[str] = None
    progress: Optional[str] = None
    percentage: Optional[float] = None
    device: Optional[str] = None
    device_id: Optional[str] = None


# Discord Payload Model
class DiscordPayload(BaseModel):
    content: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    tts: Optional[bool] = False


# Customizable webhook example: Send to discord webhook whenever a user connects to the service.
async def send_webhook_discord(payload: DiscordPayload, webhook_url: str = os.getenv('WEBHOOK_URL'),
                               webhook_enabled: bool = str_to_bool(os.getenv('WEBHOOK_ENABLED', 'False'))):
    if webhook_enabled and webhook_url != '':
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload.model_dump())
            logging.info(f'Sent Webhook to {webhook_url}, Status: {response.status_code}')
            # If response has content, parse as JSON, otherwise return status only
            try:
                response_json = response.json() if response.content else None
            except Exception as e:
                response_json = None  # Handle cases where Discord returns non-JSON data

            return {"status": response.status_code, "response": response_json}


# redirects to healthstatus when no endpoint is used.
@app.get("/", include_in_schema=False)  # Hide from OpenAPI docs
def root():
    return RedirectResponse(url="/healthstatus")


@app.post("/users/create")
async def register(kosync_user: KosyncUser):
    registrations_allowed = str_to_bool(getenv("OPEN_REGISTRATIONS", "True"))
    if registrations_allowed:
        if kosync_user.username is None or kosync_user.password is None:
            return JSONResponse(status_code=400, content={"message": "Invalid request"})
        QUser = Query()
        if users.contains(QUser.username == kosync_user.username):
            return JSONResponse(status_code=409, content="Username is already registered.")
        if users.insert({'username': kosync_user.username, 'password': kosync_user.password}):
            logging.info(f"User {kosync_user.username} registered successfully.")
            if str_to_bool(os.getenv('WEBHOOK_ENABLED', 'False')):
                # Create Webhook Payload
                payload = DiscordPayload()
                payload.content = f"User **{kosync_user.username}** has successfully registered to KOReaderPyLink!"
                payload.username = "KOReaderPyLink"
                payload.avatar_url = 'https://donkevlar.github.io/KOReaderPyLink/icon/pylink.png'

                response = await send_webhook_discord(payload=payload)

            return JSONResponse(status_code=201, content={"username": kosync_user.username})
        return JSONResponse(status_code=500, content="Unknown server error")
    else:
        return JSONResponse(status_code=403, content="This server is currently not accepting new registrations.")


@app.get("/users/auth")
def authorize(x_auth_user: Optional[str] = Header(None), x_auth_key: Optional[str] = Header(None)):
    if x_auth_user is None or x_auth_key is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    QUser = Query()
    if users.contains(QUser.username == x_auth_user):
        if users.contains((QUser.username == x_auth_user) & (QUser.password == x_auth_key)):
            logging.info(f"User {x_auth_user} successfully authenticated.")
            return JSONResponse(status_code=200, content={"authorized": "OK"})
        else:
            return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    return JSONResponse(status_code=403, content={"message": "Forbidden"})


@app.put("/syncs/progress")
def update_progress(kosync_document: KosyncDocument, x_auth_user: Optional[str] = Header(None),
                    x_auth_key: Optional[str] = Header(None)):
    if x_auth_user is None or x_auth_key is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    QUser = Query()
    QDocument = Query()
    if not users.contains(QUser.username == x_auth_user):
        return JSONResponse(status_code=403, content={"message": "Forbidden"})
    if users.contains((QUser.username == x_auth_user) & (QUser.password == x_auth_key)):
        timestamp = int(time.time())
        if kosync_document.document is None or kosync_document.progress is None or kosync_document.percentage is None \
                or kosync_document.device is None or kosync_document.device_id is None:
            return JSONResponse(status_code=500, content="Unknown server error")
        else:
            if documents.upsert({'username': x_auth_user, 'document': kosync_document.document,
                                 'progress': kosync_document.progress, 'percentage': kosync_document.percentage,
                                 'device': kosync_document.device, 'device_id': kosync_document.device_id,
                                 'timestamp': timestamp}, (QDocument.username == x_auth_user) &
                                                          (QDocument.document == kosync_document.document)):
                logging.info(f"User {x_auth_user} updated progress for document {kosync_document.document}.")
                return JSONResponse(status_code=200,
                                    content={"document": kosync_document.document, "timestamp": timestamp})
    else:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})


@app.get("/syncs/progress/{document}")
def get_progress(document: Optional[str] = None, x_auth_user: Optional[str] = Header(None),
                 x_auth_key: Optional[str] = Header(None)):
    if x_auth_user is None or x_auth_key is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    if document is None:
        return JSONResponse(status_code=500, content="Unknown server error")
    QUser = Query()
    QDocument = Query()
    if not users.contains(QUser.username == x_auth_user):
        return JSONResponse(status_code=403, content={"message": "Forbidden"})
    if users.contains((QUser.username == x_auth_user) & (QUser.password == x_auth_key)):
        result = documents.get((QDocument.username == x_auth_user) & (QDocument.document == document))
        if result:
            rrdi = str_to_bool(getenv("RECEIVE_RANDOM_DEVICE_ID", "False"))
            device_id = result["device_id"] if not rrdi else str(uuid.uuid1().hex).upper()
            logging.info(f"User {x_auth_user} retrieved progress for document {document}.")
            return JSONResponse(status_code=200,
                                content={'username': x_auth_user, 'document': result["document"],
                                         'progress': result["progress"], 'percentage': result["percentage"],
                                         'device': result["device"], 'device_id': device_id,
                                         'timestamp': result["timestamp"]})
    else:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})


@app.get("/healthstatus")
def get_healthstatus():
    return JSONResponse(status_code=200, content={"message": "healthy"})
