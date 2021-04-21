from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from database import Base


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String)
    avatar = Column(String)

    # messagesSent = relationship("MessageDB", back_populates="sender")
    # messagesReceived = relationship("MessageDB")


class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    date = Column(DateTime)

    sender_id = Column(Integer, ForeignKey("users.id"))
    sender = relationship("UserDB", foreign_keys=sender_id)

    recipient_id = Column(Integer, ForeignKey("users.id"))
    recipient = relationship("UserDB", foreign_keys=recipient_id)
