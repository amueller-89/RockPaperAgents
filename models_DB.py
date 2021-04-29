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


class GameDB(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    players = relationship("PlayerDB", back_populates="game")

    finished = Column(Boolean, default=False)
    date_created = Column(DateTime)
    last_activity = Column(DateTime)
    history = Column(String, default="")

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'game'
    }


class RockPaperScissorsDB(GameDB):
    goal = Column(Integer, default=3)

    __mapper_args__ = {
        'polymorphic_identity': 'rps'
    }


class SlipStrikeDB(GameDB):
    state = Column(Integer)  # None - between rounds, 1 - after exectuting first card, 2 - after executing 2nd card
    __mapper_args__ = {
        'polymorphic_identity': 'slip'
    }


class PlayerDB(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)

    won = Column(Boolean)  # None - not finished, true/false = yes/no

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("UserDB", back_populates="plays")

    game_id = Column(Integer, ForeignKey("games.id"))
    game = relationship("GameDB", back_populates="players")

    moves = Column(String, default="")

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'player'
    }


class Slip_PlayerDB(PlayerDB):
    committed_move_slip = Column(String)
    position = Column(Integer)
    discarded = Column(String, default="")
    hit = Column(Boolean)
    slip = Column(String)
    cd1 = Column(String)
    cd2 = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'slip_player'
    }


class RPS_PlayerDB(PlayerDB):
    score = Column(Integer, default=0)
    committed_move = Column(Integer)
    __mapper_args__ = {
        'polymorphic_identity': 'rps_player'
    }


class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    date = Column(DateTime)

    sender_id = Column(Integer, ForeignKey("users.id"))
    sender = relationship("UserDB", foreign_keys=sender_id)

    recipient_id = Column(Integer, ForeignKey("users.id"))  # none = public chat
    recipient = relationship("UserDB", foreign_keys=recipient_id)
