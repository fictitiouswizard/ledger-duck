import datetime
import uuid

from fastapi.routing import APIRouter
from sqlmodel import Session, select, func, col
from fastapi import Depends, HTTPException, status, Query
from sqlmodel.sql.expression import Select, SelectOfScalar

from restapi.api.database import create_session
from restapi.api.schemas import Transaction, CreateTransaction, ReadTransaction, CreateAccountTransaction, Account, User, \
    UpdateTransaction
from restapi.api.routers.auth import get_current_active_user

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


def transaction_count_for_account(session: Session, user: User, transaction: Transaction):
    statement = select(func.count(Transaction.id))
    statement = statement.where(Transaction.user_id == user.id)
    statement = statement.where(Transaction.account_id == transaction.account_id)
    transactions_for_account = session.exec(statement).one()
    return transactions_for_account


def get_previous_transaction(session: Session, user: User, transaction: Transaction):
    statement = select(Transaction)
    statement = statement.where(Transaction.user_id == user.id)
    statement = statement.where(Transaction.account_id == transaction.account_id)
    statement = statement.where(Transaction.transaction_date <= transaction.transaction_date)
    statement = statement.where(Transaction.id != transaction.id)
    statement = statement.order_by(col(Transaction.ordinal).desc())
    transactions = session.exec(statement).all()
    if len(transactions) > 0:
        return transactions[0]
    else:
        return None


def update_future_transactions(session: Session, user: User, transaction: Transaction, previous_ordinal: int | None = None):
    if previous_ordinal:
        if transaction.ordinal > previous_ordinal:
            ordinal = previous_ordinal
            statement = select(Transaction)
            statement = statement.where(Transaction.user_id == user.id)
            statement = statement.where(Transaction.account_id == transaction.account_id)
            statement = statement.where(Transaction.ordinal < ordinal)
            statement = statement.order_by(col(Transaction.ordinal).asc())
            transaction = session.exec(statement).first()

    statement = select(Transaction)
    statement = statement.where(Transaction.user_id == user.id)
    statement = statement.where(Transaction.account_id == transaction.account_id)
    # statement = statement.where(Transaction.transaction_date > transaction.transaction_date)
    statement = statement.where(Transaction.ordinal > transaction.ordinal)
    statement = statement.order_by(col(Transaction.ordinal).asc())
    transactions = session.exec(statement).all()

    previous_transaction = None
    for future_transaction in transactions:
        if previous_transaction is None:
            future_transaction.ordinal = transaction.ordinal + 1
            future_transaction.running_balance = transaction.running_balance + future_transaction.amount
        else:
            future_transaction.ordinal = previous_transaction.ordinal + 1
            future_transaction.running_balance = previous_transaction.running_balance + future_transaction.amount
        session.add(future_transaction)
        previous_transaction = future_transaction
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
        "created_date": datetime.datetime.utcnow(),
        "updated_date": datetime.datetime.utcnow(),
        "ordinal": 0,
        "running_balance": transaction.amount,
    }
    transaction = Transaction.from_orm(transaction, update=update_fields)
    # are there any transactions for this account?
    transactions_for_account = transaction_count_for_account(session, user, transaction)

    if transactions_for_account == 0:
        # this is the first transaction for the account
        # just push it in
        transaction.ordinal = 1
        transaction.running_balance = transaction.amount

        session.add(transaction)
        session.commit()
        session.refresh(transaction)

        return transaction
    # are there any transactions for this day?
    previous_transaction = get_previous_transaction(session, user, transaction)
    if previous_transaction:
        transaction.ordinal = previous_transaction.ordinal + 1,
        transaction.running_balance = previous_transaction.running_balance + transaction.amount

        session.add(transaction)
        session.commit()
        session.refresh(transaction)
    else:
        transaction.ordinal = 1
        transaction.running_balance = transaction.amount

        session.add(transaction)
        session.commit()
        session.refresh(transaction)

    # future days?
    update_future_transactions(session, user, transaction)

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
    previous_ordinal = transaction.ordinal
    update_dict = transaction_update.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(transaction, key, value)
    if "transaction_date" in update_dict.keys() or "amount" in update_dict.keys():
        previous_transaction = get_previous_transaction(session, user, transaction)
        if previous_transaction:
            transaction.ordinal = previous_transaction.ordinal + 1,
            transaction.running_balance = previous_transaction.running_balance + transaction.amount

            session.add(transaction)
            session.commit()
            session.refresh(transaction)
        else:
            transaction.ordinal = 1
            transaction.running_balance = transaction.amount

            session.add(transaction)
            session.commit()
            session.refresh(transaction)

        # future days?
        update_future_transactions(session, user, transaction, previous_ordinal)
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
    cmd = cmd.order_by(col(Transaction.ordinal).desc())
    cmd = cmd.offset(offset)
    cmd = cmd.limit(limit)
    transactions = session.exec(cmd).all()
    return transactions


router.include_router(accounts_router)
router.include_router(transactions_router)
