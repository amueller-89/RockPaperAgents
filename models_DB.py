from sqlalchemy import Table, Column, String, Boolean, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from database import Base


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String)
    avatar = Column(String)
    plays = relationship(
        "RPS_PlayerDB",
        back_populates="user"
    )


class RPS_PlayerDB(Base):
    __tablename__ = "playersRPS"

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Integer, default=0)
    committed_move = Column(Integer)
    won = Column(Boolean)  # None - not finished, true/false = yes/no

    moves = Column(String, default="")
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("UserDB", back_populates="plays")

    game_id = Column(Integer, ForeignKey("rps.id"))
    game = relationship("RockPaperScissorsDB", back_populates="players")


class RockPaperScissorsDB(Base):
    __tablename__ = "rps"

    id = Column(Integer, primary_key=True, index=True)
    players = relationship("RPS_PlayerDB", back_populates="game")
    finished = Column(Boolean, default=False)  # redundant so remove?
    goal = Column(Integer, default=3)
    date_created = Column(DateTime)
    last_activity = Column(DateTime)


class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    date = Column(DateTime)

    sender_id = Column(Integer, ForeignKey("users.id"))
    sender = relationship("UserDB", foreign_keys=sender_id)

    recipient_id = Column(Integer, ForeignKey("users.id"))  # none = public chat
    recipient = relationship("UserDB", foreign_keys=recipient_id)
