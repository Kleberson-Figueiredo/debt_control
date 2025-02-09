from http import HTTPStatus

from fastapi import FastAPI

from debt_control.routers import auth, debt, users
from debt_control.schemas import Message

app = FastAPI()

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(debt.router)


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'Olá Mundo!'}
