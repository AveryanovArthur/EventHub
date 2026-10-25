from django.urls import path
from .views import (
    ResourceListView,
    ResourceDetailView,
    ResourceCoverView,
    ResourceBookingListCreateView,
)

urlpatterns = [
    path('resources/', ResourceListView.as_view(), name='resource-list'),
    path('resources/<int:pk>/', ResourceDetailView.as_view(), name='resource-detail'),
    path('resources/<int:pk>/cover/', ResourceCoverView.as_view(), name='resource-cover'),
    path('resources/<int:resource_id>/bookings/', ResourceBookingListCreateView.as_view(), name='resource-bookings'),
]