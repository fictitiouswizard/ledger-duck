import uuid

from fastapi.routing import APIRouter
from sqlmodel import Session, select, col
from fastapi import Depends, status, HTTPException, Query
from restapi.api.schemas import Bill, User, ReadBill, CreateBill, UpdateBill
from restapi.api.database import create_session
from restapi.api.routers.auth import get_current_active_user


router = APIRouter(prefix="/bills", tags=["bills"])


@router.get("/", response_model=list[ReadBill])
def get_bills(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        offset: int = 0,
        limit: int = Query(default=100, lte=100),
        name: str | None = Query(default=None),
        active: bool | None = Query(default=None),
):
    cmd = select(Bill).where(Bill.user_id == user.id)
    if name:
        cmd.where(col(Bill.name).contains(name))
    if active:
        cmd.where(Bill.active == active)
    else:
        cmd.where(Bill.active == True)
    cmd = cmd.offset(offset)
    cmd = cmd.limit(limit)
    cmd = cmd.order_by(Bill.due_date)
    bills = session.exec(cmd).all()
    return bills


@router.post("/", response_model=ReadBill)
def create_bill(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        bill: CreateBill,
):
    db_bill = Bill.from_orm(bill, update={"user_id": user.id})
    session.add(db_bill)
    session.commit()
    session.refresh(db_bill)
    return db_bill


@router.get("/{bill_id}", response_model=ReadBill)
def get_bill(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        bill_id: uuid.UUID
):
    cmd = select(Bill).where(Bill.user == user)
    cmd = cmd.where(Bill.id == bill_id)
    bill = session.exec(cmd).first()
    if bill:
        return bill
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")


@router.patch("/{bill_id}", response_model=ReadBill)
def update_bill(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        bill_id: uuid.UUID,
        bill_update: UpdateBill,
):
    cmd = select(Bill).where(Bill.user == user)
    cmd = cmd.where(Bill.id == bill_id)
    bill = session.exec(cmd).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    update_dict = bill_update.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(bill, key, value)
    session.add(bill)
    session.commit()
    session.refresh(bill)
    return bill











