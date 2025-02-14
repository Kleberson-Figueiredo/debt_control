from dataclasses import asdict

from sqlalchemy import select

from debt_control.models import Debt, User


def test_create_user(session, mock_db_time):
    with mock_db_time(model=User) as time:
        new_user = User(
            username='alice', password='secret', email='teste@test'
        )
        session.add(new_user)
        session.commit()

    user = session.scalar(select(User).where(User.username == 'alice'))

    assert asdict(user) == {
        'id': 1,
        'username': 'alice',
        'password': 'secret',
        'email': 'teste@test',
        'created_at': time,
        'updated_at': time,
        'debt': [],  # Exercicio
    }


def test_create_debt(session, user: User):
    debt = Debt(
        description='Test Desc',
        value=255,
        plots=1,
        duedate='2025-02-02',
        state='pending',
        user_id=user.id,
    )

    session.add(debt)
    session.commit()
    session.refresh(debt)

    user = session.scalar(select(User).where(User.id == user.id))

    assert debt in user.debt
