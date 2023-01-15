from fastapi.routing import APIRouter
from sqlmodel import Session, select
from database import create_session
from fastapi import Depends, HTTPException, status, Query

from schemas import Category, CreateCategory, ReadCategory, User
from routers.auth import get_current_active_user


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[ReadCategory])
def get_categories(
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        offset: int = 0,
        limit: int = Query(default=100, lte=100)
):
    cmd = select(Category).where(Category.user_id == user.id)
    cmd.offset(offset)
    cmd.limit(limit)
    categories = session.exec(select(cmd)).all()
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
        category_id: int
):
    cmd = select(Category).where(Category.user_id == user.id).where(Category.id == category_id)
    category = session.exec(cmd).first()
    if category:
        return category
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


@router.post("/", response_model=ReadCategory)
def create_category(
        *,
        session: Session = Depends(create_session),
        user: User = Depends(get_current_active_user),
        category: CreateCategory
):
    session.add(category)
    session.commit()
    session.refresh(category)
    return category
