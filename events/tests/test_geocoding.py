import json
import socket
import time
import uuid

import pytest
from django.core.cache.backends.locmem import LocMemCache
from werkzeug.wrappers import Response

from events.geocoding import Coordinates, GeoapifyGeocodingService

OK_BODY = {'results': [{'lat': 50.4501, 'lon': 30.5234}]}
EXPECTED = Coordinates(50.4501, 30.5234)


def make_cache():
    return LocMemCache(f'test-{uuid.uuid4()}', {'OPTIONS': {'MAX_ENTRIES': 100}})


def make_service(base_url, timeout=2, cache=None):
    return GeoapifyGeocodingService(
        base_url=base_url,
        api_key='test-key',
        timeout_seconds=timeout,
        cache=cache or make_cache(),
        cache_seconds=3600,
        negative_cache_seconds=600,
        language='uk',
        country_code='ua',
    )


def expected_query(text):
    return {
        'text': text,
        'format': 'json',
        'limit': '1',
        'lang': 'uk',
        'filter': 'countrycode:ua',
        'apiKey': 'test-key',
    }


def stub_success(httpserver, text='Kyiv, Maidan'):
    httpserver.expect_request(
        '/v1/geocode/search',
        method='GET',
        query_string=expected_query(text),
    ).respond_with_json(OK_BODY)


def unused_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def test_success_is_cached_and_address_is_normalized(httpserver):
    stub_success(httpserver)
    service = make_service(httpserver.url_for('/'))

    first = service.geocode(' Kyiv,   Maidan ')
    second = service.geocode('kyiv, maidan')

    assert first == EXPECTED
    assert second == EXPECTED
    assert len(httpserver.log) == 1


def test_cyrillic_address_is_encoded(httpserver):
    text = 'Київ, вул. Хрещатик, 1'
    stub_success(httpserver, text)

    assert make_service(httpserver.url_for('/')).geocode(text) == EXPECTED


def test_empty_results_is_cached_as_negative_result(httpserver):
    httpserver.expect_request('/v1/geocode/search').respond_with_json({'results': []})
    service = make_service(httpserver.url_for('/'))

    assert service.geocode('Nowhere') is None
    assert service.geocode('nowhere') is None
    assert len(httpserver.log) == 1


@pytest.mark.parametrize('code', [429, 503, 401, 500])
def test_failed_http_status_is_not_cached(httpserver, code):
    httpserver.expect_request('/v1/geocode/search').respond_with_data('error', status=code)
    service = make_service(httpserver.url_for('/'))

    assert service.geocode('Kyiv, Maidan') is None

    httpserver.clear()
    stub_success(httpserver)

    assert service.geocode('Kyiv, Maidan') == EXPECTED


def test_invalid_json_is_not_cached(httpserver):
    httpserver.expect_request('/v1/geocode/search').respond_with_data(
        'not json', content_type='application/json'
    )
    service = make_service(httpserver.url_for('/'))

    assert service.geocode('Kyiv, Maidan') is None

    httpserver.clear()
    stub_success(httpserver)

    assert service.geocode('Kyiv, Maidan') == EXPECTED


@pytest.mark.parametrize(
    'payload',
    [
        {'results': 'x'},
        {'results': [{}]},
        {'results': [{'lat': 'abc', 'lon': 30}]},
        {'results': [{'lat': 100, 'lon': 30}]},
        {'results': [{'lat': 50, 'lon': 300}]},
        ['unexpected'],
    ],
)
def test_invalid_payload_is_not_cached(httpserver, payload):
    httpserver.expect_request('/v1/geocode/search').respond_with_json(payload)
    service = make_service(httpserver.url_for('/'))

    assert service.geocode('Kyiv, Maidan') is None

    httpserver.clear()
    stub_success(httpserver)

    assert service.geocode('Kyiv, Maidan') == EXPECTED


def test_timeout_returns_none_and_is_not_cached(httpserver):
    def slow(request):
        time.sleep(0.4)
        return Response(json.dumps(OK_BODY), content_type='application/json')

    httpserver.expect_request('/v1/geocode/search').respond_with_handler(slow)
    cache = make_cache()
    slow_service = make_service(httpserver.url_for('/'), timeout=0.1, cache=cache)

    assert slow_service.geocode('Kyiv, Maidan') is None

    httpserver.clear()
    stub_success(httpserver)
    fast_service = make_service(httpserver.url_for('/'), timeout=3, cache=cache)

    assert fast_service.geocode('Kyiv, Maidan') == EXPECTED


def test_network_error_returns_none():
    service = make_service(f'http://127.0.0.1:{unused_port()}/', timeout=1)

    assert service.geocode('Kyiv, Maidan') is None