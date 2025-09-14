from dataclasses import asdict

from sqlalchemy import select

from debt_control.models import Category, Debt, User


def test_create_user(session, mock_db_time):
    with mock_db_time(model=User) as time:
        new_user = User(
            username='alice',
            password='secret',
            email='teste@test',
            fcm_token=None,
        )
        session.add(new_user)
        session.commit()

    user = session.scalar(select(User).where(User.username == 'alice'))

    assert asdict(user) == {
        'id': 1,
        'username': 'alice',
        'password': 'secret',
        'email': 'teste@test',
        'fcm_token': None,
        'categories': [],
        'debt_installments': [],
        'created_at': time,
        'updated_at': time,
        'debts': [],  # Exercicio
    }


def test_create_category(session, user: User):
    category = Category(
        description='Test Desc',
        user_id=user.id,
    )

    session.add(category)
    session.commit()
    session.refresh(category)

    db_user = session.scalar(select(User).where(User.id == user.id))
    assert category in db_user.categories


def test_create_debt(session, user: User):
    category = Category(
        description='Test Category',
        user_id=user.id,
    )
    session.add(category)
    session.commit()
    session.refresh(category)

    debt = Debt(
        description='Test Desc',
        value=255,
        plots=1,
        purchasedate='2025-02-02',
        state='pending',
        user_id=user.id,
        category_id=category.id,
        note=None,
    )

    session.add(debt)
    session.commit()
    session.refresh(debt)

    db_user = session.scalar(select(User).where(User.id == user.id))

    assert debt in db_user.debts
