from pathlib import Path
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from app.db.model import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def seed_db():
    if not DATABASE_URL:
        print("DATABASE_URL not set in environment.")
        return

    engine = create_engine(DATABASE_URL, future=True)
    seed_file = Path("seeds/seed_v3.sql")

    with engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")

    Base.metadata.create_all(engine)

    if seed_file.exists():
        with engine.begin() as conn:
            raw = conn.connection
            cur = raw.cursor()
            cur.execute(seed_file.read_text())
            cur.close()
        print("✅ Database seeded successfully with v2 schema and data.")
    else:
        print(f"Warning: seed file {seed_file} not found.")


if __name__ == "__main__":
    seed_db()