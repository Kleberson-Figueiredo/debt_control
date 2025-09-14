from datetime import datetime, timedelta

from sqlalchemy import select

from debt_control.models import Debt, DebtInstallment, DebtState, User
from debt_control.utils.firebase import send_notification


def notify_installments(session):  # pragma: no cover
    today = datetime.today().date()
    five_days_ahead = today + timedelta(days=5)

    # SQLAlchemy 2.x: session.scalars(select(...)).all()
    installments = session.scalars(select(DebtInstallment)).all()

    for inst in installments:
        debt = session.scalar(select(Debt).where(Debt.id == inst.debt_id))

        user = session.get(User, inst.user_id)
        if not user or not user.fcm_token:
            continue
        # 5 dias antes
        if inst.state == DebtState.pending and inst.duedate == five_days_ahead:
            print('5 dias')
            send_notification(
                user.fcm_token,
                f'📅 Parcela da divida {debt.description} a vencer',
                f'Sua parcela nº {inst.number}'
                + f' vence em 5 dias. Valor: R$ {inst.installmentamount:.2f}',
            )

        # no dia
        if inst.state == DebtState.pending and inst.duedate == today:
            print(f'Hoje {debt.description}')
            send_notification(
                user.fcm_token,
                f'⚠️ Parcela da divida {debt.description} vence hoje',
                f'Sua parcela nº {inst.number}'
                + f' vence hoje. Valor: R$ {inst.installmentamount:.2f}',
            )
