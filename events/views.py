from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from .models import Resource, Booking
from .serializers import (
    ResourceListSerializer,
    ResourceDetailSerializer,
    BookingSerializer,
    CreateBookingSerializer
)

class ResourceListView(APIView):
    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('pageSize', 20)), 100)
        
        resource_type_id = request.query_params.get('resourceTypeId')
        search = request.query_params.get('search')
        sort_by = request.query_params.get('sortBy', 'name').lower()
        order = request.query_params.get('order', 'asc').lower()

        query = Resource.objects.select_related('resource_type').annotate(booking_count=Count('bookings'))

        if resource_type_id:
            query = query.filter(resource_type_id=resource_type_id)

        if search:
            query = query.filter(Q(name__icontains=search) | Q(description__icontains=search))

        sort_field = 'name' if sort_by == 'name' else 'created_at'
        if order == 'desc':
            sort_field = f'-{sort_field}'

        query = query.order_by(sort_field, 'id')

        total_count = query.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = query[start:end]

        serializer = ResourceListSerializer(items, many=True)
        return Response({
            'items': serializer.data,
            'total_count': total_count,
            'page': page,
            'page_size': page_size
        })

class ResourceDetailView(APIView):
    def get(self, request, pk):
        resource = get_object_or_404(
            Resource.objects.select_related('resource_type').prefetch_related('bookings'),
            pk=pk
        )
        serializer = ResourceDetailSerializer(resource)
        return Response(serializer.data)

class ResourceBookingListCreateView(APIView):
    def get(self, request, resource_id):
        resource = get_object_or_404(Resource, pk=resource_id)
        bookings = resource.bookings.all().order_by('-created_at')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

    def post(self, request, resource_id):
        resource = get_object_or_404(Resource, pk=resource_id)
        serializer = CreateBookingSerializer(data=request.data)
        if serializer.is_valid():
            booking = serializer.save(resource=resource)
            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)