from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
import random

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from models_pyd import MessageResponse, UserPydantic, RegisterRequest, MessageRequest
import RPS
from models_DB import UserDB, MessageDB, RPS_PlayerDB, RockPaperScissorsDB


# populates the database with a bunch of user accounts and messages, RPS games and moves
def populate(db: Session):
    alex = RegisterRequest(username="alex", email="alex@example.com", password="geheim")
    create_user(register_request=alex, db=db)

    martha = RegisterRequest(username="martha", email="martha@example.com", password="secret")
    create_user(register_request=martha, db=db)

    ivan = RegisterRequest(username="ivan", email="ivan@example.com", password="juri")
    create_user(register_request=ivan, db=db)

    ivan = db.query(UserDB).filter(UserDB.username == "ivan").one_or_none()
    alex = db.query(UserDB).filter(UserDB.username == "alex").one_or_none()
    martha = db.query(UserDB).filter(UserDB.username == "martha").one_or_none()
    set_avatar('zac', ivan, db)
    set_avatar('lucian', alex, db)
    set_avatar('lilia', martha, db)

    time = str(datetime.now().time())[0:5]
    msg = MessageRequest(sender_id=ivan.id, content="Hallo um, " + time, recipient_id=alex.id)
    create_message(message_request=msg, db=db)

    time = str(datetime.now().time())[0:5]
    msg = MessageRequest(sender_id=martha.id, content="Hiiii um, " + time, recipient_id=alex.id)
    create_message(message_request=msg, db=db)

    time = str(datetime.now().time())[0:5]
    msg = MessageRequest(sender_id=alex.id, content="brooo, um " + time, recipient_id=ivan.id)
    create_message(message_request=msg, db=db)

    time = str(datetime.now().time())[0:5]
    msg = MessageRequest(sender_id=martha.id, content="juri wird so cuuuute, um " + time, recipient_id=ivan.id)
    create_message(message_request=msg, db=db)

    # print("ids ivan, alex: ", ivan.id, alex.id)
    # # no bidirectionality
    # print("ivan sent:")
    # print([msg.content for msg in db.query(MessageDB).filter(MessageDB.sender == ivan)])
    # print("alex received:")
    # print([msg.content for msg in db.query(MessageDB).filter(MessageDB.recipient == alex)])

    # for i in range(0, 4):
    #     rps_request = RPS.Game_Request(player1="alex", player2="ivan", goal=2)
    #     RPS.create_game(rps_request, db)
    # find ivan's oldest unfinished game

    # for i in range(0, 5):
    #     # filter for unfinished games with ivan in them
    #     martha_games = RPS.getGames(martha, db)
    #     martha_games = martha_games.filter(RockPaperScissorsDB.finished == False)
    #     # sort by date created, oldest first
    #     martha_games = martha_games.order_by(RockPaperScissorsDB.date_created)
    #     game = martha_games.first()
    #     print("marthas oldest unfinished is #", game.id)
    #
    #     # commit a random move for both of us, to a random game
    #     game = martha_games.all()[random.randint(0, len(martha_games.all()) - 1)]
    #     move_request = RPS.Move_Request(move=random.randint(0, 2), user_id=martha.id, game_id=game.id)
    #     RPS.commit_move(move_request, db)
    #     move_request = RPS.Move_Request(move=random.randint(0, 2), user_id=alex.id, game_id=game.id)
    #     RPS.commit_move(move_request, db)


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
    return MessageResponse(sender=message_db.sender.username, sender_avatar=message_db.sender.avatar,
                           recipient=message_db.recipient.username, recipient_avatar=message_db.recipient.avatar,
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


def create_message(message_request: MessageRequest, db: Session):
    sender = db.query(UserDB).filter(UserDB.id == message_request.sender_id).one_or_none()
    recipient = db.query(UserDB).filter(UserDB.id == message_request.recipient_id).one_or_none()
    if not sender or not recipient:
        return None
    msg = MessageDB(
        content=message_request.content,
        date=message_request.date,
        sender_id=message_request.sender_id,
        recipient_id=message_request.recipient_id
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def set_avatar(name: str, user: UserDB, db: Session):
    user.avatar = name
    db.add(user)
    db.commit()
    db.refresh(user)
