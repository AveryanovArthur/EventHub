import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from events.models import ResourceType, Resource, Booking

@pytest.mark.django_db
class TestResourceBookingAPI:

    @pytest.fixture(autouse=True)
    def setup_resources(self):
        self.resource_type = ResourceType.objects.create(name="Meeting Room")
        self.resource = Resource.objects.create(
            name="Conference Room A",
            description="Big room",
            price_per_hour=50.00,
            resource_type=self.resource_type
        )
        self.url = f"/api/resources/{self.resource.id}/bookings/"

    def test_create_booking_success(self, client):
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)
        
        payload = {
            "client_name": "Alex",
            "client_email": "alex@test.com",
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        }

        response = client.post(self.url, payload, content_type='application/json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["booking"]["client_name"] == "Alex"
        assert response.data["job_id"]
        assert Booking.objects.count() == 1
        assert Booking.objects.first().resource == self.resource

    def test_create_booking_invalid_dates_fails(self, client):
        start = timezone.now() - timedelta(days=1)
        end = start - timedelta(hours=2)
        
        payload = {
            "client_name": "Alex",
            "client_email": "alex@test.com",
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        }

        response = client.post(self.url, payload, content_type='application/json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Booking.objects.count() == 0

    def test_resource_detail_success(self, client):
        url = f"/api/resources/{self.resource.id}/"
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Conference Room A"

    def test_resource_detail_not_found(self, client):
        url = "/api/resources/99999/"
        response = client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND