import uuid

from fastapi.routing import APIRouter
from sqlmodel import Session, select, col
from api.database import create_session
from fastapi import Depends, HTTPException, status, Query

from api.schemas import Category, CreateCategory, ReadCategory, User, UpdateCategory
from api.routers.auth import get_current_active_user


router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=ReadCategory)
def create_category(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        category: CreateCategory
):
    category_db = Category.from_orm(category, update={"user_id": user.id})
    session.add(category_db)
    session.commit()
    session.refresh(category_db)
    return category_db


@router.get("/", response_model=list[ReadCategory])
def get_categories(
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        offset: int = 0,
        limit: int = Query(default=100, lte=100),
        active: bool | None = Query(default=None),
        name: str | None = Query(default=None)
):
    cmd = select(Category).where(Category.user_id == user.id)
    cmd.offset(offset)
    cmd.limit(limit)
    if active:
        cmd.where(Category.active == active)
    else:
        cmd.where(Category.active is True)
    if name:
        cmd.where(col(Category.name).contains(name))
    categories = session.exec(cmd).all()
    return categories


@router.get("/{category_id}",
            response_model=ReadCategory,
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "Category not found",
                    "content": {
                        "application/json": {
                            "example": {"detail": "Category not found"}
                        }
                    }
                }
            })
def get_category(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        category_id: uuid.UUID
):
    cmd = select(Category).where(Category.user_id == user.id).where(Category.id == category_id)
    category = session.exec(cmd).first()
    if category:
        return category
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


@router.patch("/{category_id}", response_model=ReadCategory)
def update_category(
    *,
    session: Session = Depends(create_session),
    user: User = Depends(get_current_active_user),
    category_id: uuid.UUID,
    category_update: UpdateCategory
):
    cmd = select(Category).where(Category.user == user)
    cmd = cmd.where(Category.id == category_id)
    category = session.exec(cmd).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    update_dict = category_update.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(category, key, value)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category
