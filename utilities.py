from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from time import sleep
import random

from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from models_pyd import MessageResponse, UserPydantic, RegisterRequest, MessageRequest, ChatResponse
import Game
from models_DB import UserDB, MessageDB, RockPaperScissorsDB


# populates the database with a bunch of user accounts and messages, RPS games and moves
def populate(db: Session):
    alex = RegisterRequest(username="alex", email="alex@example.com", password="alex")
    create_user(register_request=alex, db=db)

    clara = RegisterRequest(username="CoolCatClara", email="clara@example.com", password="clara")
    create_user(register_request=clara, db=db)

    linos = RegisterRequest(username="LinosSup!", email="linos@example.com", password="linos")
    create_user(register_request=linos, db=db)

    asd = RegisterRequest(username="asd", email="asd@example.com", password="asd")
    create_user(register_request=asd, db=db)

    linos = db.query(UserDB).filter(UserDB.username == "CoolCatClara").one_or_none()
    alex = db.query(UserDB).filter(UserDB.username == "alex").one_or_none()
    clara = db.query(UserDB).filter(UserDB.username == "CoolCatClara").one_or_none()
    set_avatar('zac', linos, db)
    set_avatar('lucian', alex, db)
    set_avatar('lilia', clara, db)

    chat = ["Hallo wer will spielen?", "ja ich bitte", "slipstrike oder rps?",
            "mega bock auf scheresteinpapier, bis 7?", "ja lets go"]
    i = 0
    for m in chat:
        print(f"creating chat message {i}")
        create_chat_message(
            MessageRequest(sender_id=alex.id if i % 2 == 0 else clara.id, content=m, date=datetime.now()), db)
        i += 1
        sleep(.5)

    rps_request = Game.Game_Request(player1="alex", player2="CoolCatClara", type="rps", goal= 7)
    Game.create_game(rps_request, db)


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        self.active_connections.pop(username)

    def connections(self):
        return [key for key in self.active_connections]

    async def send_rps(self, response: Game.Game_Response, opp: str):
        if opp not in self.active_connections:
            print("opp not online")
            return
        await self.active_connections[opp].send_json(response.json())

    async def inform_opponent(self, game: RockPaperScissorsDB, me: str):
        for p in game.players:
            if p.user.username != me:
                opponent = p.user.username
                print("vs opponent: " + opponent)
        response = Game.make_response_from_db(game=game, my_name=opponent)
        if opponent not in self.active_connections:
            print("opp not online")
            return
        await self.active_connections[opponent].send_json(response.json())

    async def inform_recipient(self, message: MessageResponse):
        if message.recipient not in self.active_connections:
            print("recipient not online")
            return
        await self.active_connections[message.recipient].send_json(message.json())

    async def inform_chat(self, message: ChatResponse):
        for user in self.active_connections:
            print(f"sending to {user}")
            await self.active_connections[user].send_json(message.json())


# security settings and initializations
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# utility methods for handling password-hashing, avoids importing the password context into main
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def get_hashed_password(plain):
    return pwd_context.hash(plain)


# creates JWT token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=5))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


#  returns the pydantic model of the current user from the JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        # token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user_pyd = get_pyd_user_from_db(username)
    if user_pyd is None:
        raise credentials_exception
    return user_pyd


# sets up database session, used in dependency injection system
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close


# bridging SQLAlchemy and pydantic model
def make_message_response_from_db(message_db: MessageDB):
    if message_db.recipient is not None:
        return MessageResponse(sender=message_db.sender.username, sender_avatar=message_db.sender.avatar,
                               recipient=message_db.recipient.username,
                               recipient_avatar=message_db.recipient.avatar,
                               content=message_db.content, date=message_db.date)
    else:
        return ChatResponse(sender=message_db.sender.username, sender_avatar=message_db.sender.avatar,
                            content=message_db.content, date=message_db.date)


# bridging SQLAlchemy and pydantic model
def make_user_pydantic_from_db(user_db: UserDB):
    user_pyd = UserPydantic(username=user_db.username)
    user_pyd.email = user_db.email
    user_pyd.avatar = user_db.avatar
    return user_pyd


# bridging SQLAlchemy and pydantic model
def get_pyd_user_from_db(username: str):
    # print(">>>>>>>>> obtaining pydantic user for username " + username)
    db = SessionLocal()
    user_db = db.query(UserDB).filter(UserDB.username == username).one_or_none()
    if user_db:
        return make_user_pydantic_from_db(user_db)
    else:
        return None


# database utilities
def get(username: str, db: Session):
    return db.query(UserDB).filter(UserDB.username == username).one_or_none()


def create_user(register_request: RegisterRequest, db: Session):
    if db.query(UserDB).filter(UserDB.username == register_request.username).one_or_none():
        return None
    user = UserDB()
    user.username = register_request.username
    user.hashed_password = get_hashed_password(register_request.password)
    user.email = register_request.email
    user.avatar = "default"
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_chat_message(message_request: MessageRequest, db: Session):
    sender = db.query(UserDB).filter(UserDB.id == message_request.sender_id).one_or_none()
    if not sender:
        return None
    message = MessageDB(
        content=message_request.content,
        date=message_request.date,
        sender_id=message_request.sender_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def create_message(message_request: MessageRequest, db: Session):
    sender = db.query(UserDB).filter(UserDB.id == message_request.sender_id).one_or_none()
    recipient = db.query(UserDB).filter(UserDB.id == message_request.recipient_id).one_or_none()
    if not sender or not recipient:
        return None
    message = MessageDB(
        content=message_request.content,
        date=message_request.date,
        sender_id=message_request.sender_id,
        recipient_id=message_request.recipient_id
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def set_avatar(name: str, user: UserDB, db: Session):
    user.avatar = name
    db.add(user)
    db.commit()
    db.refresh(user)
