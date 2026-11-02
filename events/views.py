from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser, FormParser
from . import queries
from django.shortcuts import get_object_or_404
from . import background
from . import geocoding
from .models import Resource, Booking
from .serializers import (
    ResourceListSerializer,
    ResourceDetailSerializer,
    ResourceWriteSerializer,
    BookingSerializer,
    CreateBookingSerializer,
    CreateBookingResponseSerializer,
    JobStatusSerializer,
    ResourceCoverUploadSerializer
)

class ResourceListView(APIView):
    @extend_schema(
        summary="Отримати список ресурсів",
        description="Повертає відфільтрований список ресурсів із підтримкою пагінації, сортування та пошуку.",
        parameters=[
            OpenApiParameter('page', int, description='Номер сторінки', required=False),
            OpenApiParameter('pageSize', int, description='Кількість елементів на сторінці', required=False),
            OpenApiParameter('resourceTypeId', int, description='Фільтр за ID типу ресурсу', required=False),
            OpenApiParameter('search', str, description='Пошук за назвою або описом', required=False),
            OpenApiParameter('sortBy', str, description='Поле для сортування (name або created_at)', required=False),
            OpenApiParameter('order', str, description='Напрям сортування (asc або desc)', required=False),
        ],
        responses={200: ResourceListSerializer(many=True)}
    )
    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('pageSize', 20)), 100)

        resource_type_id = request.query_params.get('resourceTypeId')
        search = request.query_params.get('search')
        sort_by = request.query_params.get('sortBy', 'name').lower()
        order = request.query_params.get('order', 'asc').lower()

        filtered = queries.filter_resources(resource_type_id, search)
        total_count = filtered.count()
        ordered = queries.order_resources(filtered, sort_by, order).select_related('resource_type')
        
        start = (page - 1) * page_size
        items = queries.with_booking_count(ordered)[start:start + page_size]

        serializer = ResourceListSerializer(items, many=True, context={'request': request})
        return Response({
            'items': serializer.data,
            'total_count': total_count,
            'page': page,
            'page_size': page_size
        })

    @extend_schema(
        summary="Створити ресурс",
        description="Створює ресурс і намагається отримати координати адреси через зовнішнє геокодування. Якщо сервіс недоступний, ресурс зберігається без координат.",
        request=ResourceWriteSerializer,
        responses={201: ResourceDetailSerializer, 400: dict}
    )
    def post(self, request):
        serializer = ResourceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        coordinates = geocoding.geocode_address(serializer.validated_data.get('address', ''))
        resource = serializer.save(
            latitude=coordinates.latitude if coordinates else None,
            longitude=coordinates.longitude if coordinates else None,
        )
        detail = ResourceDetailSerializer(resource, context={'request': request})
        return Response(detail.data, status=status.HTTP_201_CREATED)

class ResourceDetailView(APIView):
    @extend_schema(
        summary="Отримати деталі ресурсу",
        description="Повертає детальну інформацію про конкретний ресурс разом із вкладеними бронями.",
        responses={200: ResourceDetailSerializer}
    )
    def get(self, request, pk):
        resource = get_object_or_404(
            Resource.objects.select_related('resource_type').prefetch_related('bookings'),
            pk=pk
        )
        serializer = ResourceDetailSerializer(resource, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Оновити ресурс",
        description="Оновлює ресурс. Координати перераховуються лише якщо адреса змінилася.",
        request=ResourceWriteSerializer,
        responses={200: ResourceDetailSerializer, 400: dict, 404: dict}
    )
    def put(self, request, pk):
        resource = get_object_or_404(Resource, pk=pk)
        serializer = ResourceWriteSerializer(resource, data=request.data)
        serializer.is_valid(raise_exception=True)
        new_address = serializer.validated_data.get('address', '')
        extra = {}
        if not geocoding.addresses_match(resource.address, new_address):
            coordinates = geocoding.geocode_address(new_address)
            extra = {
                'latitude': coordinates.latitude if coordinates else None,
                'longitude': coordinates.longitude if coordinates else None,
            }
        resource = serializer.save(**extra)
        detail = ResourceDetailSerializer(resource, context={'request': request})
        return Response(detail.data, status=status.HTTP_200_OK)

class ResourceCoverView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Завантажити або оновити обкладинку",
        description="Завантажує нову обкладинку для вказаного ресурсу.",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'cover_image': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Зображення обкладинки (JPEG або PNG)'
                    }
                },
                'required': ['cover_image']
            }
        },
        responses={200: ResourceDetailSerializer, 400: dict, 404: dict}
    )
    def post(self, request, pk):
        resource = get_object_or_404(
            Resource.objects.select_related('resource_type').prefetch_related('bookings'),
            pk=pk
        )
        if resource.cover_image:
            resource.cover_image.delete(save=False)
        serializer = ResourceCoverUploadSerializer(resource, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            detail_serializer = ResourceDetailSerializer(resource, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Видалити обкладинку",
        description="Видаляє поточну обкладинку ресурсу.",
        responses={204: None, 404: dict}
    )
    def delete(self, request, pk):
        resource = get_object_or_404(Resource, pk=pk)
        if resource.cover_image:
            resource.cover_image.delete(save=True)
            resource.cover_image = None
            resource.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ResourceBookingListCreateView(APIView):
    @extend_schema(
        summary="Отримати список броней ресурсу",
        description="Повертає список усіх бронювань для конкретного ресурсу.",
        responses={200: BookingSerializer(many=True)}
    )
    def get(self, request, resource_id):
        resource = get_object_or_404(Resource, pk=resource_id)
        bookings = resource.bookings.all().order_by('-created_at')
        serializer = BookingSerializer(bookings, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Створити бронювання",
        description="Створює бронювання та ставить підтвердження у фонову чергу. Повертає job_id для перевірки стану.",
        request=CreateBookingSerializer,
        responses={201: CreateBookingResponseSerializer, 400: dict}
    )
    def post(self, request, resource_id):
        resource = get_object_or_404(Resource, pk=resource_id)
        serializer = CreateBookingSerializer(data=request.data)
        if serializer.is_valid():
            booking = serializer.save(resource=resource)
            job_id = background.enqueue_confirmation(booking.client_email)
            return Response(
                {
                    'booking': BookingSerializer(booking, context={'request': request}).data,
                    'job_id': job_id,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class JobStatusView(APIView):
    @extend_schema(
        summary="Отримати стан фонової задачі",
        description="Повертає поточний стан фонової задачі за її ідентифікатором.",
        responses={200: JobStatusSerializer, 404: dict}
    )
    def get(self, request, job_id):
        job_status = background.job_status_store.get_status(job_id)
        if job_status is None:
            raise NotFound(f"Background job with id '{job_id}' does not exist.")
        return Response({'job_id': job_id, 'status': job_status.value})