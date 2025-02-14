from http import HTTPStatus
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from debt_control.database import get_session
from debt_control.models import Debt, User
from debt_control.schemas import (
    DebtDashboard,
    DebtList,
    DebtPublic,
    DebtSchema,
    DebtUpdate,
    FilterDashboard,
    FilterDebt,
    Message,
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
    debt_filter: Annotated[FilterDebt, Query()],
):
    query = select(Debt).where(Debt.user_id == user.id)

    if debt_filter.description:
        query = query.filter(
            Debt.description.contains(debt_filter.description)
        )

    if debt_filter.state:
        query = query.filter(Debt.state == debt_filter.state)

    if debt_filter.start_duedate:
        query = query.filter(Debt.duedate >= debt_filter.start_duedate)

    if debt_filter.end_duedate:
        query = query.filter(Debt.duedate <= debt_filter.end_duedate)

    debt = session.scalars(
        query.offset(debt_filter.offset).limit(debt_filter.limit)
    ).all()

    return {'debt': debt}


@router.post('/', response_model=DebtPublic)
def create_debt(debt: DebtSchema, user: CurrentUser, session: T_Session):
    if isinstance(debt.plots, str):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Value invalid plots: {debt.plots}.',
        )

    db_description = session.scalar(
        select(Debt).where(
            Debt.user_id == user.id,
            Debt.description.contains(debt.description),
            extract('month', Debt.duedate) == debt.duedate.month,
            extract('year', Debt.duedate) == debt.duedate.year,
        )
    )

    if db_description:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Debt: {debt.description}'
            + ' already exists for this month',
        )

    plots_count = debt.plots
    date = debt.duedate

    debt_dict = debt.model_dump()
    debt_dict.pop('plots', None)

    if plots_count > 1:
        debt_dict.pop('duedate', None)

        for count in range(1, plots_count + 1):
            db_todo = Debt(
                **debt_dict,
                plots=f'{count}|{plots_count}',
                duedate=date,
                user_id=user.id,
            )
            date += relativedelta(months=1)
            session.add(db_todo)

        session.commit()
        session.refresh(db_todo)

        return db_todo

    db_debt = Debt(**debt_dict, plots='1|1', user_id=user.id)

    session.add(db_debt)
    session.commit()
    session.refresh(db_debt)

    return db_debt


@router.patch('/{debt_id}', response_model=DebtPublic)
def path_debt(
    debt_id: int, session: T_Session, user: CurrentUser, debt: DebtUpdate
):
    db_debt = session.scalar(
        select(Debt).where(Debt.user_id == user.id, Debt.id == debt_id)
    )

    if not db_debt:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Debt not found'
        )

    for key, value in debt.model_dump(exclude_unset=True).items():
        setattr(db_debt, key, value)

    session.add(db_debt)
    session.commit()
    session.refresh(db_debt)

    return db_debt


@router.delete('/{debt_id}', response_model=Message)
def delete_debt(debt_id: int, session: T_Session, user: CurrentUser):
    debt = session.scalar(
        select(Debt).where(Debt.user_id == user.id, Debt.id == debt_id)
    )

    if not debt:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Debt not found.'
        )

    session.delete(debt)
    session.commit()

    return {'message': 'Debt has been deleted successfully.'}


@router.get('/dashboard', response_model=DebtDashboard)
def dashboard_debt(
    session: T_Session,
    user: CurrentUser,
    debt_filter: Annotated[FilterDashboard, Query()],
):
    query = select(Debt).where(Debt.user_id == user.id)

    if debt_filter.start_date:
        query = query.filter(Debt.duedate >= debt_filter.start_date)

    if debt_filter.end_date:
        query = query.filter(Debt.duedate <= debt_filter.end_date)

    debt = session.scalars(
        query.offset(debt_filter.offset).limit(debt_filter.limit)
    ).all()

    return DebtDashboard.from_debts(debt)
