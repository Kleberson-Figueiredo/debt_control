from datetime import datetime, timedelta
from http import HTTPStatus
from zoneinfo import ZoneInfo

import factory.fuzzy

# ...
from debt_control.models import Debt, DebtState

start_date = datetime.now(tz=ZoneInfo('UTC')).date().replace(day=1)
end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(
    day=1
) - timedelta(days=1)
purchasedate = (start_date.replace(day=28) - timedelta(days=4)).replace(
    day=1
) - timedelta(days=1)


def test_create_debt(client, token, mock_db_time, category):
    with mock_db_time(model=Debt) as time:
        response = client.post(
            '/debt',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'description': 'Test debt description',
                'value': 255,
                'category_id': category.id,
                'plots': 1,
                'purchasedate': str(start_date),
                'state': 'pending',
                'note': None,
                'paidinstallments': None,
            },
        )

    assert response.json() == {
        'id': 1,
        'description': 'Test debt description',
        'category_id': category.id,
        'value': 255.0,
        'plots': 1,
        'purchasedate': str(start_date),
        'state': 'pending',
        'note': None,
        'created_at': time.isoformat(),
        'updated_at': time.isoformat(),
        'paid_installments': None,
    }


def test_create_debt_should_return_2_plots(
    client, token, mock_db_time, category
):
    with mock_db_time(model=Debt) as time:
        response = client.post(
            '/debt',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'description': 'Test debt description',
                'value': 255,
                'category_id': category.id,
                'plots': 2,
                'purchasedate': str(start_date),
                'state': 'pending',
                'note': None,
                'paidinstallments': 0,
            },
        )

    assert response.json() == {
        'id': 1,
        'description': 'Test debt description',
        'category_id': category.id,
        'value': 255.0,
        'plots': 2,
        'purchasedate': str(start_date),
        'state': 'pending',
        'note': None,
        'created_at': time.isoformat(),
        'updated_at': time.isoformat(),
        'paid_installments': None,
    }


class DebtFactory(factory.Factory):
    class Meta:
        model = Debt

    description = factory.Faker('text')
    category_id = 1
    value = factory.fuzzy.FuzzyFloat(10, 100)
    plots = factory.Faker('random_int', min=1, max=12)
    purchasedate = factory.fuzzy.FuzzyDate(
        start_date=start_date,
        end_date=end_date,
    )
    state = factory.fuzzy.FuzzyChoice(DebtState)
    note = None
    user_id = 1


