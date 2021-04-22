from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserPydantic(BaseModel):
    username: str
    email: Optional[str] = None
    # hashed_password: str
    avatar: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class MessageRequest(BaseModel):
    sender_id: int
    recipient_id: int
    content: str
    date: Optional[datetime] = datetime.now()


class OutgoingMessage(BaseModel):
    recipient: str
    content: str


class MessageResponse(BaseModel):
    sender: str
    sender_avatar: str
    recipient: str
    recipient_avatar: str
    content: str
    date: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


