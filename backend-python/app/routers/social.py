"""API xã hội - kết bạn, feed, gợi ý, cộng đồng (kết hợp Neo4j + MongoDB)."""
from fastapi import APIRouter, HTTPException
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from ..models import FriendRequest
from ..services import sync, social_graph

router = APIRouter(prefix="/social", tags=["social"])


@router.post("/friends")
def add_friend(body: FriendRequest):
    if body.from_user == body.to_user:
        raise HTTPException(400, "Không thể tự kết bạn")
    try:
        return sync.create_friendship_dual(body.from_user, body.to_user)
    except (Neo4jError, ServiceUnavailable, OSError) as e:
        raise HTTPException(503, f"Neo4j (PC4) không khả dụng: {e}")


@router.get("/friends/{user_id}")
def list_friends(user_id: str):
    try:
        return {"friends": social_graph.get_friend_ids(user_id)}
    except (Neo4jError, ServiceUnavailable, OSError) as e:
        raise HTTPException(503, f"Neo4j không khả dụng: {e}")


@router.get("/feed/{user_id}")
def feed(user_id: str, limit: int = 20):
    return social_graph.news_feed(user_id, limit)


@router.get("/suggestions/{user_id}")
def suggestions(user_id: str, limit: int = 10):
    return social_graph.suggest_friends(user_id, limit)


@router.get("/communities")
def communities():
    return social_graph.detect_communities()
