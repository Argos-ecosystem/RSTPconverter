from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  (ensures models are registered)

    Base.metadata.create_all(bind=engine)
    if "response_body" not in {c["name"] for c in inspect(engine).get_columns("send_logs")}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE send_logs ADD COLUMN response_body TEXT"))
