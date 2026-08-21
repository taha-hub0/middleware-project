
import os
import re
from datetime import datetime, timezone


NOISE_FIELDS = {
    "debug",
    "extra",
    "metadata",
    "raw_message",
    "span_id",
    "trace_id",
}

# Filtre eşiği. Varsayılan WARNING: DEBUG ve INFO gürültü sayılır, WARNING ve üstü işlenir.
# LOG_LEVEL_THRESHOLD ortam değişkeni ile değiştirilebilir (örn. ERROR).
LEVEL_SEVERITY = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}
DEFAULT_LEVEL_THRESHOLD = "WARNING"

# Maskelenecek alan adları. Türkçe karşılıkları da kapsanır, çünkü üretici servisler
# alan adlarını farklı adlandırabiliyor.
NAME_KEYS = ("name", "full_name", "user_name", "isim", "ad_soyad", "customer_name")
EMAIL_KEYS = ("email", "e_mail", "eposta", "mail", "user_email")
PHONE_KEYS = ("phone", "phone_number", "telefon", "gsm", "mobile")
IP_KEYS = ("ip", "ip_address", "client_ip")
IDENTITY_KEYS = ("tc", "tckn", "tckimlik", "identity_number", "national_id")
CARD_KEYS = ("credit_card", "card_number", "card")
THRESHOLD_SEVERITY = LEVEL_SEVERITY.get(
    os.getenv("LOG_LEVEL_THRESHOLD", DEFAULT_LEVEL_THRESHOLD).strip().upper(),
    LEVEL_SEVERITY[DEFAULT_LEVEL_THRESHOLD],
)


def prune_step(record: dict, context: dict) -> dict:
    pruned = dict(record)
    for key in NOISE_FIELDS:
        pruned.pop(key, None)
    return pruned


def log_filter_step(record: dict, context: dict) -> dict | None:
    # Eşiğin altında kalan kayıtlar gürültü sayılıp düşürülür.
    # Seviyesi bilinmeyen veya hiç belirtilmemiş kayıt INFO kabul edilir.
    level = str(record.get("level", "INFO")).upper()
    severity = LEVEL_SEVERITY.get(level, LEVEL_SEVERITY["INFO"])
    if severity < THRESHOLD_SEVERITY:
        return None
    return record


def kvkk_mask_step(record: dict, context: dict) -> dict:
    # İki aşamalı maskeleme:
    # 1) Alan adı bilinen hassas veriler (email, phone, tc, ...) doğrudan maskelenir.
    # 2) Kalan tüm metin değerleri regex ile taranır; böylece `message` gövdesine gömülmüş
    #    veya beklenmedik bir alan adıyla gelen PII de maskesiz çıkmaz.
    masked = dict(record)
    for keys, masker in (
        (NAME_KEYS, _mask_text),
        (EMAIL_KEYS, _mask_email),
        (PHONE_KEYS, _mask_phone),
        (IP_KEYS, _mask_ip),
        (IDENTITY_KEYS, _mask_numeric_id),
        (CARD_KEYS, _mask_credit_card),
    ):
        for key in keys:
            if key in masked:
                masked[key] = masker(masked[key])
                context.setdefault("masked_fields", []).append(key)

    for key, value in masked.items():
        if isinstance(value, str):
            masked[key] = _mask_free_text(value)
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


def _mask_numeric_id(value: object) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return _mask_text(value)
    if len(digits) <= 4:
        return "*" * (len(digits) - 2) + digits[-2:]
    return "*" * (len(digits) - 4) + digits[-4:]


def _mask_credit_card(value: object) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) <= 4:
        return "*" * max(len(digits), 1)
    # show only last 4 digits
    return "*" * (len(digits) - 4) + digits[-4:]


def _mask_ip(value: object) -> str:
    text = str(value)
    parts = text.split(".")
    if len(parts) != 4:
        return _mask_text(text)
    return ".".join(parts[:2] + ["***", "***"])


# Serbest metin içinde geçen PII kalıpları. Sıra önemlidir: daha spesifik kalıplar önce
# uygulanır, böylece bir telefon numarası kart numarası sanılıp yanlış maskelenmez.
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+")
_IPV4_PATTERN = re.compile(r"(?<![\d.])\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?![\d.])")
_PHONE_PATTERN = re.compile(
    r"(?<![\d*])(?:"
    r"\+\d{1,3}[ .()-]?\d(?:[ .()-]?\d){7,13}"      # +90 555 123 45 67
    r"|0\d{3}[ .-]?\d{3}[ .-]?\d{2}[ .-]?\d{2}"     # 0555 123 45 67
    r"|\(\d{3}\)[ .-]?\d{3}[ .-]?\d{4}"            # (555) 123-4567
    r"|\d{3}[.-]\d{3}[.-]\d{4}"                    # 555-123-4567
    r")(?!\d)"
)
# 13-19 haneli kart numarası; araya boşluk veya tire girebilir.
_CARD_PATTERN = re.compile(r"(?<![\d*])\d(?:[ -]?\d){12,18}(?!\d)")
# 11 haneli TC kimlik numarası.
_IDENTITY_PATTERN = re.compile(r"(?<![\d*])\d{11}(?!\d)")

_CONTENT_RULES = (
    (_EMAIL_PATTERN, _mask_email),
    (_IPV4_PATTERN, _mask_ip),
    (_PHONE_PATTERN, _mask_phone),
    (_CARD_PATTERN, _mask_credit_card),
    (_IDENTITY_PATTERN, _mask_numeric_id),
)


def _mask_free_text(value: str) -> str:
    # Zaten maskelenmiş değerler yıldız içerdiği için kalıplara takılmaz; bu sayede
    # fonksiyon idempotenttir ve alan adı maskelemesinin üstüne güvenle uygulanabilir.
    masked = value
    for pattern, masker in _CONTENT_RULES:
        masked = pattern.sub(lambda match: masker(match.group(0)), masked)
    return masked
