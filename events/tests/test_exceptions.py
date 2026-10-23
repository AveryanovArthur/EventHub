import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory
from events.exceptions import NotFoundException, ConflictException, ValidationException
from events.exceptions_handler import custom_exception_handler

@pytest.mark.django_db
class TestCustomExceptionsAndHandler:
    
    def test_not_found_exception_handling(self):
        factory = APIRequestFactory()
        request = factory.get('/')
        exc = NotFoundException("Resource not found")
        response = custom_exception_handler(exc, {'request': request})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['status'] == 404
        assert response.data['title'] == "Resource not found"

    def test_conflict_exception_handling(self):
        factory = APIRequestFactory()
        request = factory.get('/')
        exc = ConflictException("Conflict occurred")
        response = custom_exception_handler(exc, {'request': request})
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['status'] == 409
        assert response.data['title'] == "Resource conflict"

    def test_validation_exception_handling(self):
        factory = APIRequestFactory()
        request = factory.get('/')
        exc = ValidationException("Validation failed")
        response = custom_exception_handler(exc, {'request': request})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.data['status'] == 422
        assert response.data['title'] == "Business rule violation"

    def test_unexpected_exception_handling(self):
        factory = APIRequestFactory()
        request = factory.get('/')
        exc = Exception("Unexpected error")
        response = custom_exception_handler(exc, {'request': request})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['status'] == 500
        assert response.data['title'] == "An unexpected error occurred"