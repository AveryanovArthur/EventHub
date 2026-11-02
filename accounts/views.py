from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(APIView):
    authentication_classes = []

    @extend_schema(
        summary="Зареєструвати користувача",
        description="Створює обліковий запис із роллю Attendee.",
        request=RegisterSerializer,
        responses={201: UserSerializer, 400: dict, 409: dict}
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = []

    @extend_schema(
        summary="Перевірити облікові дані",
        description="Перевіряє email і пароль та повертає профіль. Токен або сесія поки не видаються.",
        request=LoginSerializer,
        responses={200: UserSerializer, 400: dict, 401: dict}
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.authenticate_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)