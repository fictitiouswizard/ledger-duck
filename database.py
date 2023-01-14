from sqlmodel import create_engine, Session, SQLModel


postgres_url = "postgresql://localhost/duckledger"
engine = create_engine(postgres_url)


def create_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)