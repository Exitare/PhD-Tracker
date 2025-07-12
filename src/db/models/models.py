from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Text, BigInteger, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.orm import relationship, Mapped
from src.db import Base
from datetime import timezone, datetime
import json


class User(Base, UserMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    stripe_customer_id: Mapped[str] = Column(String(100), unique=True)
    email: Mapped[str] = Column(String(150), unique=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(BigInteger, nullable=True, default=None)
    first_name: Mapped[str] = Column(String(150), nullable=True)
    last_name: Mapped[str] = Column(String(150), nullable=True)
    last_sign_in: Mapped[int] = Column(BigInteger, nullable=False, default=int(datetime.now(timezone.utc).timestamp() * 1000))
    organization_name: Mapped[str] = Column(String(150), nullable=True)
    managed_by = Column(Integer, ForeignKey('users.id'), nullable=True)  # For user management hierarchy
    managed_by_stripe_id: Mapped[str] = Column(String(100), nullable=True)  # Stripe ID of the manager if applicable
    pending_email: Mapped[str] = Column(String(150), nullable=True)
    password_hash: Mapped[str] = Column(String(200), nullable=False)
    created_at = Column(BigInteger, nullable=False, default=int(datetime.now(timezone.utc).timestamp() * 1000))
    active = Column(Boolean, default=True, nullable=False)  # Whether the user is active or not
    deactivated_at = Column(BigInteger, nullable=True, default=None)
    plan: Mapped[str] = Column(String(50), default='student')
    stripe_subscription_id = Column(String(100), nullable=True)
    stripe_subscription_item_ids = Column(String(100), nullable=True)
    stripe_subscription_expires_at = Column(BigInteger, nullable=True)
    stripe_subscription_canceled = Column(Boolean, default=False, nullable=False) # Whether the subscription is canceled or not
    role = Column(Enum("user", "manager", "admin", name="user_role"), default="user", nullable=False)
    access_code = Column(String(100), nullable=True)  # For manager accounts to let users join their team

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")

    def __str__(self):
        return (
            f"User(id={self.id}, email='{self.email}', created_at={self.created_at}, plan='{self.plan}', stripe_customer_id='{self.stripe_customer_id}',"
            f" email_verified={self.email_verified}, email_verified_at={self.email_verified_at}, pending_email='{self.pending_email}',"
            f" password_hash='{self.password_hash}', stripe_subscription_id='{self.stripe_subscription_id}',"
            f" stripe_subscription_item_ids='{self.stripe_subscription_item_ids}',"
            f" stripe_subscription_expires_at={self.stripe_subscription_expires_at},"
            f" role='{self.role}', first_name='{self.first_name}', last_name='{self.last_name}', organization='{self.organization_name},"
            f" managed_by={self.managed_by}, managed_by_stripe_id={self.managed_by_stripe_id}, access_code='{self.access_code}')")


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    type = Column(Enum("paper", "poster", "dissertation", name="project_type"), nullable=False, default="paper")
    selected_venue = Column(String(255), nullable=True)
    selected_venue_url = Column(String(255), nullable=True)
    journal_recommendations = Column(JSON, nullable=True)
    venue_requirements = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False, default=datetime.now(timezone.utc).timestamp())
    user = relationship("User", back_populates="projects")
    sub_projects = relationship("SubProject", back_populates="project", cascade="all, delete-orphan")

    @property
    def venue_requirements_data(self):
        if not self.venue_requirements:
            return {}
        try:
            if isinstance(self.venue_requirements, str):
                return json.loads(self.venue_requirements)
            return self.venue_requirements  # just in case it's already a dict
        except Exception as e:
            print(f"Error parsing venue requirements for project {self.id}: {e}")
            return {}

    @venue_requirements_data.setter
    def venue_requirements_data(self, value: dict):
        if isinstance(value, dict):
            self.venue_requirements = json.dumps(value)
        else:
            raise ValueError("venue_requirements_data must be a dictionary")

    def __str__(self):
        return (
            f"Project(id={self.id}, user_id={self.user_id}, title='{self.title}', description='{self.description}', "
            f"type='{self.type}', selected_venue='{self.selected_venue}', selected_venue_url='{self.selected_venue_url}', "
            f"created_at={self.created_at}, journal_recommendations={self.journal_recommendations}, venue_requirements='{self.venue_requirements}')"
        )


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


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_name = Column(String(100), nullable=False)  # e.g., 'tokenrequests'
    used_tokens = Column(Integer, nullable=False, default=0)  # Number of credits used for this event
    created_at = Column(BigInteger, nullable=False, default=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))

    user = relationship("User", back_populates="usage_logs")

    def __str__(self):
        return f"UsageLog(id={self.id}, user_id={self.user_id}, event_name='{self.event_name}', created_at={self.created_at})"
