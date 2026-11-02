import pytest
from django.db import IntegrityError, transaction

from accounts import services
from accounts.models import User, UserRole, UserRoleAssignment

REGISTER_URL = '/api/auth/register/'
LOGIN_URL = '/api/auth/login/'
PASSWORD = 'DemoPassword14'


def register_payload(**overrides):
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


def test_register_creates_normalized_attendee(client, db):
    response = post(
        client,
        REGISTER_URL,
        register_payload(email='  STUDENT14@Example.com ', first_name='   Oksana   ', last_name='    Koval   '),
    )

    assert response.status_code == 201
    body = response.json()
    assert body['email'] == 'student14@example.com'
    assert body['first_name'] == 'Oksana'
    assert body['last_name'] == 'Koval'
    assert body['roles'] == ['Attendee']
    assert 'password' not in body
    assert 'password_hash' not in body
    user = User.objects.get(email='student14@example.com')
    assert user.password_hash != PASSWORD
    assert list(user.roles.values_list('role', flat=True)) == ['Attendee']


def test_password_is_stored_as_bcrypt_hash_with_cost_12(client, db, settings):
    settings.PASSWORD_HASH_ROUNDS = 12

    post(client, REGISTER_URL, register_payload())

    stored = User.objects.get(email='student14@example.com').password_hash
    assert stored.startswith('$2b$12$')
    assert len(stored) == 60


def test_duplicate_email_returns_409(client, db):
    post(client, REGISTER_URL, register_payload())

    response = post(client, REGISTER_URL, register_payload(email='STUDENT14@EXAMPLE.COM'))

    assert response.status_code == 409
    assert response.json()['detail'] == 'An account with this email already exists.'
    assert User.objects.count() == 1


def test_concurrent_duplicate_is_stopped_by_unique_index(client, db, monkeypatch):
    post(client, REGISTER_URL, register_payload())
    real_email_exists = services.email_exists
    calls = []

    def stale_precheck(email):
        calls.append(email)
        return False if len(calls) == 1 else real_email_exists(email)

    monkeypatch.setattr(services, 'email_exists', stale_precheck)

    response = post(client, REGISTER_URL, register_payload())

    assert response.status_code == 409
    assert User.objects.count() == 1
    assert UserRoleAssignment.objects.count() == 1


@pytest.mark.parametrize(
    'password',
    [
        'short',
        'eventhub14',
        'EVENTHUB14',
        'EventHub',
        'Event14!',
        'ПодіяAb14',
        'EventHub 14',
        ' EventHub14',
        'EventHub14 ',
        'Aa1aaaa',
        'Aa1' + 'a' * 70,
    ],
)
def test_invalid_password_returns_400_and_creates_nothing(client, db, password):
    response = post(client, REGISTER_URL, register_payload(password=password))

    assert response.status_code == 400
    assert 'password' in response.json()
    assert User.objects.count() == 0


@pytest.mark.parametrize('password', ['Aa1' + 'a' * 5, 'Aa1' + 'a' * 69])
def test_password_length_boundaries_are_accepted(client, db, password):
    assert post(client, REGISTER_URL, register_payload(password=password)).status_code == 201


@pytest.mark.parametrize(
    'overrides, field',
    [
        ({'first_name': '   '}, 'first_name'),
        ({'last_name': '   '}, 'last_name'),
        ({'email': 'not-an-email'}, 'email'),
        ({'email': ''}, 'email'),
    ],
)
def test_invalid_profile_fields_return_400(client, db, overrides, field):
    response = post(client, REGISTER_URL, register_payload(**overrides))

    assert response.status_code == 400
    assert field in response.json()
    assert User.objects.count() == 0


def test_client_cannot_choose_role(client, db):
    response = post(client, REGISTER_URL, register_payload(roles=['Admin']))

    assert response.status_code == 201
    assert response.json()['roles'] == ['Attendee']
    assert list(UserRoleAssignment.objects.values_list('role', flat=True)) == ['Attendee']


def test_role_cannot_be_assigned_twice(db):
    user = User.objects.create(email='a@example.com', first_name='A', last_name='B', password_hash='x')
    UserRoleAssignment.objects.create(user=user, role=UserRole.ATTENDEE)

    with pytest.raises(IntegrityError), transaction.atomic():
        UserRoleAssignment.objects.create(user=user, role=UserRole.ATTENDEE)


def test_login_returns_profile_for_correct_password(client, db):
    post(client, REGISTER_URL, register_payload())

    response = post(client, LOGIN_URL, {'email': ' STUDENT14@Example.com ', 'password': PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body['email'] == 'student14@example.com'
    assert body['roles'] == ['Attendee']
    assert 'password_hash' not in body


def test_wrong_password_and_unknown_email_give_identical_401(client, db):
    post(client, REGISTER_URL, register_payload())

    wrong_password = post(client, LOGIN_URL, {'email': 'student14@example.com', 'password': 'WrongPassword14'})
    unknown_email = post(client, LOGIN_URL, {'email': 'nobody14@example.com', 'password': PASSWORD})

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()['detail'] == 'Invalid email or password.'


@pytest.mark.parametrize('password', ['', 'short', 'eventhub14', ' DemoPassword14', 'Event14!'])
def test_login_format_errors_return_400_not_401(client, db, password):
    post(client, REGISTER_URL, register_payload())

    response = post(client, LOGIN_URL, {'email': 'student14@example.com', 'password': password})

    assert response.status_code == 400
    assert 'password' in response.json()


def test_login_password_is_case_sensitive(client, db):
    post(client, REGISTER_URL, register_payload())

    response = post(client, LOGIN_URL, {'email': 'student14@example.com', 'password': 'Demopassword14'})

    assert response.status_code == 401