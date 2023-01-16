import datetime
import uuid

from fastapi.routing import APIRouter
from sqlmodel import Session, select, func, col
from fastapi import Depends, HTTPException, status, Query

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
    try:
        transaction = Transaction.from_orm(transaction, update=update_fields)
    except Exception as e:
        print(e)
        raise(e)
    with Session(engine) as another_session:
        cmd = select(Transaction).where(Transaction.user == user)
        cmd = cmd.where(Transaction.account_id == transaction.account_id)
        cmd = cmd.where(Transaction.transaction_date >= transaction.transaction_date)
        cmd = cmd.order_by(col(Transaction.transaction_date).asc())
        cmd = cmd.order_by(col(Transaction.amount).desc())
        transactions = another_session.exec(cmd).all()

        if transactions:
            previous_transaction = None
            location_found = False
            for db_transaction in transactions:
                if db_transaction.transaction_date >= transaction.transaction_date and \
                        db_transaction.amount <= transaction.amount:
                    # this is where the tranaction goes
                    if not location_found:
                        if previous_transaction:
                            transaction.running_balance = previous_transaction.running_balance + transaction.amount
                            previous_transaction = transaction
                            continue
                        else:
                            # get the transaction from the previous day
                            delta = datetime.timedelta(days=1)
                            with Session(engine) as different_session:
                                cmd = select(Transaction).where(Transaction.user == user)
                                cmd = cmd.where(Transaction.account_id == transaction.account_id)
                                cmd = cmd.where(Transaction.transaction_date >= (transaction.transaction_date - delta))
                                cmd = cmd.order_by(col(Transaction.transaction_date).asc())
                                cmd = cmd.order_by(col(Transaction.amount).desc())
                                previous_day_transaction = different_session.exec(cmd).first()
                                previous_date_running_balance = previous_day_transaction.running_balance
                            transaction.running_balance = previous_date_running_balance + transaction.amount
                    else:
                        db_transaction.running_balance = previous_transaction.running_balance + db_transaction.amount
                        another_session.add(db_transaction)
                        previous_transaction = db_transaction
                else:
                    if previous_transaction is None:
                        if len(transactions) == 1:
                            transaction.running_balance = db_transaction.running_balance + transaction.amount
                            continue
                        else:
                            previous_transaction = db_transaction
                            continue
                    db_transaction.running_balance = previous_transaction.running_balance + db_transaction.amount
                    another_session.add(db_transaction)
                    previous_transaction = db_transaction
            another_session.commit()
        else:
            # there are no transactions newer than this one
            # get the previous transaction and update the running balance
            delta = datetime.timedelta(days=1)
            cmd = select(Transaction).where(Transaction.user == user)
            cmd = cmd.where(Transaction.account_id == transaction.account_id)
            cmd = cmd.where(Transaction.transaction_date == (transaction.transaction_date - delta))
            cmd = cmd.order_by(col(Transaction.transaction_date).asc())
            cmd = cmd.order_by(col(Transaction.amount).desc())
            previous_transaction = session.exec(cmd).first()
            if previous_transaction:
                transaction.running_balance = previous_transaction.running_balance + transaction.amount
            else:
                transaction.running_balance = transaction.amount

        session.add(transaction)
        session.commit()
        session.refresh(transaction)
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
    cmd = cmd.order_by(col(Transaction.transaction_date).asc())
    cmd = cmd.order_by(col(Transaction.amount).desc())
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
        limit: int = 0,
        offset: int = Query(default=100, lte=100)
):
    cmd = select(Transaction).where(Transaction.user_id == user.id)
    cmd = cmd.where(Transaction.account_id == account_id)
    cmd = cmd.order_by(col(Transaction.transaction_date).asc())
    cmd = cmd.order_by(col(Transaction.amount).desc())
    cmd = cmd.offset(offset)
    cmd = cmd.limit(limit)
    transactions = session.exec(cmd).all()
    return transactions


router.include_router(accounts_router)
router.include_router(transactions_router)
