import os
import json

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, messaging

load_dotenv()

firebase_key_path = os.getenv('FIREBASE_CREDENTIALS')

if firebase_key_path:  # só inicializa se a variável estiver definida
    cred = credentials.Certificate(json.loads(firebase_key_path))
    firebase_admin.initialize_app(cred)
else:
    # Modo teste/CI: não inicializa Firebase
    firebase_admin = None
    messaging = None


def send_notification(token: str, title: str, body: str):  # pragma: no cover
    if not token:
        return {'error': 'Usuário não possui token registrado'}

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )
    return messaging.send(message)
