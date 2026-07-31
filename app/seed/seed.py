from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.db.model import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, future=True)

seed_file = "seeds/seed.sql"

from app.db.model import Base

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

with engine.begin() as conn:
    raw = conn.connection
    cur = raw.cursor()
    cur.execute(seed_file.read_text())
    cur.close()

print("✅ Database seeded successfully.")