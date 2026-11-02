from django.conf import settings
from rest_framework import serializers
from django.utils import timezone
from .models import Resource, Booking, ResourceType

BYTES_IN_MEGABYTE = 1024 * 1024
ALLOWED_COVER_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/jpg')

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'resource', 'client_name', 'client_email', 'start_time', 'end_time', 'status', 'created_at']
        read_only_fields = ['id', 'created_at', 'status']

class CreateBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['client_name', 'client_email', 'start_time', 'end_time']
        extra_kwargs = {
            'client_name': {'help_text': 'Повне ім`я клієнта, що бронює ресурс.'},
            'client_email': {'help_text': 'Електронна пошта для сповіщень.'},
            'start_time': {'help_text': 'Дата та час початку бронювання (UTC).'},
            'end_time': {'help_text': 'Дата та час завершення бронювання (UTC).'},
        }

    def validate_start_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("The start time must be a date in the future.")
        return value

    def validate(self, data):
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError({
                    "end_time": "End time must be later than start time."
                })
        return data

class CreateBookingResponseSerializer(serializers.Serializer):
    booking = BookingSerializer()
    job_id = serializers.UUIDField()

class JobStatusSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=['pending', 'processing', 'done', 'failed', 'cancelled'])

class ResourceListSerializer(serializers.ModelSerializer):
    resource_type_name = serializers.CharField(source='resource_type.name', read_only=True)
    booking_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'description', 'price_per_hour', 'resource_type', 'resource_type_name', 'address', 'latitude', 'longitude', 'booking_count', 'cover_image', 'created_at']

class ResourceDetailSerializer(serializers.ModelSerializer):
    resource_type_name = serializers.CharField(source='resource_type.name', read_only=True)
    bookings = BookingSerializer(many=True, read_only=True)

    class Meta:
        model = Resource
        fields = ['id', 'name', 'description', 'price_per_hour', 'resource_type', 'resource_type_name', 'address', 'latitude', 'longitude', 'cover_image', 'created_at', 'bookings']

class ResourceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['name', 'description', 'price_per_hour', 'resource_type', 'address']

class ResourceCoverUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['cover_image']
        extra_kwargs = {
            'cover_image': {'required': True, 'help_text': 'Зображення обкладинки (JPEG або PNG).'}
        }

    def validate_cover_image(self, value):
        if not value:
            raise serializers.ValidationError("File cannot be empty.")
        max_size_mb = settings.MAX_FILE_SIZE_MB
        if value.size > max_size_mb * BYTES_IN_MEGABYTE:
            raise serializers.ValidationError(f"The cover image must not exceed {max_size_mb} MB.")

        if hasattr(value, 'content_type') and value.content_type not in ALLOWED_COVER_CONTENT_TYPES:
            raise serializers.ValidationError("Only JPEG and PNG cover images are supported.")

        return value