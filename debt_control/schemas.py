from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, EmailStr

from debt_control.models import DebtState


class Message(BaseModel):
    message: str


class UserSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    fcm_token: None | str = None


class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: list[UserPublic]


class UpdateFcmToken(BaseModel):
    fcm_token: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserPublic


class TokenData(BaseModel):
    username: str | None = None


class FilterPage(BaseModel):
    offset: int = 0
    limit: int = 100


class CategorySchema(BaseModel):
    description: str


class CategoryPublic(CategorySchema):
    id: int
    created_at: datetime
    updated_at: datetime


class FilterCategory(FilterPage):
    description: str | None = None


class ListCategories(BaseModel):
    categories: list[CategoryPublic]


class DebtSchema(BaseModel):
    description: str
    category_id: int
    value: float
    plots: int | None
    purchasedate: date
    note: str | None = None


class PaidInstallments(DebtSchema):
    paidinstallments: int | None


class DebtPublic(DebtSchema):
    state: DebtState = 'pending'
    paid_installments: int | None = None
    id: int
    created_at: datetime
    updated_at: datetime


class DebtCategory(DebtPublic):
    category: str


class DebtList(BaseModel):
    debt: list[DebtCategory]


class FilterDebt(FilterPage):
    description: str | None = None
    state: DebtState | None = None


class DebtUpdate(BaseModel):
    state: DebtState | None = None


class DebtInstallmentSchema(BaseModel):
    id: int
    debt_id: int
    installmentamount: float
    number: int
    duedate: date
    amount: float | None = None
    paid_date: date | None = None
    state: DebtState


class PayInstallentsSchema(BaseModel):
    plot_ids: list[int]
    amount: float | None


class DebtInstallmentsPublic(DebtInstallmentSchema):
    id: int
    created_at: datetime
    updated_at: datetime


class DebtInstallmentsList(BaseModel):
    debtinstallments: list[DebtInstallmentSchema]


class FilterDebtInstallments(FilterPage):
    state: DebtState | None = None


class FilterDashboard(FilterPage):
    start_date: date | None = date.today().replace(day=1)
    end_date: date | None = (
        start_date.replace(day=28) + timedelta(days=4)
    ).replace(day=1) - timedelta(days=1)


class DebtDashboard(BaseModel):
    total_debt_value: float
    total_debt: float

    total_pay_value: float
    total_pay: float

    total_pending_value: float
    total_pending: float

    total_overdue_value: float
    total_overdue: float

    total_canceled_value: float
    total_canceled: float

    @classmethod
    def from_debts(cls, debts):
        total_debt_value = 0
        total_debt = []

        total_pay_value = 0
        total_pay = []

        total_pending_value = 0
        total_pending = []

        total_overdue_value = 0
        total_overdue = []

        total_canceled_value = 0
        total_canceled = []

        today = date.today()

        for debt in debts:
            value = debt.installmentamount
            duedate = debt.duedate
            state = debt.state

            total_debt_value += value
            total_debt.append(value)

            if state == 'pay':
                total_pay_value += value
                total_pay.append(value)
            elif state == 'pending':
                total_pending_value += value
                total_pending.append(value)
            elif state == 'canceled':
                total_canceled_value += value
                total_canceled.append(value)
            elif duedate < today:  # Verifica se a dívida está vencida
                total_overdue_value += value
                total_overdue.append(value)

        return cls(
            total_debt_value=round(total_debt_value, 2),
            total_debt=len(total_debt),
            total_pay_value=round(total_pay_value, 2),
            total_pay=len(total_pay),
            total_pending_value=round(total_pending_value, 2),
            total_pending=len(total_pending),
            total_overdue_value=round(total_overdue_value, 2),
            total_overdue=len(total_overdue),
            total_canceled_value=round(total_canceled_value, 2),
            total_canceled=len(total_canceled),
        )
