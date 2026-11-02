import os
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from events.models import Resource, ResourceType

COVER_URL = '/api/resources/{id}/cover/'


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def resource_type(db):
    return ResourceType.objects.create(name='Hall')


@pytest.fixture
def resource(resource_type):
    return Resource.objects.create(name='Room', price_per_hour=10, resource_type=resource_type)


def image_file(name='cover.png', image_format='PNG', content_type='image/png'):
    buffer = BytesIO()
    Image.new('RGB', (2, 2), 'red').save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def large_png(name='big.png'):
    image = Image.frombytes('RGB', (600, 600), os.urandom(600 * 600 * 3))
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


def upload_cover(client, resource_id, file):
    return client.post(COVER_URL.format(id=resource_id), {'cover_image': file})


def test_list_uses_default_page_size(client, resource_type):
    Resource.objects.bulk_create(
        [Resource(name=f'R{number:02d}', price_per_hour=10, resource_type=resource_type) for number in range(25)]
    )

    body = client.get('/api/resources/').json()

    assert body['page_size'] == 20
    assert len(body['items']) == 20
    assert body['total_count'] == 25


def test_list_caps_page_size_at_100(client, resource):
    assert client.get('/api/resources/?pageSize=500').json()['page_size'] == 100


def test_list_sorts_by_name_descending(client, resource_type):
    for name in ['A', 'B', 'C']:
        Resource.objects.create(name=name, price_per_hour=10, resource_type=resource_type)

    items = client.get('/api/resources/?sortBy=name&order=desc').json()['items']

    assert [item['name'] for item in items] == ['C', 'B', 'A']


def test_list_search_filters_by_name(client, resource_type):
    Resource.objects.create(name='Alpha room', price_per_hour=10, resource_type=resource_type)
    Resource.objects.create(name='Beta desk', price_per_hour=10, resource_type=resource_type)

    items = client.get('/api/resources/?search=alpha').json()['items']

    assert [item['name'] for item in items] == ['Alpha room']


def test_cover_upload_for_missing_resource_returns_404(client, db):
    assert upload_cover(client, 99999, image_file()).status_code == 404


def test_cover_upload_sets_cover(client, resource):
    response = upload_cover(client, resource.id, image_file())

    assert response.status_code == 200
    assert response.json()['cover_image']
    resource.refresh_from_db()
    assert os.path.exists(resource.cover_image.path)


def test_cover_delete_removes_cover(client, resource):
    upload_cover(client, resource.id, image_file())

    response = client.delete(COVER_URL.format(id=resource.id))

    assert response.status_code == 204
    resource.refresh_from_db()
    assert not resource.cover_image


def test_cover_delete_without_cover_returns_204(client, resource):
    assert client.delete(COVER_URL.format(id=resource.id)).status_code == 204


def test_cover_delete_for_missing_resource_returns_404(client, db):
    assert client.delete(COVER_URL.format(id=99999)).status_code == 404


def test_cover_larger_than_limit_returns_400(client, resource, settings):
    settings.MAX_FILE_SIZE_MB = 1

    response = upload_cover(client, resource.id, large_png())

    assert response.status_code == 400
    assert '1 MB' in str(response.json())


def test_cover_with_unsupported_type_returns_400(client, resource):
    response = upload_cover(client, resource.id, image_file('anim.gif', 'GIF', 'image/gif'))

    assert response.status_code == 400


def test_booking_list_for_missing_resource_returns_404(client, db):
    assert client.get('/api/resources/99999/bookings/').status_code == 404


def test_booking_create_for_missing_resource_returns_404(client, db):
    response = client.post('/api/resources/99999/bookings/', {}, content_type='application/json')

    assert response.status_code == 404


def test_invalid_upload_keeps_previous_cover(client, resource):
    upload_cover(client, resource.id, image_file('first.png'))
    resource.refresh_from_db()
    old_path = resource.cover_image.path

    response = upload_cover(client, resource.id, image_file('anim.gif', 'GIF', 'image/gif'))

    assert response.status_code == 400
    resource.refresh_from_db()
    assert resource.cover_image.path == old_path
    assert os.path.exists(old_path)


def test_valid_upload_replaces_previous_cover(client, resource):
    upload_cover(client, resource.id, image_file('first.png'))
    resource.refresh_from_db()
    old_path = resource.cover_image.path

    response = upload_cover(client, resource.id, image_file('second.png'))

    assert response.status_code == 200
    resource.refresh_from_db()
    assert resource.cover_image.path != old_path
    assert os.path.exists(resource.cover_image.path)
    assert not os.path.exists(old_path)