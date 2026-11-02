from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone

from events.models import Booking, Resource, ResourceType


@pytest.fixture
def resource_type(db):
    return ResourceType.objects.create(name='Hall')


def make_resource(resource_type, name):
    return Resource.objects.create(name=name, price_per_hour=10, resource_type=resource_type)


def make_booking(resource, shift):
    start = timezone.now() + timedelta(days=1, hours=shift)
    return Booking.objects.create(
        resource=resource,
        client_name='Alex',
        client_email='alex@example.com',
        start_time=start,
        end_time=start + timedelta(hours=1),
    )


def test_composite_index_exists(db):
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, 'events_resource')

    assert constraints['ix_resource_type_name_id']['columns'] == ['resource_type_id', 'name', 'id']


def test_list_returns_booking_count_per_resource(client, resource_type):
    busy = make_resource(resource_type, 'Busy')
    empty = make_resource(resource_type, 'Empty')
    make_booking(busy, 0)
    make_booking(busy, 2)

    response = client.get('/api/resources/')

    counts = {item['name']: item['booking_count'] for item in response.json()['items']}
    assert counts == {'Busy': 2, 'Empty': 0}
    assert response.json()['total_count'] == 2


def test_list_uses_fixed_number_of_queries(client, resource_type, django_assert_num_queries):
    for number in range(5):
        resource = make_resource(resource_type, f'Room {number}')
        make_booking(resource, number * 2)

    with django_assert_num_queries(2):
        response = client.get('/api/resources/')

    assert response.status_code == 200
    assert len(response.json()['items']) == 5


def test_list_filters_by_type_and_sorts_by_name(client, resource_type):
    other = ResourceType.objects.create(name='Desk')
    make_resource(resource_type, 'B')
    make_resource(resource_type, 'A')
    make_resource(other, 'C')

    response = client.get(f'/api/resources/?resourceTypeId={resource_type.id}&sortBy=name&order=asc')

    assert [item['name'] for item in response.json()['items']] == ['A', 'B']


def test_seed_command_refuses_outside_development(db):
    with pytest.raises(CommandError):
        call_command('seed_performance_data', count=5)


def test_seed_and_explain_commands_work(db, settings):
    settings.SETTINGS_MODULE = 'config.settings.development'

    call_command('seed_performance_data', count=25, batch_size=10, stdout=StringIO())

    assert Resource.objects.filter(resource_type__name__startswith='Performance data ').count() == 25
    assert Booking.objects.count() == 6

    call_command('seed_performance_data', count=25, stdout=StringIO())
    assert Resource.objects.count() == 25

    call_command('seed_performance_data', count=12, batch_size=5, reset=True, stdout=StringIO())
    assert Resource.objects.count() == 12

    output = StringIO()
    call_command('explain_resources', mode='current', repeat=1, stdout=output)
    assert 'Plan:' in output.getvalue()