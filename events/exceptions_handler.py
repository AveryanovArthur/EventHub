from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from .exceptions import NotFoundException, ConflictException, ValidationException

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, NotFoundException):
        return Response({
            "title": "Resource not found",
            "status": 404,
            "detail": str(exc)
        }, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, ConflictException):
        return Response({
            "title": "Resource conflict",
            "status": 409,
            "detail": str(exc)
        }, status=status.HTTP_409_CONFLICT)

    if isinstance(exc, ValidationException):
        return Response({
            "title": "Business rule violation",
            "status": 422,
            "detail": str(exc)
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    if response is None:
        return Response({
            "title": "An unexpected error occurred",
            "status": 500,
            "detail": "The server could not complete the request."
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response