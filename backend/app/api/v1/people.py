from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.models import Person
from backend.app.schemas import PersonCreate, PersonRead, PersonUpdate


router = APIRouter(prefix="/people", tags=["people"])


def _get_person_or_404(person_id: int, db: Session) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


@router.get("", response_model=list[PersonRead])
def list_people(q: str | None = None, db: Session = Depends(get_db)) -> list[Person]:
    query = select(Person).order_by(Person.name)
    if q is not None:
        query = query.where(
            or_(
                Person.name.ilike(f"%{q}%"),
                Person.alias.ilike(f"%{q}%"),
                Person.email.ilike(f"%{q}%"),
            )
        )
    return list(db.scalars(query).all())


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)) -> Person:
    person = Person(**payload.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.get("/{person_id}", response_model=PersonRead)
def get_person(person_id: int, db: Session = Depends(get_db)) -> Person:
    return _get_person_or_404(person_id, db)


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(person_id: int, payload: PersonUpdate, db: Session = Depends(get_db)) -> Person:
    person = _get_person_or_404(person_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(person, key, value)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: int, db: Session = Depends(get_db)) -> Response:
    person = _get_person_or_404(person_id, db)
    db.delete(person)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
