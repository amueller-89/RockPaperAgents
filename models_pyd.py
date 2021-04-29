from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GameType(BaseModel):
    name: str
    color: str
    active: bool


class UserPydantic(BaseModel):
    username: str
    email: Optional[str] = None
    avatar: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class MessageRequest(BaseModel):
    sender_id: int
    recipient_id: Optional[str] = None
    content: str
    date: Optional[datetime] = datetime.now()


class ChatMessage(BaseModel):
    message: str


class OutgoingMessage(BaseModel):
    recipient: str
    content: str


class MessageResponse(BaseModel):
    type: str = "message"
    sender: str
    sender_avatar: str
    recipient: str
    recipient_avatar: str
    content: str
    date: datetime


class ChatResponse(BaseModel):
    type: str = "chat"
    sender: str
    sender_avatar: str
    content: str
    date: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
