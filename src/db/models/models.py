from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Text, BigInteger, ForeignKey, Enum
from sqlalchemy.orm import relationship
from src.db import Base
from datetime import timezone, datetime


class User(Base, UserMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    stripe_customer_id = Column(String, unique=True)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(BigInteger, nullable=False, default=int(datetime.now(timezone.utc).timestamp() * 1000))
    plan = Column(String(50), default='student')
    stripe_subscription_id = Column(String, nullable=True)
    stripe_subscription_item_id = Column(String, nullable=True)
    stripe_subscription_expires_at = Column(BigInteger, nullable=True)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False, default=datetime.now(timezone.utc).timestamp())
    user = relationship("User", back_populates="projects")
    sub_projects = relationship("SubProject", back_populates="project", cascade="all, delete-orphan")


class SubProject(Base):
    __tablename__ = 'sub_projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    type = Column(Enum("revision", "normal", name="subproject_type"), nullable=False, default="normal")
    title = Column(String(255), nullable=False)
    reviewer_comments = Column(Text, default="")
    description = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False, default=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))
    deadline = Column(BigInteger, nullable=False)

    # add relationship to Project if needed
    project = relationship("Project", back_populates="sub_projects")

    def __str__(self):
        return f"SubProject(id={self.id}, title='{self.title}', description='{self.description}', created_at={self.created_at}, deadline={self.deadline}, type='{self.type}')"


class Milestone(Base):
    __tablename__ = 'milestones'

    id = Column(Integer, primary_key=True)
    sub_project_id = Column(Integer, ForeignKey('sub_projects.id'), nullable=False)
    milestone = Column(Text, nullable=False)
    due_date = Column(String(10), nullable=False)
    notes = Column(Text, default="")
    status = Column(String(50), default="Not Started")

    sub_project = relationship("SubProject", backref="milestones")

    def __str__(self):
        return f"Milestone(id={self.id}, sub_project_id={self.sub_project_id}, milestone='{self.milestone}', due_date='{self.due_date}', status='{self.status}')"

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "milestone": self.milestone,
            "due_date": self.due_date,
            "status": self.status
        }


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(100), unique=True, nullable=False)  # Stripe's unique ID for the event
    event_type = Column(String(100), nullable=False)  # e.g., 'invoice.payment_succeeded'
    received_at = Column(BigInteger, nullable=False, default=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))