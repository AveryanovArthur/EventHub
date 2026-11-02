import queue
import threading
import time

import pytest

from events.background import (
    BackgroundTaskQueue,
    BackgroundTaskWorker,
    JobStatus,
    JobStatusStore,
    LoggingBookingConfirmationSender,
    OperationCancelled,
    process_confirmation_job,
)


class RecordingSender:
    def __init__(self):
        self.calls = []

    def send(self, client_email, stop_event):
        self.calls.append(client_email)


class FailingSender:
    def send(self, client_email, stop_event):
        raise RuntimeError('boom')


class CancellingSender:
    def send(self, client_email, stop_event):
        raise OperationCancelled()


def wait_for_status(store, job_id, expected, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if store.get_status(job_id) == expected:
            return True
        time.sleep(0.01)
    return False


def test_queue_returns_same_work_item():
    task_queue = BackgroundTaskQueue(10)
    work_item = lambda stop_event: None

    task_queue.enqueue(work_item)

    assert task_queue.dequeue(timeout=1) is work_item


def test_queue_rejects_non_callable():
    with pytest.raises(TypeError):
        BackgroundTaskQueue(10).enqueue('not callable')


def test_queue_is_bounded():
    task_queue = BackgroundTaskQueue(1)
    task_queue.enqueue(lambda stop_event: None)

    blocked = threading.Event()

    def producer():
        task_queue.enqueue(lambda stop_event: None)
        blocked.set()

    thread = threading.Thread(target=producer, daemon=True)
    thread.start()

    assert not blocked.wait(0.2)
    task_queue.dequeue(timeout=1)
    assert blocked.wait(1)


def test_status_store_lifecycle():
    store = JobStatusStore()
    job_id = store.create_job()

    assert store.get_status(job_id) == JobStatus.PENDING
    store.set_status(job_id, JobStatus.DONE)
    assert store.get_status(job_id) == JobStatus.DONE


def test_status_store_unknown_job_returns_none():
    import uuid

    assert JobStatusStore().get_status(uuid.uuid4()) is None


def test_process_job_success_sets_done():
    store = JobStatusStore()
    sender = RecordingSender()
    job_id = store.create_job()

    process_confirmation_job(job_id, 'a@test.com', store, sender, threading.Event())

    assert store.get_status(job_id) == JobStatus.DONE
    assert sender.calls == ['a@test.com']


def test_process_job_failure_sets_failed_and_reraises():
    store = JobStatusStore()
    job_id = store.create_job()

    with pytest.raises(RuntimeError):
        process_confirmation_job(job_id, 'a@test.com', store, FailingSender(), threading.Event())

    assert store.get_status(job_id) == JobStatus.FAILED


def test_process_job_cancel_sets_cancelled_and_reraises():
    store = JobStatusStore()
    job_id = store.create_job()

    with pytest.raises(OperationCancelled):
        process_confirmation_job(job_id, 'a@test.com', store, CancellingSender(), threading.Event())

    assert store.get_status(job_id) == JobStatus.CANCELLED


def test_real_sender_respects_stop_event(settings):
    settings.CONFIRMATION_DELAY_SECONDS = 2
    stop_event = threading.Event()
    stop_event.set()

    with pytest.raises(OperationCancelled):
        LoggingBookingConfirmationSender().send('a@test.com', stop_event)


def test_simulated_failure_for_fail_prefix(settings):
    settings.CONFIRMATION_SIMULATE_FAILURES = True

    with pytest.raises(RuntimeError):
        LoggingBookingConfirmationSender().send('fail@example.com', threading.Event())


def test_worker_survives_failure_and_processes_next_item():
    store = JobStatusStore()
    task_queue = BackgroundTaskQueue(10)
    worker = BackgroundTaskWorker(task_queue)
    worker.start()
    try:
        failed_id = store.create_job()
        done_id = store.create_job()
        sender = RecordingSender()

        task_queue.enqueue(
            lambda stop_event: process_confirmation_job(
                failed_id, 'fail@test.com', store, FailingSender(), stop_event
            )
        )
        task_queue.enqueue(
            lambda stop_event: process_confirmation_job(
                done_id, 'ok@test.com', store, sender, stop_event
            )
        )

        assert wait_for_status(store, failed_id, JobStatus.FAILED)
        assert wait_for_status(store, done_id, JobStatus.DONE)
        assert worker.is_alive()
    finally:
        worker.stop()
        worker.join(timeout=2)