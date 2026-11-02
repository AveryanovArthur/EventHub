from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from events.models import Booking, Resource, ResourceType

TYPE_PREFIX = 'Performance data '
TYPE_COUNT = 10
FIRST_BOOKING = datetime(2030, 1, 1, tzinfo=dt_timezone.utc)


class Command(BaseCommand):
    help = 'Seeds reproducible data for query performance measurements (development only).'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=100000)
        parser.add_argument('--batch-size', type=int, default=2000)
        parser.add_argument('--reset', action='store_true')

    def handle(self, *args, **options):
        if settings.SETTINGS_MODULE != 'config.settings.development':
            raise CommandError('Performance data can be seeded only with config.settings.development.')

        count = options['count']
        batch_size = options['batch_size']
        if count < 1 or batch_size < 1:
            raise CommandError('--count and --batch-size must be positive.')

        existing = ResourceType.objects.filter(name__startswith=TYPE_PREFIX)
        if existing.exists():
            if not options['reset']:
                self.stdout.write('Performance data already exists. Run with --reset to replace it.')
                return
            Resource.objects.filter(resource_type__in=existing).delete()
            existing.delete()

        ResourceType.objects.bulk_create(
            [ResourceType(name=f'{TYPE_PREFIX}{number:02d}') for number in range(1, TYPE_COUNT + 1)]
        )
        types = list(ResourceType.objects.filter(name__startswith=TYPE_PREFIX).order_by('id'))

        for offset in range(0, count, batch_size):
            size = min(batch_size, count - offset)
            resources = [self._build_resource(index, types) for index in range(offset, offset + size)]
            with transaction.atomic():
                Resource.objects.bulk_create(resources)
                bookings = []
                for resource, index in zip(resources, range(offset, offset + size)):
                    if index % 10 == 0:
                        bookings.extend(self._build_bookings(resource, index))
                Booking.objects.bulk_create(bookings)
            self.stdout.write(f'Seeded {offset + size} of {count} performance resources.')

        with connection.cursor() as cursor:
            cursor.execute('ANALYZE')

        ids = ', '.join(str(item.id) for item in types)
        self.stdout.write(self.style.SUCCESS(f'Done. Performance resource type ids: {ids}'))

    def _build_resource(self, index, types):
        return Resource(
            name=f'Performance resource {index + 1:06d}',
            description='Generated data for measuring EventHub database queries.',
            price_per_hour=Decimal('10.00') + (index % 50),
            resource_type=types[index % len(types)],
            address=f'Test venue {(index % 100) + 1:03d}',
        )

    def _build_bookings(self, resource, index):
        start = FIRST_BOOKING + timedelta(hours=index)
        return [
            Booking(
                resource=resource,
                client_name=f'Client {number}',
                client_email=f'client{number}@example.com',
                start_time=start + timedelta(hours=number * 2),
                end_time=start + timedelta(hours=number * 2 + 1),
            )
            for number in range(2)
        ]