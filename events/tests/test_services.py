import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import ValidationError
from events.models import ResourceType, Resource, Booking
from events.serializers import CreateBookingSerializer

@pytest.mark.django_db
class TestBookingValidation:
    
    def test_start_time_in_past_raises_error(self):
        """Перевірка, що дата початку в минулому викликає помилку валідації."""
        past_time = timezone.now() - timedelta(hours=2)
        future_time = timezone.now() + timedelta(hours=2)
        
        data = {
            "client_name": "Test User",
            "client_email": "test@example.com",
            "start_time": past_time,
            "end_time": future_time
        }
        
        serializer = CreateBookingSerializer(data=data)
        assert not serializer.is_valid()
        assert "start_time" in serializer.errors

    def test_end_time_before_start_time_raises_error(self):
        """Перевірка, що час завершення раніше за час початку є невалідним."""
        start_time = timezone.now() + timedelta(hours=2)
        end_time = timezone.now() + timedelta(hours=1)
        
        data = {
            "client_name": "Test User",
            "client_email": "test@example.com",
            "start_time": start_time,
            "end_time": end_time
        }
        
        serializer = CreateBookingSerializer(data=data)
        assert not serializer.is_valid()
        assert "end_time" in serializer.errors