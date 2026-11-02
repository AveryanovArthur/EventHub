from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from .models import Booking, Resource


def filter_resources(resource_type_id=None, search=None):
    query = Resource.objects.all()
    if resource_type_id:
        query = query.filter(resource_type_id=resource_type_id)
    if search:
        query = query.filter(Q(name__icontains=search) | Q(description__icontains=search))
    return query


def order_resources(query, sort_by='name', order='asc'):
    sort_field = 'name' if sort_by == 'name' else 'created_at'
    if order == 'desc':
        sort_field = f'-{sort_field}'
    return query.order_by(sort_field, 'id')


def with_booking_count(query):
    bookings = (
        Booking.objects.filter(resource=OuterRef('pk'))
        .order_by()
        .values('resource')
        .annotate(total=Count('pk'))
        .values('total')
    )
    return query.annotate(
        booking_count=Coalesce(Subquery(bookings, output_field=IntegerField()), Value(0))
    )