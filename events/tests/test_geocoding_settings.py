import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.base import build_geocoding_settings


@pytest.fixture(autouse=True)
def valid_environment(monkeypatch):
    monkeypatch.setenv('GEOCODING_API_KEY', 'some-key')
    monkeypatch.delenv('GEOCODING_BASE_URL', raising=False)
    monkeypatch.delenv('GEOCODING_TIMEOUT_SECONDS', raising=False)


def test_valid_defaults():
    result = build_geocoding_settings()

    assert result['TIMEOUT_SECONDS'] == 5
    assert result['CACHE_SECONDS'] == 3600
    assert result['NEGATIVE_CACHE_SECONDS'] == 600


def test_missing_api_key_fails(monkeypatch):
    monkeypatch.setenv('GEOCODING_API_KEY', '   ')

    with pytest.raises(ImproperlyConfigured):
        build_geocoding_settings()


@pytest.mark.parametrize('url', ['http://api.geoapify.com/', 'not-a-url', 'https://'])
def test_invalid_base_url_fails(monkeypatch, url):
    monkeypatch.setenv('GEOCODING_BASE_URL', url)

    with pytest.raises(ImproperlyConfigured):
        build_geocoding_settings()


@pytest.mark.parametrize('value', ['0', '61'])
def test_timeout_out_of_range_fails(monkeypatch, value):
    monkeypatch.setenv('GEOCODING_TIMEOUT_SECONDS', value)

    with pytest.raises(ImproperlyConfigured):
        build_geocoding_settings()