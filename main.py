from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import accounts, categories, transactions, auth, bills

from database import create_db_and_tables

app = FastAPI(title="Duck Ledger")

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_event_handler("startup", create_db_and_tables)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(bills.router)


