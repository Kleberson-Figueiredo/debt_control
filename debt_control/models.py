from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import ForeignKey, exists, func, update
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

table_registry = registry()


class DebtState(str, Enum):
    pay = 'pay'
    overdue = 'overdue'
    pending = 'pending'
    canceled = 'canceled'


@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    fcm_token: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    categories: Mapped[List['Category']] = relationship(
        init=False, back_populates='user', cascade='all, delete-orphan'
    )

    debts: Mapped[List['Debt']] = relationship(
        init=False, back_populates='user', cascade='all, delete-orphan'
    )

    debt_installments: Mapped[List['DebtInstallment']] = relationship(
        init=False, back_populates='user', cascade='all, delete-orphan'
    )


@table_registry.mapped_as_dataclass
class Category:
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    description: Mapped[str]

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    user: Mapped[User] = relationship(init=False, back_populates='categories')

    debts: Mapped[List['Debt']] = relationship(
        init=False, back_populates='category', cascade='all, delete-orphan'
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )


@table_registry.mapped_as_dataclass
class Debt:
    __tablename__ = 'debt'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    description: Mapped[str]
    value: Mapped[float]
    plots: Mapped[str]
    purchasedate: Mapped[date]
    state: Mapped[DebtState]
    note: Mapped[str] = mapped_column(nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    category_id: Mapped[int] = mapped_column(ForeignKey('category.id'))

    user: Mapped[User] = relationship(init=False, back_populates='debts')

    category: Mapped[Category] = relationship(
        init=False, back_populates='debts'
    )

    installments: Mapped[List['DebtInstallment']] = relationship(
        init=False, back_populates='debt', cascade='all, delete-orphan'
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    def update_overdue_debts(cls, session):
        stmt = (
            update(cls)
            .where(
                exists().where(
                    (DebtInstallment.debt_id == cls.id)
                    & (DebtInstallment.state == 'overdue')
                )
            )
            .values(state='overdue')
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount


@table_registry.mapped_as_dataclass
class DebtInstallment:
    __tablename__ = 'debt_installment'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    debt_id: Mapped[int] = mapped_column(ForeignKey('debt.id'))
    installmentamount: Mapped[float]
    number: Mapped[int]
    duedate: Mapped[date]
    amount: Mapped[float] = mapped_column(nullable=True)
    paid_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    state: Mapped[DebtState]

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    user: Mapped[User] = relationship(
        init=False, back_populates='debt_installments'
    )
    debt: Mapped[Debt] = relationship(
        init=False, back_populates='installments'
    )

    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    def update_overdue(cls, session):
        today = date.today()
        stmt = (
            update(cls)
            .where(cls.state == 'pending', cls.duedate < today)
            .values(state='overdue')
            .execution_options(synchronize_session='fetch')
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount
