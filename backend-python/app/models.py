"""Pydantic models cho API."""
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=4, max_length=100)
    full_name: str = ""
    avatar_url: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class PostCreate(BaseModel):
    author_id: str
    content: str = Field(min_length=1, max_length=5000)
    image_urls: list[str] = []


class CommentCreate(BaseModel):
    post_id: str
    author_id: str
    content: str = Field(min_length=1, max_length=2000)


class FriendRequest(BaseModel):
    from_user: str
    to_user: str
