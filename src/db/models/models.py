from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from src.db import Base
from datetime import timezone, datetime


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False, default=datetime.now(timezone.utc).timestamp())

    sub_projects = relationship("SubProject", back_populates="project", cascade="all, delete-orphan")


class SubProject(Base):
    __tablename__ = 'sub_projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)

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
