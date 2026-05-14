"""
Structured audit logging.
ISO 27001 A.12.4 — Logging and monitoring.
ISO 27001 A.12.4.1 — Event logging.
ISO 27001 A.12.4.3 — Administrator and operator logs.

Every security-relevant event (auth, access, data change) is emitted as a
structured JSON log entry to stdout so a SIEM (Elastic, Splunk, etc.) can
ingest it without parsing.
"""
import structlog
from enum import StrEnum

log = structlog.get_logger("audit")


class AuditEvent(StrEnum):
    LOGIN_SUCCESS  = "auth.login.success"
    LOGIN_FAILURE  = "auth.login.failure"
    LOGOUT         = "auth.logout"
    TOKEN_REFRESH  = "auth.token.refresh"
    ACCESS_DENIED  = "authz.access.denied"
    ORDER_SENT     = "trading.order.sent"
    ORDER_CANCEL   = "trading.order.cancel"
    USER_CREATED   = "admin.user.created"
    USER_DELETED   = "admin.user.deleted"
    CONFIG_CHANGED = "admin.config.changed"


def audit_log(
    event: AuditEvent,
    subject: str | None = None,
    ip: str | None = None,
    detail: str | None = None,
    **extra,
) -> None:
    log.info(
        event,
        subject=subject,
        ip=ip,
        detail=detail,
        **extra,
    )
