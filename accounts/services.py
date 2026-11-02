from django.db import IntegrityError, transaction

from .exceptions import EmailAlreadyRegistered, InvalidCredentials
from .models import User, UserRole, UserRoleAssignment
from .passwords import dummy_password_hash, hash_password, verify_password


def normalize_email(email):
    return email.strip().lower()


def email_exists(email):
    return User.objects.filter(email=email).exists()


def register_user(email, password, first_name, last_name, display_name=''):
    normalized_email = normalize_email(email)
    if email_exists(normalized_email):
        raise EmailAlreadyRegistered()

    password_hash = hash_password(password)
    try:
        with transaction.atomic():
            user = User.objects.create(
                email=normalized_email,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                display_name=display_name.strip(),
                password_hash=password_hash,
            )
            UserRoleAssignment.objects.create(user=user, role=UserRole.ATTENDEE)
    except IntegrityError:
        if email_exists(normalized_email):
            raise EmailAlreadyRegistered()
        raise
    return user


def authenticate_user(email, password):
    user = User.objects.prefetch_related('roles').filter(email=normalize_email(email)).first()
    stored_hash = user.password_hash if user else dummy_password_hash()
    password_matches = verify_password(password, stored_hash)
    if user is None or not password_matches:
        raise InvalidCredentials()
    return user