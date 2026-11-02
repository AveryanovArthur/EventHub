import hashlib
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float


class GeocodingService(ABC):
    @abstractmethod
    def geocode(self, address):
        ...


@dataclass(frozen=True)
class _Lookup:
    coordinates: Coordinates | None
    should_cache: bool


_TRANSIENT_FAILURE = _Lookup(None, False)


def collapse_whitespace(address):
    return ' '.join(address.split())


def normalize_address(address):
    return collapse_whitespace(address).casefold()


def addresses_match(first, second):
    return normalize_address(first or '') == normalize_address(second or '')


def _read_coordinates(result):
    if not isinstance(result, dict):
        return None
    try:
        latitude = float(result['lat'])
        longitude = float(result['lon'])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return Coordinates(latitude, longitude)


class GeoapifyGeocodingService(GeocodingService):
    def __init__(
        self,
        base_url,
        api_key,
        timeout_seconds,
        cache,
        cache_seconds,
        negative_cache_seconds,
        language='uk',
        country_code='ua',
        session=None,
    ):
        self._endpoint = urljoin(base_url, 'v1/geocode/search')
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._cache = cache
        self._cache_seconds = cache_seconds
        self._negative_cache_seconds = negative_cache_seconds
        self._language = language
        self._country_code = country_code
        self._session = session or requests.Session()
        self._session.headers['User-Agent'] = 'EventHub/1.0'

    def geocode(self, address):
        collapsed = collapse_whitespace(address)
        cache_key = self._cache_key(collapsed.casefold())

        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached[0]

        lookup = self._request_coordinates(collapsed)
        if lookup.should_cache:
            self._store(cache_key, lookup.coordinates)
        return lookup.coordinates

    def _cache_key(self, normalized_address):
        digest = hashlib.sha256(normalized_address.encode('utf-8')).hexdigest()
        return f'geocoding:{digest}'

    def _store(self, cache_key, coordinates):
        timeout = self._negative_cache_seconds if coordinates is None else self._cache_seconds
        self._cache.set(cache_key, (coordinates,), timeout=timeout)

    def _request_coordinates(self, address):
        params = {
            'text': address,
            'format': 'json',
            'limit': 1,
            'lang': self._language,
            'filter': f'countrycode:{self._country_code}',
            'apiKey': self._api_key,
        }
        logger.info('Sending Geoapify geocoding request.')
        try:
            response = self._session.get(
                self._endpoint,
                params=params,
                timeout=self._timeout_seconds,
            )
        except requests.Timeout:
            logger.warning('Geoapify geocoding timed out.')
            return _TRANSIENT_FAILURE
        except requests.RequestException as exception:
            logger.warning('Geoapify geocoding is unavailable (%s).', type(exception).__name__)
            return _TRANSIENT_FAILURE
        return self._read_response(response)

    def _read_response(self, response):
        if response.status_code == 429:
            logger.warning('Geoapify rate limit was exceeded.')
            return _TRANSIENT_FAILURE
        if not response.ok:
            logger.warning('Geoapify failed with HTTP status %s.', response.status_code)
            return _TRANSIENT_FAILURE
        try:
            payload = response.json()
        except ValueError:
            logger.warning('Geoapify returned invalid JSON.')
            return _TRANSIENT_FAILURE
        return self._parse_payload(payload)

    def _parse_payload(self, payload):
        results = payload.get('results') if isinstance(payload, dict) else None
        if not isinstance(results, list):
            logger.warning('Geoapify returned an unexpected response shape.')
            return _TRANSIENT_FAILURE
        if not results:
            return _Lookup(None, True)
        coordinates = _read_coordinates(results[0])
        if coordinates is None:
            logger.warning('Geoapify returned invalid coordinates.')
            return _TRANSIENT_FAILURE
        return _Lookup(coordinates, True)


_service = None
_service_lock = threading.Lock()


def get_geocoding_service():
    global _service
    with _service_lock:
        if _service is None:
            config = settings.GEOCODING
            _service = GeoapifyGeocodingService(
                base_url=config['BASE_URL'],
                api_key=config['API_KEY'],
                timeout_seconds=config['TIMEOUT_SECONDS'],
                cache=caches['geocoding'],
                cache_seconds=config['CACHE_SECONDS'],
                negative_cache_seconds=config['NEGATIVE_CACHE_SECONDS'],
                language=config['LANGUAGE'],
                country_code=config['COUNTRY_CODE'],
            )
        return _service


def geocode_address(address):
    if not address or not address.strip():
        return None
    return get_geocoding_service().geocode(address)