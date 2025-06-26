import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

ENV = os.environ.get("FLASK_ENV", "development")

if ENV == "production":
    # MySQL example via SSH tunnel (you handle tunnel externally or via Paramiko/etc)
    DB_URL = os.environ.get("DATABASE_URL")  # e.g., "mysql+pymysql://user:pass@127.0.0.1:3307/dbname"
else:
    DB_URL = "sqlite:///milestones.db"

engine = create_engine(DB_URL, echo=(ENV != "production"))
db_session = scoped_session(sessionmaker(bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    import src.models  # Ensure models are registered
    Base.metadata.create_all(bind=engine)