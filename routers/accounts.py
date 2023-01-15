from fastapi.routing import APIRouter
from sqlmodel import Session, select
from fastapi import Depends, status, HTTPException
from schemas import Account, ReadAccount, CreateAccount, User
from database import create_session
from routers.auth import get_current_active_user


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=list[ReadAccount])
def get_accounts(
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user)
):
    accounts = session.exec(select(Account)).all()
    return accounts


@router.get("/{account_id}",
            response_model=ReadAccount,
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "Account not found",
                    "content": {
                        "application/json": {
                            "example": {"detail": "Account not found"}
                        }
                    }
                }
            })
def get_account(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        account_id: int):
    account = session.get(Account, account_id)
    if account:
        return account
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")


@router.post("/", response_model=ReadAccount)
def create_account(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        account: CreateAccount):
    session.add(account)
    session.commit()
    session.refresh(account)
    return account
