import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config.settings.base import build_databases, build_spectacular_settings, read_max_file_size


def test_openapi_defaults_are_valid(monkeypatch):
    monkeypatch.delenv('OPENAPI_TITLE', raising=False)
    monkeypatch.delenv('OPENAPI_VERSION', raising=False)
    result = build_spectacular_settings()
    assert result['TITLE']
    assert result['VERSION']


def test_openapi_title_from_environment(monkeypatch):
    monkeypatch.setenv('OPENAPI_TITLE', 'Custom API')
    assert build_spectacular_settings()['TITLE'] == 'Custom API'


@pytest.mark.parametrize('name', ['OPENAPI_TITLE', 'OPENAPI_VERSION'])
def test_openapi_empty_value_fails(monkeypatch, name):
    monkeypatch.setenv(name, '   ')
    with pytest.raises(ImproperlyConfigured):
        build_spectacular_settings()


@pytest.mark.parametrize('value', ['0', '101'])
def test_max_file_size_out_of_range_fails(monkeypatch, value):
    monkeypatch.setenv('MAX_FILE_SIZE_MB', value)
    with pytest.raises(ImproperlyConfigured):
        read_max_file_size(5)


def test_max_file_size_environment_overrides_default(monkeypatch):
    monkeypatch.setenv('MAX_FILE_SIZE_MB', '12')
    assert read_max_file_size(5) == 12


def test_missing_database_url_fails_when_required(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', '   ')
    with pytest.raises(ImproperlyConfigured):
        build_databases(required=True)


def test_missing_database_url_falls_back_when_optional(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', '   ')
    assert 'sqlite' in build_databases(required=False)['default']['ENGINE']


def test_swagger_is_disabled_outside_development(client):
    assert settings.ENABLE_API_DOCS is False
    assert client.get('/api/docs/').status_code == 404