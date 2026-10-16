"""程序入口：uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import handlers
from .db import pool
from .routers import auth, requests

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="企业审批系统", lifespan=lifespan)
handlers.install(app)

app.include_router(auth.router, prefix="/api")
app.include_router(requests.router, prefix="/api")

# 页面和 js、css。放在最后挂载，/api 开头的请求先被上面的路由接走
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
