from fastapi.routing import APIRouter
from sqlmodel import Session, select
from fastapi import Depends, HTTPException, status, Query

from database import create_session
from schemas import Transaction, CreateTransaction, ReadTransaction, CreateAccountTransaction, Account, User
from routers.auth import get_current_active_user

accounts_router = APIRouter(
    prefix="/accounts/{account_id}/transactions",
    tags=["accounts"],
)

transactions_router = APIRouter(
    prefix="/transactions",
    tags=["transactions"],
)

router = APIRouter()


@accounts_router.get(
    "/",
    response_model=list[ReadTransaction],
)
def get_transactions_for_account(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        account_id: int,
        limit: int = 0,
        offset: int = Query(default=100, lte=100)
):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    cmd = select(Transaction).where(Transaction.account_id == account.id)
    cmd.offset(offset)
    cmd.limit(limit)
    transactions = session.exec(cmd).all()
    return transactions


@accounts_router.post(
    "/",
    response_model=ReadTransaction,
)
def create_transaction_for_account(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        account_id: int,
        transaction: CreateAccountTransaction
):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    transaction_db = Transaction.from_orm(CreateTransaction(**transaction.dict(), account_id=account.id))
    session.add(transaction_db)
    session.commit()
    session.refresh(transaction_db)
    return transaction_db


@transactions_router.get("/", response_model=list[ReadTransaction])
def get_transactions(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        offset: int = 0,
        limit: int = Query(default=100, lte=100),
):
    transactions = session.exec(select(Transaction).offset(offset).limit(limit)).all()
    return transactions


@transactions_router.post("/", response_model=ReadTransaction)
def create_transaction(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        transaction: CreateTransaction,
):
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


@transactions_router.get("/{transaction_id}", response_model=ReadTransaction)
def get_transaction(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        transaction_id: int
):
    transaction = session.get(Transaction, transaction_id)
    if transaction:
        return transaction
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")


router.include_router(accounts_router)
router.include_router(transactions_router)

