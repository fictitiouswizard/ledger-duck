from fastapi import FastAPI
from routers import accounts, categories, transactions

from database import create_db_and_tables

app = FastAPI(title="Duck Ledger")

app.add_event_handler("startup", create_db_and_tables)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
