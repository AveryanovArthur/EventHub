import atexit
import logging
import queue
import threading
import uuid
from enum import Enum
from functools import partial

from django.conf import settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    DONE = 'done'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class OperationCancelled(Exception):
    pass


class JobStatusStore:
    def __init__(self):
        self._statuses = {}
        self._lock = threading.Lock()

    def create_job(self):
        job_id = uuid.uuid4()
        with self._lock:
            self._statuses[job_id] = JobStatus.PENDING
        return job_id

    def get_status(self, job_id):
        with self._lock:
            return self._statuses.get(job_id)

    def set_status(self, job_id, status):
        with self._lock:
            self._statuses[job_id] = status


class BackgroundTaskQueue:
    def __init__(self, capacity):
        self._queue = queue.Queue(maxsize=capacity)

    def enqueue(self, work_item):
        if not callable(work_item):
            raise TypeError('work_item must be callable')
        self._queue.put(work_item)

    def dequeue(self, timeout):
        return self._queue.get(timeout=timeout)


class LoggingBookingConfirmationSender:
    def send(self, client_email, stop_event):
        logger.info('Sending booking confirmation to %s...', client_email)
        if settings.CONFIRMATION_SIMULATE_FAILURES and client_email.startswith('fail@'):
            raise RuntimeError('Simulated confirmation failure.')
        if stop_event.wait(settings.CONFIRMATION_DELAY_SECONDS):
            raise OperationCancelled()
        logger.info('Booking confirmation sent to %s.', client_email)


def process_confirmation_job(job_id, client_email, status_store, sender, stop_event):
    status_store.set_status(job_id, JobStatus.PROCESSING)
    try:
        sender.send(client_email, stop_event)
        status_store.set_status(job_id, JobStatus.DONE)
    except OperationCancelled:
        status_store.set_status(job_id, JobStatus.CANCELLED)
        raise
    except Exception:
        status_store.set_status(job_id, JobStatus.FAILED)
        raise


class BackgroundTaskWorker(threading.Thread):
    def __init__(self, task_queue):
        super().__init__(name='background-task-worker', daemon=True)
        self._task_queue = task_queue
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            try:
                work_item = self._task_queue.dequeue(timeout=0.5)
            except queue.Empty:
                continue
            try:
                work_item(self.stop_event)
            except OperationCancelled:
                logger.info('A background job was cancelled.')
            except Exception:
                logger.exception('A background job failed.')

    def stop(self):
        self.stop_event.set()


task_queue = BackgroundTaskQueue(settings.BACKGROUND_QUEUE_CAPACITY)
job_status_store = JobStatusStore()
confirmation_sender = LoggingBookingConfirmationSender()

_worker = None
_worker_lock = threading.Lock()


def start_worker():
    global _worker
    with _worker_lock:
        if _worker is not None and _worker.is_alive():
            return _worker
        _worker = BackgroundTaskWorker(task_queue)
        _worker.start()
        atexit.register(_worker.stop)
        return _worker


def enqueue_confirmation(client_email):
    job_id = job_status_store.create_job()
    task_queue.enqueue(
        partial(
            process_confirmation_job,
            job_id,
            client_email,
            job_status_store,
            confirmation_sender,
        )
    )
    return job_id