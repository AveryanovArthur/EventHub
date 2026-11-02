from rest_framework import status
from rest_framework.exceptions import APIException


class EmailAlreadyRegistered(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'An account with this email already exists.'
    default_code = 'email_already_registered'


class InvalidCredentials(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid email or password.'
    default_code = 'invalid_credentials'