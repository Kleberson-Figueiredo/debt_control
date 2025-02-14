from datetime import date, timedelta
from http import HTTPStatus

import factory.fuzzy
from dateutil.relativedelta import relativedelta

# ...
from debt_control.models import Debt, DebtState
from debt_control.schemas import DebtDashboard

start_date = date.today().replace(day=1)
end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(
    day=1
) - timedelta(days=1)


def test_create_debt(client, token, mock_db_time):
    with mock_db_time(model=Debt) as time:
        response = client.post(
            '/debt',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'description': 'Test debt description',
                'value': 255,
                'plots': 1,
                'duedate': str(start_date),
                'state': 'pending',
            },
        )

    assert response.json() == {
        'id': 1,
        'description': 'Test debt description',
        'value': 255.0,
        'plots': '1|1',
        'duedate': str(start_date),
        'state': 'pending',
        'created_at': time.isoformat(),
        'updated_at': time.isoformat(),
    }


def test_create_debt_should_return_2_plots(client, token, mock_db_time):
    with mock_db_time(model=Debt) as time:
        response = client.post(
            '/debt',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'description': 'Test debt description',
                'value': 255,
                'plots': 2,
                'duedate': str(start_date),
                'state': 'pending',
            },
        )

    assert response.json() == {
        'id': 2,
        'description': 'Test debt description',
        'value': 255.0,
        'plots': '2|2',
        'duedate': str(start_date + relativedelta(months=1)),
        'state': 'pending',
        'created_at': time.isoformat(),
        'updated_at': time.isoformat(),
    }


class DebtFactory(factory.Factory):
    class Meta:
        model = Debt

    description = factory.Faker('text')
    value = factory.fuzzy.FuzzyFloat(10, 100)
    plots = factory.Faker('random_int', min=1, max=12)
    duedate = factory.fuzzy.FuzzyDate(
        start_date=date.today(), end_date=date.today() + timedelta(days=15)
    )
    state = factory.fuzzy.FuzzyChoice(DebtState)
    user_id = 1


def test_list_debt_should_return_5_debt(session, client, user, token):
    expected_debts = 5
    session.bulk_save_objects(DebtFactory.create_batch(5, user_id=user.id))
    session.commit()

    response = client.get(
        '/debt/',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_list_debt_pagination_should_return_2_debt(
    session, user, client, token
):
    expected_debts = 2
    session.bulk_save_objects(DebtFactory.create_batch(5, user_id=user.id))
    session.commit()

    response = client.get(
        '/debt/?offset=1&limit=2',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_list_debt_filter_description_should_return_5_debt(
    session, user, client, token
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
    session, user, client, token
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


def test_list_debt_filter_start_duedate_should_return_5_debt(
    session, user, client, token
):
    expected_debts = 5
    session.bulk_save_objects(
        DebtFactory.create_batch(5, user_id=user.id, state=DebtState.pending)
    )
    session.commit()

    response = client.get(
        f'/debt/?start_duedate={date.today().replace(day=1)}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_list_debt_filter_end_duedate_should_return_5_debt(
    session, user, client, token
):
    expected_debts = 5
    session.bulk_save_objects(
        DebtFactory.create_batch(5, user_id=user.id, state=DebtState.pending)
    )
    session.commit()

    response = client.get(
        f'/debt/?end_duedate={end_date}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_list_debt_filter_combined_should_return_5_debt(
    session, user, client, token
):
    expected_debts = 5
    session.bulk_save_objects(
        DebtFactory.create_batch(
            5,
            user_id=user.id,
            description='combined description',
            state=DebtState.pending,
        )
    )

    session.bulk_save_objects(
        DebtFactory.create_batch(
            3,
            user_id=user.id,
            description='other description',
            state=DebtState.overdue,
        )
    )
    session.commit()

    response = client.get(
        f'/debt/?description=combined&state=pending&start_duedate={start_date}'
        + f'&end_duedate={end_date}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert len(response.json()['debt']) == expected_debts


def test_patch_debt_error(client, token):
    response = client.patch(
        '/debt/100',
        json={},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Debt not found'}


def test_patch_todo(session, client, user, token):
    debt = DebtFactory(user_id=user.id)

    session.add(debt)
    session.commit()

    response = client.patch(
        f'/debt/{debt.id}',
        json={'state': 'canceled'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['state'] == 'canceled'


def test_delete_debt(session, client, user, token):
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


def test_list_debt_should_return_all_expected_fields__exercicio(
    session, client, user, token, mock_db_time
):
    with mock_db_time(model=Debt) as time:
        debt = DebtFactory.create(user_id=user.id)
        session.add(debt)
        session.commit()

    session.refresh(debt)
    response = client.get(
        '/debt/',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.json()['debt'] == [
        {
            'created_at': time.isoformat(),
            'updated_at': time.isoformat(),
            'description': debt.description,
            'id': debt.id,
            'value': debt.value,
            'plots': debt.plots,
            'duedate': debt.duedate.isoformat(),
            'state': debt.state.value,
        }
    ]


def test_create_debt_error_should_return_value_invalid_plots(client, token):
    response = client.post(
        '/debt',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'description': 'Test debt description',
            'value': 255,
            'plots': 'a',
            'duedate': str(start_date),
            'state': 'pending',
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Value invalid plots: a.'}


def test_list_dashboard_filter_start_data(client, token):
    _response = client.post(
        '/debt',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'description': 'Test debt description',
            'value': 255,
            'plots': 1,
            'duedate': str(start_date),
            'state': 'pending',
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


def test_list_dashboard_filter_end_date(client, token):
    _response = client.post(
        '/debt',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'description': 'Test debt description',
            'value': 255,
            'plots': 1,
            'duedate': str(start_date),
            'state': 'pending',
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


def test_debt_dashboard_from_debts():
    states = ['pending', 'pay', 'overdue', 'canceled']
    debts = []

    for k in states:
        debts.append(
            Debt(
                description='a',
                value=1,
                plots=1,
                duedate=start_date,
                state=k,
                user_id=1,
            )
        )

    result = DebtDashboard.from_debts(debts)

    assert result.total_debt_value == int(4)
    assert result.total_debt == int(4)

    assert result.total_pay_value == float(1)
    assert result.total_pay == float(1)

    assert result.total_pending_value == float(1)
    assert result.total_pending == float(1)

    assert result.total_canceled_value == float(1)
    assert result.total_canceled == float(1)

    assert result.total_overdue_value == float(1)
    assert result.total_overdue == float(1)


def test_create_debt_error_should_return_value_Debt_already_exists(
    client, token, user, session
):
    debt = DebtFactory(user_id=user.id)

    session.add(debt)
    session.commit()

    response = client.post(
        '/debt',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'description': f'{debt.description}',
            'value': 255,
            'plots': 1,
            'duedate': f'{debt.duedate}',
            'state': 'pending',
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {
        'detail': f'Debt: {debt.description}'
        + f' already exists for date: {debt.duedate}'
    }
