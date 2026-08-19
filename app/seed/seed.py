from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.db.model import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, future=True)

seed_file = Path("seeds/seed_v2.sql")

from app.db.model import Base

with engine.begin() as conn:
    conn.exec_driver_sql("DROP SCHEMA public CASCADE")
    conn.exec_driver_sql("CREATE SCHEMA public")

Base.metadata.create_all(engine)

with engine.begin() as conn:
    raw = conn.connection
    cur = raw.cursor()
    cur.execute(seed_file.read_text())
    cur.close()

print("✅ Database seeded successfully.")