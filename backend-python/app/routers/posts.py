"""API bài viết & bình luận - lưu MongoDB, shard theo author_id / post_id."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from ..models import PostCreate, CommentCreate
from .. import database as dbx

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("")
def create_post(body: PostCreate):
    doc = {
        "_id": str(uuid.uuid4()),
        "author_id": body.author_id,
        "content": body.content,
        "image_urls": body.image_urls,
        "likes": 0,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        dbx.db.posts.insert_one(doc)  # mongos định tuyến tới shard theo hash(author_id)
    except PyMongoError as e:
        raise HTTPException(503, f"MongoDB cluster lỗi: {e}")
    return doc


@router.get("/by-author/{author_id}")
def posts_by_author(author_id: str, limit: int = 20):
    """Truy vấn TARGETED: có shard key → chỉ chạm 1 shard."""
    return list(
        dbx.db.posts.find({"author_id": author_id}).sort("created_at", -1).limit(limit)
    )


@router.get("/search")
def search_posts(q: str, limit: int = 20):
    """Truy vấn SCATTER-GATHER: không có shard key → quét mọi shard."""
    return list(
        dbx.db.posts.find({"content": {"$regex": q, "$options": "i"}}).limit(limit)
    )


@router.post("/{post_id}/like")
def like_post(post_id: str):
    r = dbx.db.posts.update_one({"_id": post_id}, {"$inc": {"likes": 1}})
    if not r.matched_count:
        raise HTTPException(404, "Không tìm thấy bài viết")
    return {"status": "ok"}


@router.post("/comments", tags=["comments"])
def create_comment(body: CommentCreate):
    doc = {
        "_id": str(uuid.uuid4()),
        "post_id": body.post_id,
        "author_id": body.author_id,
        "content": body.content,
        "created_at": datetime.now(timezone.utc),
    }
    dbx.db.comments.insert_one(doc)
    return doc


@router.get("/{post_id}/comments")
def get_comments(post_id: str, limit: int = 50):
    return list(
        dbx.db.comments.find({"post_id": post_id}).sort("created_at", 1).limit(limit)
    )
