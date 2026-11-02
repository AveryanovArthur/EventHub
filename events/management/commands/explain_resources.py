import statistics
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Count

from events import queries
from events.management.commands.seed_performance_data import TYPE_PREFIX
from events.models import Resource, ResourceType

PAGE_SIZE = 20


class Command(BaseCommand):
    help = 'Prints the query plan and timings for the resource list query.'

    def add_arguments(self, parser):
        parser.add_argument('--type-id', type=int)
        parser.add_argument('--mode', choices=['core', 'legacy', 'current'], default='core')
        parser.add_argument('--repeat', type=int, default=5)

    def handle(self, *args, **options):
        type_id = options['type_id']
        if type_id is None:
            first = ResourceType.objects.filter(name__startswith=TYPE_PREFIX).order_by('id').first()
            if first is None:
                raise CommandError('No performance data found. Run seed_performance_data first.')
            type_id = first.id

        queryset = self._build(options['mode'], type_id)
        self.stdout.write(f'Database: {connection.vendor}')
        self.stdout.write(f'Mode: {options["mode"]}, resource type id: {type_id}')
        self.stdout.write('SQL:')
        self.stdout.write(str(queryset.query))

        timings = []
        for _ in range(options['repeat']):
            started = time.perf_counter()
            list(queryset.all())
            timings.append((time.perf_counter() - started) * 1000)
        self.stdout.write(
            'Timings ms: ' + ', '.join(f'{value:.2f}' for value in timings)
            + f' (median {statistics.median(timings):.2f})'
        )

        if connection.vendor == 'postgresql':
            plan = queryset.explain(analyze=True, buffers=True)
        else:
            plan = queryset.explain()
        self.stdout.write('Plan:')
        self.stdout.write(plan)

    def _build(self, mode, type_id):
        if mode == 'core':
            filtered = queries.filter_resources(type_id)
            return queries.order_resources(filtered).values_list('id', 'name')[:PAGE_SIZE]
        if mode == 'legacy':
            legacy = (
                Resource.objects.select_related('resource_type')
                .annotate(booking_count=Count('bookings'))
                .filter(resource_type_id=type_id)
            )
            return legacy.order_by('name', 'id')[:PAGE_SIZE]
        filtered = queries.filter_resources(type_id)
        ordered = queries.order_resources(filtered).select_related('resource_type')
        return queries.with_booking_count(ordered)[:PAGE_SIZE]