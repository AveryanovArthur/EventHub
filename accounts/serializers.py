import re

from rest_framework import serializers

from .models import User

PASSWORD_ERROR_MESSAGE = (
    'Password must contain 8 to 72 characters, using only A-Z, a-z and 0-9, '
    'with at least one uppercase letter, one lowercase letter and one digit.'
)


def validate_password_format(value):
    if (
        not re.fullmatch(r'[A-Za-z0-9]{8,72}', value)
        or not re.search(r'[A-Z]', value)
        or not re.search(r'[a-z]', value)
        or not re.search(r'[0-9]', value)
    ):
        raise serializers.ValidationError(PASSWORD_ERROR_MESSAGE)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=320)
    password = serializers.CharField(write_only=True, trim_whitespace=False, validators=[validate_password_format])
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    display_name = serializers.CharField(max_length=80, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=320)
    password = serializers.CharField(write_only=True, trim_whitespace=False, validators=[validate_password_format])


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'display_name', 'roles']

    def get_roles(self, user):
        return sorted(assignment.role for assignment in user.roles.all())

    def get_display_name(self, user):
        return user.display_name or f'{user.first_name} {user.last_name}'