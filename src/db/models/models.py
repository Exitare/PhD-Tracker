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

    # add relationship to Project if needed
    project = relationship("Project", back_populates="sub_projects")

    def __str__(self):
        return f"SubProject(id={self.id}, title='{self.title}', description='{self.description}', created_at={self.created_at})"


class Milestone(Base):
    __tablename__ = 'milestones'

    id = Column(Integer, primary_key=True)
    sub_project_id = Column(Integer, ForeignKey('sub_projects.id'), nullable=False)
    milestone = Column(Text)
    due_date = Column(String(10))  # Or Date if using date objects
    notes = Column(Text, default="")
    status = Column(String(50), default="Not Started")

    sub_project = relationship("SubProject", backref="milestones")
