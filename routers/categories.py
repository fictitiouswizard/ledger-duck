from fastapi.routing import APIRouter
from sqlmodel import Session, select
from database import create_session
from fastapi import Depends, HTTPException, status

from schemas import Category, CreateCategory, ReadCategory


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[ReadCategory])
def get_categories(session: Session = Depends(create_session)):
    categories = session.exec(select(Category)).all()
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
def get_category(*, session: Session = Depends(create_session), category_id: int):
    category = session.get(Category, category_id)
    if category:
        return category
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


@router.post("/", response_model=ReadCategory)
def create_category(*, session: Session = Depends(create_session), category: CreateCategory):
    session.add(category)
    session.commit()
    session.refresh(category)
    return category
