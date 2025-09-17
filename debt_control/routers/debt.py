from datetime import datetime
from http import HTTPStatus
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from debt_control.database import get_session
from debt_control.models import (
    Category,
    Debt,
    DebtInstallment,
    DebtState,
    User,
)
from debt_control.schemas import (
    DebtCategory,
    DebtDashboard,
    DebtInstallmentsList,
    DebtList,
    DebtPublic,
    FilterDashboard,
    FilterDebt,
    FilterDebtInstallments,
    Message,
    PaidInstallments,
    PayInstallentsSchema,
)
from debt_control.security import get_current_user
from debt_control.utils.firebase import send_notification

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
    DebtInstallment.update_overdue(session)

    Debt.update_overdue_debts(session)

    query = select(Debt).where(Debt.user_id == user.id)

    if debt_filter.description:
        query = query.filter(
            Debt.description.contains(debt_filter.description)
        )

    if debt_filter.state:
        query = query.filter(Debt.state == debt_filter.state)

    debts = session.scalars(
        query.offset(debt_filter.offset).limit(debt_filter.limit)
    ).all()

    debts_public = []
    for debt in debts:
        pay = len(
            session.scalars(
                select(DebtInstallment).where(
                    DebtInstallment.debt_id == debt.id,
                    DebtInstallment.state == 'pay',
                )
            ).all()
        )

        category = session.scalar(
            select(Category).where(Category.id == Debt.category_id)
        )

        debt_dict = debt.__dict__.copy()
        debt_dict['paid_installments'] = pay
        debt_dict['category'] = category.description
        debts_public.append(DebtCategory(**debt_dict))

    return {'debt': debts_public}


@router.post('/', response_model=DebtPublic)
def create_debt(debt: PaidInstallments, user: CurrentUser, session: T_Session):
    if isinstance(debt.plots, str):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Value invalid plots: {debt.plots}.',
        )

    db_category = session.scalar(
        select(Category).where(
            Category.id == debt.category_id, Category.user_id == user.id
        )
    )

    if not db_category:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Category not found'
        )

    if debt.plots == 0:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Value invalid plots: {debt.plots}.',
        )

    db_description = session.scalar(
        select(Debt).where(
            Debt.user_id == user.id,
            Debt.description.contains(debt.description),
            extract('month', Debt.purchasedate) == debt.purchasedate.month,
            extract('year', Debt.purchasedate) == debt.purchasedate.year,
        )
    )

    if db_description:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Debt: {debt.description}'
            + ' already exists for this month',
        )
    count_paidinstallments = debt.paidinstallments
    plots_count = debt.plots
    date = debt.purchasedate
    value = round(debt.value / debt.plots, 2)

    db_debt = Debt(
        description=debt.description,
        category_id=debt.category_id,
        value=debt.value,
        plots=debt.plots,
        purchasedate=debt.purchasedate,
        state=DebtState.pay
        if count_paidinstallments == plots_count
        else DebtState.pending,
        note=debt.note,
        user_id=user.id,
    )

    session.add(db_debt)
    session.flush()

    if plots_count > 1:
        for count in range(1, plots_count + 1):
            date += relativedelta(months=1)

            db_todo = DebtInstallment(
                debt_id=db_debt.id,
                installmentamount=value,
                number=count,
                duedate=date,
                amount=None if count > count_paidinstallments else value,
                paid_date=None if count > count_paidinstallments else date,
                state=(
                    DebtState.pending
                    if count > count_paidinstallments
                    else DebtState.pay
                ),
                user_id=user.id,
            )
            session.add(db_todo)

        session.commit()
        session.refresh(db_debt)
        return db_debt

    db_debt_installment = DebtInstallment(
        debt_id=db_debt.id,
        installmentamount=value,
        number=1,
        duedate=date + relativedelta(months=1),
        amount=value if count_paidinstallments == 1 else None,
        paid_date=(
            date + relativedelta(months=1)
            if count_paidinstallments == 1
            else None
        ),
        state=(
            DebtState.pay if count_paidinstallments == 1 else DebtState.pending
        ),
        user_id=user.id,
    )

    session.add(db_debt_installment)
    session.commit()
    session.refresh(db_debt)
    return db_debt


@router.patch('/{debt_id}', response_model=Message)
def path_debt(
    debt_id: int,
    session: T_Session,
    user: CurrentUser,
    plots: PayInstallentsSchema,
):
    db_debt = session.scalar(
        select(Debt).where(Debt.user_id == user.id, Debt.id == debt_id)
    )

    if not db_debt:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Debt not found'
        )

    plot_ids = plots.plot_ids

    installments = session.scalars(
        select(DebtInstallment).where(
            DebtInstallment.debt_id == debt_id,
            DebtInstallment.id.in_(plot_ids),
            DebtInstallment.user_id == user.id,
            DebtInstallment.state.in_([DebtState.pending, DebtState.overdue]),
        )
    ).all()

    if not installments or len(installments) != len(plot_ids):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='One or more installments not found.',
        )

    for installment in installments:
        installment.state = DebtState.pay
        installment.paid_date = datetime.today()
        installment.amount = (
            installment.installmentamount if plots.amount else plots.amount
        )

        if user.fcm_token:
            send_notification(
                user.fcm_token,
                '✅ Parcela paga',
                f'Sua parcela nº {installment.number}'
                + f' da divida {db_debt.description} foi paga',
            )

    pending_installments = session.scalars(
        select(DebtInstallment).where(
            DebtInstallment.debt_id == debt_id,
            DebtInstallment.user_id == user.id,
            DebtInstallment.state == DebtState.pending,
        )
    ).first()

    if not pending_installments:
        db_debt.state = DebtState.pay

    session.commit()
    return {'message': 'paid installments'}


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


@router.get('/{debt_id}/installments', response_model=DebtInstallmentsList)
def list_installments(
    debt_id: int,
    session: T_Session,
    user: CurrentUser,
    debt_filter: Annotated[FilterDebtInstallments, Query()],
):
    query = select(DebtInstallment).where(
        DebtInstallment.debt_id == debt_id, DebtInstallment.user_id == user.id
    )

    if debt_filter.state:
        query = query.filter(DebtInstallment.state == debt_filter.state)
    else:
        query = query.filter(
            DebtInstallment.state.in_([DebtState.pending, DebtState.overdue])
        )

    debt = session.scalars(
        query.offset(debt_filter.offset).limit(debt_filter.limit)
    ).all()

    return {'debtinstallments': debt}


@router.get('/dashboard', response_model=DebtDashboard)
def dashboard_debt(
    session: T_Session,
    user: CurrentUser,
    debt_filter: Annotated[FilterDashboard, Query()],
):
    query = select(DebtInstallment).where(DebtInstallment.user_id == user.id)

    if debt_filter.start_date:
        query = query.filter(DebtInstallment.duedate >= debt_filter.start_date)

    if debt_filter.end_date:
        query = query.filter(DebtInstallment.duedate <= debt_filter.end_date)

    debt = session.scalars(
        query.offset(debt_filter.offset).limit(debt_filter.limit)
    ).all()

    return DebtDashboard.from_debts(debt)
