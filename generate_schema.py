from sqlalchemy import create_engine, MetaData
from sqlalchemy.schema import CreateTable
from src.db.models import Base, User, Project, SubProject, Milestone, StripeWebhookEvent, UsageLog

# Replace this with your actual database URL (can be SQLite for offline generation)
DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(DATABASE_URL)
metadata = Base.metadata

# Create all tables in memory
metadata.create_all(engine)

# Output SQL to file
with open("schema.sql", "w") as f:
    for table in metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(engine)).strip() + ";\n\n"
        f.write(ddl)

print("✅ schema.sql has been generated.")