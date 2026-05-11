# Processing steps for the middleware pipeline.
from datetime import datetime, timezone


def log_filter_step(record: dict, context: dict) -> dict | None:
    level = str(record.get("level", "INFO")).upper()
    if level == "DEBUG":
        return None
    return record


def kvkk_mask_step(record: dict, context: dict) -> dict:
    masked = dict(record)
    for key in ["name", "full_name", "user_name"]:
        if key in masked:
            masked[key] = _mask_text(masked[key])
    if "email" in masked:
        masked["email"] = _mask_email(masked["email"])
    if "phone" in masked:
        masked["phone"] = _mask_phone(masked["phone"])
    if "ip" in masked:
        masked["ip"] = _mask_ip(masked["ip"])
    return masked


def enrichment_step(record: dict, context: dict) -> dict:
    enriched = dict(record)
    event_type = str(enriched.get("event_type", "")).lower()
    level = str(enriched.get("level", "INFO")).upper()
    if "login_failed" in event_type or level in {"ERROR", "CRITICAL"}:
        category = "security"
    elif "payment" in event_type:
        category = "finance"
    else:
        category = "general"
    enriched["category"] = category
    enriched["processed_at"] = datetime.now(timezone.utc).isoformat()
    return enriched


def routing_step(record: dict, context: dict) -> dict:
    category = record.get("category", "general")
    if category == "security":
        context["channel"] = "critical"
    else:
        context["channel"] = "general"
    return record


def _mask_text(value: object) -> str:
    text = str(value)
    if len(text) <= 1:
        return "*"
    return text[0] + "*" * (len(text) - 1)


def _mask_email(value: object) -> str:
    text = str(value)
    if "@" not in text:
        return _mask_text(text)
    local, domain = text.split("@", 1)
    if not local:
        return "*" + "@" + domain
    return local[0] + "*" * max(len(local) - 1, 1) + "@" + domain


def _mask_phone(value: object) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) <= 2:
        return "*" * max(len(digits), 1)
    return "*" * (len(digits) - 2) + digits[-2:]


def _mask_ip(value: object) -> str:
    text = str(value)
    parts = text.split(".")
    if len(parts) != 4:
        return _mask_text(text)
    return ".".join(parts[:2] + ["***", "***"])
