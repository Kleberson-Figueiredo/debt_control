from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from debt_control.database import get_session
from debt_control.models import Debt, User
from debt_control.schemas import (
    FilterDebt,
    Message,
    DebtList,
    DebtPublic,
    DebtSchema,
    DebtUpdate
)
from debt_control.security import get_current_user

router = APIRouter()

T_Session = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]

router = APIRouter(prefix='/debt', tags=['debt'])


@router.get('/', response_model=DebtList)
def list_debt(
    session: T_Session,
    user: CurrentUser,
    todo_filter: Annotated[FilterDebt, Query()],
):
    query = select(Debt).where(Debt.user_id == user.id)

    if todo_filter.description:
        query = query.filter(
            Debt.description.contains(todo_filter.description)
        )
        
    if todo_filter.state:
        query = query.filter(Debt.state == todo_filter.state)

    debt = session.scalars(
        query.offset(todo_filter.offset).limit(todo_filter.limit)
    ).all()

    return {'debt': debt}


@router.post('/', response_model=DebtPublic)
def create_debt(todo: DebtSchema, user: CurrentUser, session: T_Session):
    db_todo = Debt(
        description=todo.description,
        value=todo.value,
        plots=todo.plots,
        duedate=todo.duedate,
        state=todo.state,
        user_id=user.id,
    )
    session.add(db_todo)
    session.commit()
    session.refresh(db_todo)

    return db_todo


@router.patch('/{todo_id}', response_model=DebtPublic)
def path_debt(
    debt_id: int, session: T_Session, user: CurrentUser, todo: DebtUpdate
):
    db_debt = session.scalar(
        select(Debt).where(Debt.user_id == user.id, Debt.id == debt_id)
    )

    if not db_debt:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Debt not found'
        )

    for key, value in todo.model_dump(exclude_unset=True).items():
        setattr(db_debt, key, value)

    session.add(db_debt)
    session.commit()
    session.refresh(db_debt)

    return db_debt


@router.delete('/{todo_id}', response_model=Message)
def delete_debt(todo_id: int, session: T_Session, user: CurrentUser):
    todo = session.scalar(
        select(Debt).where(Debt.user_id == user.id, Debt.id == todo_id)
    )

    if not todo:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Task not found.'
        )

    session.delete(todo)
    session.commit()

    return {'message': 'Task has been deleted successfully.'}
