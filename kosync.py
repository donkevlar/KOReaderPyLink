# -*- coding: utf-8 -*-
import time
import uuid
import logging
from os import getenv
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tinydb import Query, TinyDB

app = FastAPI(openapi_url=None, redoc_url=None)
db = TinyDB("data/db.json")
users = db.table("users")
documents = db.table("documents")
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def str_to_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")


class KosyncUser(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class KosyncDocument(BaseModel):
    document: Optional[str] = None
    progress: Optional[str] = None
    percentage: Optional[float] = None
    device: Optional[str] = None
    device_id: Optional[str] = None


@app.post("/users/create")
def register(kosync_user: KosyncUser):
    registrations_allowed = str_to_bool(getenv("OPEN_REGISTRATIONS", "True"))
    if registrations_allowed:
        if kosync_user.username is None or kosync_user.password is None:
            return JSONResponse(status_code=400, content={"message": "Invalid request"})
        QUser = Query()
        if users.contains(QUser.username == kosync_user.username):
            return JSONResponse(status_code=409, content="Username is already registered.")
        if users.insert({'username': kosync_user.username, 'password': kosync_user.password}):
            logging.info(f"User {kosync_user.username} registered successfully.")
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