def test_list_debt_should_return_5_debt(
    session, client, user, token, category
):
    expected_debts = 5
    session.bulk_save_objects(DebtFactory.create_batch(5, user_id=user.id))
    session.commit()

    response = client.get(
        '/debt/',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_list_debt_pagination_should_return_5_debt(
    session, user, client, token, category
):
    expected_debts = 5
    session.bulk_save_objects(DebtFactory.create_batch(6, user_id=user.id))
    session.commit()

    response = client.get(
        '/debt/?offset=1&limit=5',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_list_debt_filter_description_should_return_5_debt(
    session, user, client, token, category
):
    expected_debts = 5
    session.bulk_save_objects(
        DebtFactory.create_batch(5, user_id=user.id, description='description')
    )
    session.commit()

    response = client.get(
        '/debt/?description=desc',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_list_debt_filter_state_should_return_5_debt(
    session, user, client, token, category
):
    expected_debts = 5
    session.bulk_save_objects(
        DebtFactory.create_batch(5, user_id=user.id, state=DebtState.pending)
    )
    session.commit()

    response = client.get(
        '/debt/?state=pending',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_list_debt_filter_combined_should_return_5_debt(
    session, user, client, token, category
):
    expected_debts = 5
    session.bulk_save_objects(
        DebtFactory.create_batch(
            5,
            user_id=user.id,
            description='combined description',
            state=DebtState.pending,
            category_id=category.id,
        )
    )

    session.bulk_save_objects(
        DebtFactory.create_batch(
            3,
            user_id=user.id,
            description='other description',
            state=DebtState.overdue,
            category_id=category.id,
        )
    )
    session.commit()

    response = client.get(
        '/debt/?description=combined&state=pending',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_patch_debt_error(client, token):
    response = client.patch(
        '/debt/100',
        json={'plot_ids': [1], 'amount': 0},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Debt not found'}


def test_delete_debt(session, client, user, token, category):
    debt = DebtFactory(user_id=user.id)

    session.add(debt)
    session.commit()

    response = client.delete(
        f'/debt/{debt.id}', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'message': 'Debt has been deleted successfully.'
    }


def test_delete_debt_error(client, token):
    response = client.delete(
        '/debt/100', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Debt not found.'}


# def test_create_debt_error_should_return_value_invalid_plots(
#     client, token, category
# ):
#     response = client.post(
#         '/debt',
#         headers={'Authorization': f'Bearer {token}'},
#         json={
#             'description': 'Test debt description',
#             'category_id': category.id,
#             'value': 255,
#             'plots': 0,
#             'purchasedate': str(start_date),
#             'state': 'pending',
#             'paidinstallments': None,
#             'note': None,
#         },
#     )

#     assert response.status_code == HTTPStatus.BAD_REQUEST
#     assert response.json() == {'detail': 'Value invalid plots: 0.'}


def test_list_dashboard_filter_start_data(client, token, category):
    _response = client.post(
        '/debt',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'description': 'Test debt description',
            'category_id': category.id,
            'value': 255,
            'plots': 1,
            'purchasedate': str(end_date),
            'state': 'pending',
            'paidinstallments': None,
            'note': None,
        },
    )

    response = client.get(
        f'/debt/dashboard/?start_date={start_date}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.json() == {
        'total_canceled': 0.0,
        'total_canceled_value': 0.0,
        'total_debt': 1.0,
        'total_debt_value': 255.0,
        'total_overdue': 0.0,
        'total_overdue_value': 0.0,
        'total_pay': 0.0,
        'total_pay_value': 0.0,
        'total_pending': 1.0,
        'total_pending_value': 255.0,
    }


def test_list_dashboard_filter_end_date(client, token, category):
    _response = client.post(
        '/debt',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'description': 'Test debt description',
            'category_id': category.id,
            'value': 255,
            'plots': 1,
            'purchasedate': str(end_date),
            'state': 'pending',
            'paidinstallments': None,
            'note': None,
        },
    )

    response = client.get(
        f'/debt/dashboard/?end_date={end_date}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.json() == {
        'total_canceled': 0.0,
        'total_canceled_value': 0.0,
        'total_debt': 1.0,
        'total_debt_value': 255.0,
        'total_overdue': 0.0,
        'total_overdue_value': 0.0,
        'total_pay': 0.0,
        'total_pay_value': 0.0,
        'total_pending': 1.0,
        'total_pending_value': 255.0,
    }


# def test_debt_dashboard_from_debts():
#     states = ['pending', 'pay', 'overdue', 'canceled']
#     debts = []

#     for k in states:
#         debts.append(
#             Debt(
#                 description='a',
#                 value=1,
#                 plots=1,
#                 duedate=start_date,
#                 state=k,
#                 user_id=1,
#             )
#         )

#     result = DebtDashboard.from_debts(debts)

#     assert result.total_debt_value == int(4)
#     assert result.total_debt == int(4)

#     assert result.total_pay_value == float(1)
#     assert result.total_pay == float(1)

#     assert result.total_pending_value == float(1)
#     assert result.total_pending == float(1)

#     assert result.total_canceled_value == float(1)
#     assert result.total_canceled == float(1)

#     assert result.total_overdue_value == float(1)
#     assert result.total_overdue == float(1)


def test_create_debt_error_should_return_value_Debt_already_exists(
    client, token, user, session, category
):
    debt = DebtFactory(user_id=user.id, category_id=category.id)

    session.add(debt)
    session.commit()

    response = client.post(
        '/debt',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'description': f'{debt.description}',
            'category_id': category.id,
            'value': 255,
            'plots': 1,
            'purchasedate': f'{debt.purchasedate}',
            'state': 'pending',
            'paidinstallments': None,
            'note': None,
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        'detail': f'Debt: {debt.description}'
        + ' already exists for this month'
    }
