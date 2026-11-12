"""Prometheus metrics, exposed at GET /metrics.

Automatic (from prometheus-flask-exporter):
  flask_http_request_total{method,status,url_rule}        request count / traffic / 4xx-5xx
  flask_http_request_duration_seconds{method,status,url_rule}  latency histogram (p95)
  flask_http_request_exceptions_total                     unhandled exceptions
  process_* / python_*                                     CPU, memory, GC

Custom (ticketing_*): business and database metrics defined below.
"""
import time
from datetime import datetime, timezone

from flask import request
from prometheus_client import Counter, Gauge, Histogram
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import and_, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

# group_by="url_rule" labels requests by route pattern ("/api/v1/events/<int:event_id>/seats")
# instead of the real URL, so each event id doesn't create a new time series.
metrics = PrometheusMetrics.for_app_factory(
    group_by="url_rule",
    excluded_paths=["/metrics"],
)

# --- Business metrics -------------------------------------------------------
TICKETS_SOLD = Counter(
    "ticketing_tickets_sold",
    "Tickets sold (increments when checkout creates tickets).",
)
CHECKOUT_REQUESTS = Counter(
    "ticketing_checkout_requests",
    "Checkout attempts received.",
)
CHECKOUT_FAILURES = Counter(
    "ticketing_checkout_failures",
    "Checkout attempts rejected, by reason.",
    ["reason"],
)
SEAT_HOLDS = Counter(
    "ticketing_seat_holds",
    "Seats successfully put on hold.",
)
HOLD_REQUESTS = Counter(
    "ticketing_hold_requests",
    "Hold requests received.",
)
HOLD_FAILURES = Counter(
    "ticketing_hold_failures",
    "Hold requests that failed, by reason.",
    ["reason"],
)
HOLD_FAILURE_REASONS = ("invalid_request", "event_not_found", "not_on_sale", "seats_unavailable")
for _reason in HOLD_FAILURE_REASONS:
    HOLD_FAILURES.labels(reason=_reason)  # show every reason as 0 from the start

SEATS_HELD = Gauge(
    "ticketing_seats_held",
    "Seats currently on hold (hold not yet expired).",
)
HOLDS_EXPIRED = Gauge(
    "ticketing_holds_expired",
    "Seats whose hold has expired but are still marked held in the database.",
)
SEATS_AVAILABLE = Gauge(
    "ticketing_seats_available",
    "Seats currently available across all events.",
)
SEATS_SOLD = Gauge(
    "ticketing_seats_sold",
    "Seats sold across all events.",
)

# --- Database metrics -------------------------------------------------------
DB_QUERY_DURATION = Histogram(
    "ticketing_db_query_duration_seconds",
    "Time taken by database queries.",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
DB_UP = Gauge(
    "ticketing_db_up",
    "1 if the database answered the last /metrics scrape, otherwise 0.",
)
DB_POOL_CHECKED_OUT = Gauge(
    "ticketing_db_pool_connections_in_use",
    "Database connections currently checked out of the pool.",
)
DB_POOL_CAPACITY = Gauge(
    "ticketing_db_pool_connections_capacity",
    "Maximum database connections available to the application pool.",
)

_db_listeners_added = False


def _add_db_timing_listeners():
    """Time every SQL query. Added once per process, for all engines."""
    global _db_listeners_added
    if _db_listeners_added:
        return

    @event.listens_for(Engine, "before_cursor_execute")
    def _start_timer(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_times", []).append(time.perf_counter())

    @event.listens_for(Engine, "after_cursor_execute")
    def _stop_timer(conn, cursor, statement, parameters, context, executemany):
        started = conn.info["query_start_times"].pop()
        DB_QUERY_DURATION.observe(time.perf_counter() - started)

    _db_listeners_added = True


def _refresh_seat_gauges():
    """Count seats by state. Runs only when Prometheus scrapes /metrics."""
    from app.models import EventSeat

    now = datetime.now(timezone.utc)
    try:
        held = EventSeat.status == "held"
        not_expired = EventSeat.hold_expires_at > now
        counts = db.session.execute(
            select(
                func.count().filter(and_(held, not_expired)),
                func.count().filter(and_(held, ~not_expired)),
                func.count().filter(EventSeat.status == "available"),
                func.count().filter(EventSeat.status == "sold"),
            )
        ).one()
        SEATS_HELD.set(counts[0])
        HOLDS_EXPIRED.set(counts[1])
        SEATS_AVAILABLE.set(counts[2])
        SEATS_SOLD.set(counts[3])
        DB_UP.set(1)
    except SQLAlchemyError:
        db.session.rollback()
        DB_UP.set(0)
    finally:
        db.session.remove()

    try:
        pool = db.engine.pool
        DB_POOL_CHECKED_OUT.set(pool.checkedout())
        pool_size = getattr(pool, "size", lambda: 0)()
        max_overflow = getattr(pool, "_max_overflow", 0)
        DB_POOL_CAPACITY.set(pool_size + max_overflow)
    except (AttributeError, SQLAlchemyError):
        DB_POOL_CAPACITY.set(0)  # some pool types do not expose pool sizing


def init_metrics(app):
    """Attach /metrics and the database timing to the app."""
    if not app.config.get("METRICS_ENABLED", True):
        return

    metrics.init_app(app)
    _add_db_timing_listeners()

    @app.before_request
    def _update_gauges_before_scrape():
        if request.path == "/metrics":
            _refresh_seat_gauges()
