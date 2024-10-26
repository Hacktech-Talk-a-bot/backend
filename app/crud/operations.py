# app/crud/operations.py
from typing import Optional, List, Dict, Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.database import User, Form, form_user


# User CRUD Operations
def create_user(db: Session, name: str, category: str) -> User:
    db_user = User(name=name, category=category)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def update_user(db: Session, user_id: int, name: Optional[str] = None, category: Optional[str] = None) -> Optional[
    User]:
    db_user = get_user(db, user_id)
    if db_user:
        if name is not None:
            db_user.name = name
        if category is not None:
            db_user.category = category
        db.commit()
        db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False


# Form CRUD Operations
def create_form(db: Session, title: str, description: str, json_structure: Dict, category: str) -> Form:
    db_form = Form(
        title=title,
        description=description,
        json_structure=json_structure,
        category=category,
        state="draft"
    )
    db.add(db_form)
    db.commit()
    db.refresh(db_form)
    return db_form


def get_form(db: Session, form_id: int) -> Optional[Form]:
    return db.query(Form).filter(Form.id == form_id).first()


def get_forms(db: Session, skip: int = 0, limit: int = 100) -> List[Form]:
    return db.query(Form).offset(skip).limit(limit).all()


def update_form(
        db: Session,
        form_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        json_structure: Optional[Dict] = None,
        category: Optional[str] = None,
        state: Optional[str] = None
) -> Optional[Form]:
    db_form = get_form(db, form_id)
    if db_form:
        if title is not None:
            db_form.title = title
        if description is not None:
            db_form.description = description
        if json_structure is not None:
            db_form.json_structure = json_structure
        if category is not None:
            db_form.category = category
        if state is not None and state in ["draft", "started", "finished"]:
            db_form.state = state
        db.commit()
        db.refresh(db_form)
    return db_form


def delete_form(db: Session, form_id: int) -> bool:
    db_form = get_form(db, form_id)
    if db_form:
        db.delete(db_form)
        db.commit()
        return True
    return False


# User-Form Relationship CRUD Operations
def assign_form_to_user(
        db: Session,
        user_id: int,
        form_id: int,
        json_begin: Optional[Dict] = None,
) -> bool:
    db_user = get_user(db, user_id)
    db_form = get_form(db, form_id)

    if db_user and db_form:
        # Check if relationship already exists
        stmt = form_user.select().where(
            and_(
                form_user.c.user_id == user_id,
                form_user.c.form_id == form_id
            )
        )
        existing = db.execute(stmt).first()

        if not existing:
            # Insert new relationship
            stmt = form_user.insert().values(
                user_id=user_id,
                form_id=form_id,
                state="initial",
                json_begin=json_begin,
                json_response=None
            )
            db.execute(stmt)
            db.commit()
            return True
    return False


def update_user_form_state(
        db: Session,
        user_id: int,
        form_id: int,
        state: str,
        json_response: Optional[Dict] = None
) -> bool:
    if state not in ["initial", "in_progress", "finished", "analyzed"]:
        return False

    stmt = form_user.update().where(
        and_(
            form_user.c.user_id == user_id,
            form_user.c.form_id == form_id
        )
    ).values(
        state=state,
        json_response=json_response if json_response is not None else form_user.c.json_response
    )

    result = db.execute(stmt)
    db.commit()
    return result.rowcount > 0


def get_user_forms(db: Session, user_id: int) -> List[Dict[str, Any]]:
    user = get_user(db, user_id)
    if not user:
        return []

    # Query to get all forms and their relationship data for a user
    stmt = db.query(
        Form,
        form_user.c.state,
        form_user.c.json_begin,
        form_user.c.json_response
    ).join(
        form_user
    ).filter(
        form_user.c.user_id == user_id
    )

    results = []
    for form, state, json_begin, json_response in stmt:
        results.append({
            "form_id": form.id,
            "title": form.title,
            "description": form.description,
            "category": form.category,
            "form_state": form.state,
            "user_form_state": state,
            "json_begin": json_begin,
            "json_response": json_response
        })

    return results


def remove_form_from_user(db: Session, user_id: int, form_id: int) -> bool:
    stmt = form_user.delete().where(
        and_(
            form_user.c.user_id == user_id,
            form_user.c.form_id == form_id
        )
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount > 0
