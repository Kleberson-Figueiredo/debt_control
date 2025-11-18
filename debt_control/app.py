from http import HTTPStatus

from fastapi import FastAPI

from debt_control.routers import auth, category, debt, users
from debt_control.schemas import Message
from debt_control.services.scheduler import start_scheduler

app = FastAPI()

# # Libera o frontend local
# origins = [
#     "http://127.0.0.1:5500",
#     "http://localhost:5500",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,          # Ou ["*"] para liberar tudo (não recomendado em produção)
#     allow_credentials=True,
#     allow_methods=["*"],            # Permite todos os métodos (GET, POST, etc)
#     allow_headers=["*"],            # Permite todos os cabeçalhos
# )

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(category.router)
app.include_router(debt.router)

# inicia agendador ao subir o app
start_scheduler()  # pragma: no cover


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'Olá Mundo!'}
