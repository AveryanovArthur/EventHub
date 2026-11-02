import uuid

from django.db import models


class UserRole(models.TextChoices):
    ATTENDEE = 'Attendee', 'Attendee'
    ORGANIZER = 'Organizer', 'Organizer'
    ADMIN = 'Admin', 'Admin'


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=320, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=80, blank=True, default='')
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class UserRoleAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=20, choices=UserRole.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'role'], name='uq_user_role'),
        ]

    def __str__(self):
        return f'{self.user_id}: {self.role}'