import time
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import Resource, ResourceType


@pytest.fixture
def resource(db):
    resource_type = ResourceType.objects.create(name='Meeting Room')
    return Resource.objects.create(
        name='Room',
        description='Room',
        price_per_hour=10,
        resource_type=resource_type,
    )


def booking_payload(email):
    start = timezone.now() + timedelta(days=1)
    return {
        'client_name': 'Alex',
        'client_email': email,
        'start_time': start.isoformat(),
        'end_time': (start + timedelta(hours=2)).isoformat(),
    }


def create_booking(client, resource, email):
    return client.post(
        f'/api/resources/{resource.id}/bookings/',
        booking_payload(email),
        content_type='application/json',
    )


def wait_for_job_status(client, job_id, expected, timeout=3.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        response = client.get(f'/api/jobs/{job_id}/')
        last = response.json()['status']
        if last == expected:
            return True
        time.sleep(0.02)
    return False


def test_create_booking_returns_job_id_and_job_becomes_done(client, resource):
    response = create_booking(client, resource, 'ok@example.com')

    assert response.status_code == 201
    body = response.json()
    assert body['booking']['client_email'] == 'ok@example.com'
    assert body['job_id']
    assert wait_for_job_status(client, body['job_id'], 'done')


def test_unknown_job_returns_404(client, db):
    response = client.get(f'/api/jobs/{uuid.uuid4()}/')

    assert response.status_code == 404


def test_failed_job_does_not_break_http_or_next_job(client, resource):
    failed = create_booking(client, resource, 'fail@example.com')

    assert failed.status_code == 201
    failed_id = failed.json()['job_id']
    assert wait_for_job_status(client, failed_id, 'failed')

    ok = create_booking(client, resource, 'next@example.com')

    assert ok.status_code == 201
    assert wait_for_job_status(client, ok.json()['job_id'], 'done')


def test_invalid_booking_does_not_create_job(client, resource):
    payload = booking_payload('bad@example.com')
    payload['end_time'] = payload['start_time']

    response = client.post(
        f'/api/resources/{resource.id}/bookings/',
        payload,
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'job_id' not in response.json()