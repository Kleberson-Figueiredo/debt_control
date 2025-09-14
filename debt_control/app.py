from http import HTTPStatus

from fastapi import FastAPI

from debt_control.routers import auth, category, debt, users
from debt_control.schemas import Message
from debt_control.services.scheduler import start_scheduler

app = FastAPI()

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(category.router)
app.include_router(debt.router)

# inicia agendador ao subir o app
start_scheduler()


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'Olá Mundo!'}
