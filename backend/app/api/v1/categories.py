from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.models import Category, Transaction, TransactionSplit
from backend.app.schemas import CategoryCreate, CategoryRead, CategoryUpdate


router = APIRouter(prefix="/categories", tags=["categories"])


def _get_category_or_404(category_id: int, db: Session) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def _ensure_unique_name(name: str, db: Session, category_id: int | None = None) -> None:
    query = select(Category).where(func.lower(Category.name) == name.lower())
    existing = db.scalar(query)
    if existing and existing.id != category_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists",
        )


def _validate_parent(parent_id: int | None, db: Session) -> None:
    if parent_id is None:
        return
    if db.get(Category, parent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found")


@router.get("", response_model=list[CategoryRead])
def list_categories(kind: str | None = None, db: Session = Depends(get_db)) -> list[Category]:
    query = select(Category).order_by(Category.sort_order, Category.name)
    if kind is not None:
        query = query.where(Category.kind.in_([kind, "both"]))
    return list(db.scalars(query).all())


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)) -> Category:
    _ensure_unique_name(payload.name, db)
    _validate_parent(payload.parent_id, db)
    category = Category(**payload.model_dump(), is_system=False)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)) -> Category:
    return _get_category_or_404(category_id, db)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
) -> Category:
    category = _get_category_or_404(category_id, db)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data:
        _ensure_unique_name(data["name"], db, category_id=category.id)
    if "parent_id" in data:
        if data["parent_id"] == category.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category cannot be its own parent")
        _validate_parent(data["parent_id"], db)

    for key, value in data.items():
        setattr(category, key, value)

    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> Response:
    category = _get_category_or_404(category_id, db)
    if category.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System categories cannot be deleted",
        )

    db.execute(
        update(Transaction)
        .where(Transaction.category_id == category.id)
        .values(category_id=None)
    )
    db.execute(
        update(TransactionSplit)
        .where(TransactionSplit.category_id == category.id)
        .values(category_id=None)
    )
    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
