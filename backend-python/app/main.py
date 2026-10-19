"""FastAPI app - chạy trên PC4 (master: mongos + backend + Neo4j)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.include_router(users.router)
app.include_router(posts.router)
app.include_router(social.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"service": "mini-social-network", "docs": "/docs"}
