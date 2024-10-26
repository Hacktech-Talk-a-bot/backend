# app/api/endpoints.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud.operations import (
    create_user, get_user, get_users, update_user, delete_user,
    create_form, get_form, get_forms, update_form, delete_form,
    assign_form_to_user, update_user_form_state, get_user_forms,
    remove_form_from_user
)
from app.schemas.schemas import (
    UserCreate, User, UserUpdate, UserList,
    FormCreate, Form, FormUpdate, FormList,
    UserFormAssign, UserFormUpdate, UserFormResponse
)

router = APIRouter()


# User endpoints
@router.post("/users/", response_model=User, status_code=201)
def create_new_user(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, name=user.name, category=user.category)


@router.get("/users/", response_model=UserList)
def read_users(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        db: Session = Depends(get_db)
):
    users = get_users(db, skip=skip, limit=limit)
    return {"total": len(users), "users": users}


@router.get("/users/{user_id}", response_model=User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.patch("/users/{user_id}", response_model=User)
def update_existing_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = update_user(db, user_id, name=user.name, category=user.category)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/users/{user_id}", status_code=204)
def delete_existing_user(user_id: int, db: Session = Depends(get_db)):
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return None


# Form endpoints
@router.post("/forms/", response_model=Form, status_code=201)
def create_new_form(form: FormCreate, db: Session = Depends(get_db)):
    return create_form(
        db,
        title=form.title,
        description=form.description,
        json_structure=form.json_structure,
        category=form.category
    )


@router.get("/forms/", response_model=FormList)
def read_forms(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        db: Session = Depends(get_db)
):
    forms = get_forms(db, skip=skip, limit=limit)
    return {"total": len(forms), "forms": forms}


@router.get("/forms/{form_id}", response_model=Form)
def read_form(form_id: int, db: Session = Depends(get_db)):
    db_form = get_form(db, form_id)
    if db_form is None:
        raise HTTPException(status_code=404, detail="Form not found")
    return db_form


@router.patch("/forms/{form_id}", response_model=Form)
def update_existing_form(form_id: int, form: FormUpdate, db: Session = Depends(get_db)):
    db_form = update_form(
        db,
        form_id,
        title=form.title,
        description=form.description,
        json_structure=form.json_structure,
        category=form.category,
        state=form.state
    )
    if db_form is None:
        raise HTTPException(status_code=404, detail="Form not found")
    return db_form


@router.delete("/forms/{form_id}", status_code=204)
def delete_existing_form(form_id: int, db: Session = Depends(get_db)):
    success = delete_form(db, form_id)
    if not success:
        raise HTTPException(status_code=404, detail="Form not found")
    return None


# User-Form relationship endpoints
@router.post("/users/{user_id}/forms/{form_id}", status_code=201)
def assign_user_form(
        user_id: int,
        form_id: int,
        assignment: UserFormAssign,
        db: Session = Depends(get_db)
):
    success = assign_form_to_user(
        db,
        user_id=user_id,
        form_id=form_id,
        json_begin=assignment.json_begin
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail="User or form not found, or assignment already exists"
        )
    return {"status": "Form assigned successfully"}


@router.patch("/users/{user_id}/forms/{form_id}", response_model=dict)
def update_user_form(
        user_id: int,
        form_id: int,
        update_data: UserFormUpdate,
        db: Session = Depends(get_db)
):
    success = update_user_form_state(
        db,
        user_id=user_id,
        form_id=form_id,
        state=update_data.state,
        json_response=update_data.json_response
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail="User-form relationship not found"
        )
    return {"status": "Form state updated successfully"}


@router.get("/users/{user_id}/forms/", response_model=List[UserFormResponse])
def get_forms_for_user(user_id: int, db: Session = Depends(get_db)):
    forms = get_user_forms(db, user_id)
    if not forms:
        raise HTTPException(
            status_code=404,
            detail="User not found or has no forms"
        )
    return forms


@router.delete("/users/{user_id}/forms/{form_id}", status_code=204)
def remove_user_form(user_id: int, form_id: int, db: Session = Depends(get_db)):
    success = remove_form_from_user(db, user_id, form_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="User-form relationship not found"
        )
    return None
