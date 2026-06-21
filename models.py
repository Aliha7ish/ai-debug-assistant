from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    review_sessions = relationship(
        "ReviewSession",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ReviewSession.id.desc()",
    )


class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    language = Column(String, nullable=False)
    issue_description = Column(Text, nullable=False)

    ai_category = Column(String, nullable=True)
    ai_difficulty = Column(String, nullable=True)
    ai_recommendation = Column(Text, nullable=True)
    ai_status = Column(String, nullable=False, default="PENDING")  # SUCCESS | FAILED | PENDING
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="review_sessions")
