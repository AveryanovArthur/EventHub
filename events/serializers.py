from rest_framework import serializers
from django.utils import timezone
from .models import Resource, Booking, ResourceType

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'resource', 'client_name', 'client_email', 'start_time', 'end_time', 'status', 'created_at']
        read_only_fields = ['id', 'created_at', 'status']

class CreateBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['client_name', 'client_email', 'start_time', 'end_time']

        def validate_start_time(self, value):
            if value < timezone.now():
                raise serializers.ValidationError("The start time must be a date in the future.")
            return value

        def validate(self, data):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError({
                "end_time": "End time must be later than start time."
                })
            return data

class ResourceListSerializer(serializers.ModelSerializer):
    resource_type_name = serializers.CharField(source='resource_type.name', read_only=True)
    booking_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'description', 'price_per_hour', 'resource_type', 'resource_type_name', 'booking_count', 'created_at']

class ResourceDetailSerializer(serializers.ModelSerializer):
    resource_type_name = serializers.CharField(source='resource_type.name', read_only=True)
    bookings = BookingSerializer(many=True, read_only=True)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'description', 'price_per_hour', 'resource_type', 'resource_type_name', 'created_at', 'bookings']