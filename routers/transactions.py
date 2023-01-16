import datetime
import uuid

from fastapi.routing import APIRouter
from sqlmodel import Session, select, func, col
from fastapi import Depends, HTTPException, status, Query
from sqlmodel.sql.expression import Select, SelectOfScalar

from database import create_session, engine
from schemas import Transaction, CreateTransaction, ReadTransaction, CreateAccountTransaction, Account, User, \
    UpdateTransaction
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


def sort_transactions_statement(statement: Select | SelectOfScalar):
    statement = statement.order_by(col(Transaction.transaction_date).asc())
    statement = statement.order_by(col(Transaction.amount).asc())
    statement = statement.order_by(col(Transaction.running_balance).desc())
    return statement


def get_running_balance(session: Session, transaction: Transaction, user: User):
    cmd = select(Transaction).where(Transaction.user == user)
    cmd = cmd.where(Transaction.account_id == transaction.account_id)
    cmd = cmd.where(Transaction.transaction_date <= transaction.transaction_date)
    cmd = cmd.where(Transaction.amount > transaction.amount)
    cmd = sort_transactions_statement(cmd)
    older_transaction = session.exec(cmd).first()
    if older_transaction:
        transaction.running_balance = older_transaction.running_balance + transaction.amount
    else:
        transaction.running_balance = transaction.amount


def update_running_balance(session: Session, transaction: Transaction, user: User):
    cmd = select(Transaction).where(Transaction.user == user)
    cmd = cmd.where(Transaction.account_id == transaction.account_id)
    cmd = cmd.where(Transaction.transaction_date >= transaction.transaction_date)
    cmd = cmd.where(Transaction.amount <= transaction.amount)
    cmd = cmd.where(Transaction.id != transaction.id)
    cmd = sort_transactions_statement(cmd)
    newer_transactions = session.exec(cmd)

    if newer_transactions:
        previous_transaction = None
        for newer_transaction in newer_transactions:
            if previous_transaction is None:
                newer_transaction.running_balance = transaction.running_balance + newer_transaction.amount
                session.add(newer_transaction)
                previous_transaction = newer_transaction
                continue
            newer_transaction.running_balance = previous_transaction.running_balance + newer_transaction.amount
            session.add(newer_transaction)
            previous_transaction = newer_transaction
        session.commit()


@transactions_router.post("/", response_model=ReadTransaction)
def create_transaction(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        transaction: CreateTransaction,
):
    update_fields = {
        "user_id": user.id,
        "running_balance": 0.00
    }
    transaction = Transaction.from_orm(transaction, update=update_fields)

    get_running_balance(session=session, transaction=transaction, user=user)

    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    update_running_balance(session=session, transaction=transaction, user=user)

    return transaction


@transactions_router.get("/{transaction_id}", response_model=ReadTransaction)
def get_transaction(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        transaction_id: uuid.UUID
):
    cmd = select(Transaction).where(Transaction.id == transaction_id)
    cmd = cmd.where(Transaction.user_id == user.id)
    transaction = session.exec(cmd).first()
    if transaction:
        return transaction
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")


@transactions_router.patch("/{transaction_id}", response_model=ReadTransaction)
def update_transaction(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        transaction_id: uuid.UUID,
        transaction_update: UpdateTransaction,
):
    cmd = select(Transaction).where(Transaction.user == user)
    cmd = cmd.where(Transaction.id == transaction_id)
    transaction = session.exec(cmd).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    update_dict = transaction_update.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(transaction, key, value)
    if "transaction_date" in update_dict.keys() or "amount" in update_dict.keys():
        get_running_balance(session=session, transaction=transaction, user=user)

        session.add(transaction)
        session.commit()
        session.refresh(transaction)

        update_running_balance(session=session, transaction=transaction, user=user)
    else:
        session.add(transaction)
        session.commit()
        session.refresh(transaction)

    return transaction


@transactions_router.get("/", response_model=list[ReadTransaction])
def get_transactions(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        offset: int = 0,
        limit: int = Query(default=100, lte=100),
):
    cmd = select(Transaction)
    cmd = cmd.where(Transaction.user_id == user.id)
    cmd = sort_transactions_statement(cmd)
    cmd = cmd.offset(offset)
    cmd = cmd.limit(limit)
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
        account_id: uuid.UUID,
        transaction: CreateAccountTransaction
):
    cmd = select(Account).where(Account.user == user)
    cmd = cmd.where(Account.id == account_id)
    account = session.exec(cmd).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    transaction = CreateTransaction(**transaction.dict(), account_id=account.id)
    transaction_db = create_transaction(transaction=transaction, session=session, user=user)
    return transaction_db


@accounts_router.get(
    "/",
    response_model=list[ReadTransaction],
)
def get_transactions_for_account(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        account_id: uuid.UUID,
        offset: int = 0,
        limit: int = Query(default=100, lte=100)
):
    cmd = select(Transaction).where(Transaction.user_id == user.id)
    cmd = cmd.where(Transaction.account_id == account_id)
    cmd = sort_transactions_statement(cmd)
    cmd = cmd.offset(offset)
    cmd = cmd.limit(limit)
    transactions = session.exec(cmd).all()
    return transactions


router.include_router(accounts_router)
router.include_router(transactions_router)
