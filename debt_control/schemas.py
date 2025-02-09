from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, EmailStr

from debt_control.models import DebtState


class Message(BaseModel):
    message: str


class UserSchema(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: list[UserPublic]


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class FilterPage(BaseModel):
    offset: int = 0
    limit: int = 100


class DebtSchema(BaseModel):
    description: str
    value: float
    plots: int
    duedate: str
    state: DebtState


class DebtPublic(DebtSchema):
    id: int
    created_at: datetime
    updated_at: datetime


class DebtList(BaseModel):
    debt: list[DebtPublic]


class FilterDebt(FilterPage):
    description: str | None = None
    state: DebtState | None = None
    # start_date: str | datetime = None  # Data inicial para o filtro
    # end_date: str | datetime = None    # Data final para o filtro
    


class DebtUpdate(BaseModel):
    state: DebtState | None = None
