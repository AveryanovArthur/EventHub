import pytest

from events import geocoding
from events.geocoding import Coordinates
from events.models import Resource, ResourceType


class FakeGeocoder:
    def __init__(self):
        self.calls = []

    def geocode(self, address):
        self.calls.append(address)
        lowered = address.lower()
        if 'kyiv' in lowered:
            return Coordinates(50.4501, 30.5234)
        if 'kharkiv' in lowered:
            return Coordinates(49.9935, 36.2304)
        return None


@pytest.fixture
def geocoder(monkeypatch):
    fake = FakeGeocoder()
    monkeypatch.setattr(geocoding, 'get_geocoding_service', lambda: fake)
    return fake


@pytest.fixture
def resource_type(db):
    return ResourceType.objects.create(name='Hall')


def payload(kind, **overrides):
    data = {
        'name': 'Hall A',
        'description': 'Test',
        'price_per_hour': '25.00',
        'resource_type': kind.id,
        'address': 'Maidan, Kyiv',
    }
    data.update(overrides)
    return data


def create(client, data):
    return client.post('/api/resources/', data, content_type='application/json')


def update(client, resource_id, data):
    return client.put(f'/api/resources/{resource_id}/', data, content_type='application/json')


def test_create_with_known_address_saves_coordinates(client, geocoder, resource_type):
    response = create(client, payload(resource_type))

    assert response.status_code == 201
    body = response.json()
    assert body['latitude'] == 50.4501
    assert body['longitude'] == 30.5234
    saved = Resource.objects.get(pk=body['id'])
    assert saved.latitude == 50.4501
    assert saved.longitude == 30.5234


def test_create_with_unknown_address_saves_null_coordinates(client, geocoder, resource_type):
    response = create(client, payload(resource_type, address='Nowhere'))

    assert response.status_code == 201
    assert response.json()['latitude'] is None
    assert response.json()['longitude'] is None


def test_create_with_unknown_resource_type_does_not_call_geocoder(client, geocoder, resource_type):
    response = create(client, payload(resource_type, resource_type=9999))

    assert response.status_code == 400
    assert geocoder.calls == []
    assert Resource.objects.count() == 0


def test_create_without_address_does_not_call_geocoder(client, geocoder, resource_type):
    data = payload(resource_type)
    del data['address']

    response = create(client, data)

    assert response.status_code == 201
    assert geocoder.calls == []
    assert response.json()['latitude'] is None


def test_update_with_equivalent_address_keeps_coordinates_without_call(client, geocoder, resource_type):
    created = create(client, payload(resource_type)).json()
    assert len(geocoder.calls) == 1

    response = update(
        client,
        created['id'],
        payload(resource_type, name='Renamed', address='  MAIDAN,   kyiv '),
    )

    assert response.status_code == 200
    assert response.json()['name'] == 'Renamed'
    assert response.json()['latitude'] == 50.4501
    assert len(geocoder.calls) == 1


def test_update_with_new_address_replaces_coordinates(client, geocoder, resource_type):
    created = create(client, payload(resource_type)).json()

    response = update(client, created['id'], payload(resource_type, address='Kharkiv, Sumska'))

    assert response.status_code == 200
    assert response.json()['latitude'] == 49.9935
    assert response.json()['longitude'] == 36.2304


def test_update_with_unresolvable_address_clears_old_coordinates(client, geocoder, resource_type):
    created = create(client, payload(resource_type)).json()

    response = update(client, created['id'], payload(resource_type, address='Nowhere'))

    assert response.status_code == 200
    assert response.json()['latitude'] is None
    assert response.json()['longitude'] is None


def test_detail_contains_coordinates(client, geocoder, resource_type):
    created = create(client, payload(resource_type)).json()

    response = client.get(f"/api/resources/{created['id']}/")

    assert response.status_code == 200
    assert response.json()['latitude'] == 50.4501