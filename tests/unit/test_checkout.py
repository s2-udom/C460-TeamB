from datetime import UTC, datetime, timedelta

from app.routes.checkout import _hold_is_active


def test_hold_is_active_for_future_timestamp():
    now = datetime.now(UTC)

    assert _hold_is_active(now + timedelta(minutes=1), now)


def test_hold_is_inactive_for_expired_timestamp():
    now = datetime.now(UTC)

    assert not _hold_is_active(now - timedelta(seconds=1), now)


def test_naive_database_timestamp_is_treated_as_utc():
    now = datetime.now(UTC)
    naive_future = (now + timedelta(minutes=1)).replace(tzinfo=None)

    assert _hold_is_active(naive_future, now)
