from sqlmodel import create_engine, Session, SQLModel
import os

try:
    postgres_url = os.environ["postgres_url"]
except KeyError:
    postgres_url = "postgresql://localhost/duckledger"
engine = create_engine(postgres_url)


def create_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)