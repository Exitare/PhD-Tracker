from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
import os
import logging

logger = logging.getLogger(__name__)

db_session = None
Base = declarative_base()

def get_db_session():
    global db_session
    if db_session is None:
        raise RuntimeError("Database session not initialized. Call init_db() first.")
    return db_session

def init_db(mode: str):
    if mode == "dev":
        db_url = "sqlite:///milestones.db"
    else:
        # Read individual environment variables
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "3306")  # default for MySQL
        db_name = os.environ.get("DB_NAME")

        # Assemble DB URL
        db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        # Optional: raise if any critical variable is missing
        if not all([db_user, db_password, db_host, db_port, db_name]):
            raise ValueError("Missing one or more required DB environment variables.")

    engine = create_engine(db_url)
    global db_session
    logger.info('[Flask] Engine created with URL: %s', db_url)
    db_session = scoped_session(sessionmaker(bind=engine))
    Base.query = db_session.query_property()

    if mode == "dev":
        Base.metadata.create_all(engine)  # Only run in dev!
