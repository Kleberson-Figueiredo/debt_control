from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from debt_control.database import get_session
from debt_control.models import Category, User
from debt_control.schemas import (
    CategoryPublic,
    CategorySchema,
    FilterCategory,
    ListCategories,
    Message,
)
from debt_control.security import get_current_user

router = APIRouter()

T_Session = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]

router = APIRouter(prefix='/category', tags=['category'])


@router.get('/', response_model=ListCategories)
def list_categories(
    session: T_Session,
    user: CurrentUser,
    category_filter: Annotated[FilterCategory, Query()],
):
    query = select(Category).where(Category.user_id == user.id)

    if category_filter.description:
        query = query.filter(
            Category.description.contains(category_filter.description)
        )
    category = session.scalars(
        query.offset(category_filter.offset).limit(category_filter.limit)
    ).all()

    return {'categories': category}


@router.post('/', response_model=CategoryPublic)
def create_category(
    category: CategorySchema, user: CurrentUser, session: T_Session
):
    db_description = session.scalar(
        select(Category).where(
            Category.user_id == user.id,
            Category.description.contains(category.description),
        )
    )

    if db_description:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='category already exists',
        )

    db_category = category.model_dump()
    db = Category(**db_category, user_id=user.id)
    session.add(db)
    session.commit()
    session.refresh(db)

    return db


@router.delete('/{category_id}', response_model=Message)
def delete_category(category_id: int, session: T_Session, user: CurrentUser):
    category = session.scalar(
        select(Category).where(
            Category.user_id == user.id, Category.id == category_id
        )
    )

    if not category:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Category not found.'
        )

    session.delete(category)

    session.commit()

    return {'message': 'Category has been deleted successfully.'}
