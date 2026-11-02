import pytest

from accounts.models import User, UserRoleAssignment

REGISTER_URL = '/api/auth/register/'
LOGIN_URL = '/api/auth/login/'
PASSWORD = 'DemoPassword14'


def payload(**overrides):
    data = {
        'email': 'student14@example.com',
        'password': PASSWORD,
        'first_name': 'Oksana',
        'last_name': 'Koval',
    }
    data.update(overrides)
    return data


def post(client, url, data):
    return client.post(url, data, content_type='application/json')


def test_given_display_name_is_trimmed_and_returned(client, db):
    response = post(client, REGISTER_URL, payload(display_name='   Ksu   '))

    assert response.status_code == 201
    assert response.json()['display_name'] == 'Ksu'
    assert User.objects.get(email='student14@example.com').display_name == 'Ksu'


def test_missing_display_name_falls_back_to_full_name(client, db):
    response = post(client, REGISTER_URL, payload())

    assert response.status_code == 201
    assert response.json()['display_name'] == 'Oksana Koval'


def test_whitespace_display_name_falls_back_to_full_name(client, db):
    response = post(client, REGISTER_URL, payload(display_name='     '))

    assert response.status_code == 201
    assert response.json()['display_name'] == 'Oksana Koval'


def test_display_name_length_limit_is_80(client, db):
    assert post(client, REGISTER_URL, payload(display_name='a' * 80)).status_code == 201
    response = post(client, REGISTER_URL, payload(email='other14@example.com', display_name='a' * 81))

    assert response.status_code == 400
    assert 'display_name' in response.json()
    assert User.objects.count() == 1


@pytest.mark.parametrize('value', [None, ['Ksu'], {'name': 'Ksu'}])
def test_non_string_display_name_is_rejected(client, db, value):
    response = post(client, REGISTER_URL, payload(display_name=value))

    assert response.status_code == 400
    assert 'display_name' in response.json()


def test_display_name_does_not_change_role_password_or_leak_hash(client, db):
    response = post(client, REGISTER_URL, payload(display_name='Ksu'))

    assert response.json()['roles'] == ['Attendee']
    assert 'password_hash' not in response.json()
    assert list(UserRoleAssignment.objects.values_list('role', flat=True)) == ['Attendee']
    login = post(client, LOGIN_URL, {'email': 'student14@example.com', 'password': PASSWORD})
    assert login.status_code == 200
    assert login.json()['display_name'] == 'Ksu'