import functools
import uuid

import bcrypt
from django.conf import settings


def hash_password(password):
    salt = bcrypt.gensalt(rounds=settings.PASSWORD_HASH_ROUNDS)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('ascii')


def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('ascii'))


@functools.lru_cache(maxsize=None)
def dummy_password_hash():
    return hash_password(uuid.uuid4().hex)