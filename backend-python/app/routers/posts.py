"""API bài viết & bình luận - lưu MongoDB, shard theo author_id / post_id."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pymongo.errors import PyMongoError

from ..models import PostCreate, CommentCreate
from ..services import interests
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
    # Chủ đề bài viết → sở thích của tác giả (Neo4j) để gợi ý kết bạn theo nội dung
    interests.record_interest(body.author_id, body.content, interests.WEIGHT_POST, "post")
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


def _get_post(post_id: str) -> dict:
    p = dbx.db.posts.find_one({"_id": post_id})  # không có shard key → scatter-gather
    if not p:
        raise HTTPException(404, "Không tìm thấy bài viết")
    return p


@router.get("/{post_id}")
def get_post(post_id: str):
    return _get_post(post_id)


@router.post("/{post_id}/view")
def view_post(post_id: str, x_user_id: str | None = Header(default=None)):
    """User mở xem bài → ghi nhận quan tâm tới chủ đề của bài."""
    p = _get_post(post_id)
    if x_user_id and x_user_id != p["author_id"]:
        kws = interests.record_interest(x_user_id, p.get("content", ""), interests.WEIGHT_VIEW, "view",
                                         target_id=p["author_id"])
        return {"status": "ok", "keywords": kws}
    return {"status": "ok", "keywords": []}


@router.post("/{post_id}/like")
def like_post(post_id: str, x_user_id: str | None = Header(default=None)):
    p = dbx.db.posts.find_one_and_update({"_id": post_id}, {"$inc": {"likes": 1}})
    if not p:
        raise HTTPException(404, "Không tìm thấy bài viết")
    if x_user_id and x_user_id != p["author_id"]:
        interests.record_interest(x_user_id, p.get("content", ""), interests.WEIGHT_LIKE, "like",
                                  target_id=p["author_id"])
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
    post = dbx.db.posts.find_one({"_id": body.post_id}, {"author_id": 1, "content": 1})
    if post and post["author_id"] != body.author_id:
        interests.record_interest(body.author_id, post.get("content", ""), interests.WEIGHT_COMMENT, "comment",
                                  target_id=post["author_id"])
    return doc


@router.get("/{post_id}/comments")
def get_comments(post_id: str, limit: int = 50):
    return list(
        dbx.db.comments.find({"post_id": post_id}).sort("created_at", 1).limit(limit)
    )
