"""FastAPI app - chạy trên PC4 (master: mongos + backend + Neo4j)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from .routers import users, posts, social, admin
from .services import sync

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync.start_outbox_worker(interval_s=10)
    yield


app = FastAPI(
    title="Mini Social Network - Distributed Backend",
    description="MongoDB Sharded Cluster (4 nút) + Neo4j",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.exception_handler(PyMongoError)
def mongo_unavailable(request: Request, exc: PyMongoError):
    """Cụm MongoDB lỗi → trả 503 có thông báo rõ thay vì 500."""
    logging.getLogger("api").warning("MongoDB lỗi tại %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "MongoDB tạm thời không khả dụng, vui lòng thử lại sau"},
    )


app.include_router(users.router)
app.include_router(posts.router)
app.include_router(social.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"service": "mini-social-network", "docs": "/docs"}
