import uuid
from fastapi import FastAPI, Response

from middleware.formatters import FormatterFactory
from middleware.observers import CriticalLogObserver, EventDispatcher, NormalLogObserver
from middleware.pipeline import build_chain
from middleware.steps import (
    enrichment_step,
    kvkk_mask_step,
    log_filter_step,
    prune_step,
    routing_step,
)
from middleware.storage import OutputStorage

app = FastAPI()

dispatcher = EventDispatcher([NormalLogObserver(), CriticalLogObserver()])
pipeline = build_chain(
    [
        ("prune", prune_step),
        ("log_filter", log_filter_step),
        ("kvkk_mask", kvkk_mask_step), 
        ("enrichment", enrichment_step),
        ("routing", routing_step),
    ]
)
formatter_factory = FormatterFactory()
storage = OutputStorage(outputs_dir="outputs")


def _formats_for_role(role: str | None) -> list[str]:
    normalized_role = str(role or "").strip().lower().replace(" ", "_")
    if normalized_role in {"system_admin", "admin", "system-admin"}:
        return ["html", "csv", "json"]
    if normalized_role in {"cybersec", "cyber_security", "security"}:
        return ["json", "html", "csv"]
    if normalized_role in {"web_dev", "webdev", "developer"}:
        return ["csv", "html", "json"]
    return ["html", "csv", "json"]


@app.post("/logs")
def receive_log(payload: dict, response: Response) -> dict:
    context: dict = {}
    dispatcher.notify(
        {
            "type": "received",
            "level": payload.get("level", "INFO"),
            "message": "Log received",
            "record": payload,
        }
    )
    try:
        return _process(payload, context)
    except Exception as exc:
        # Hata yakalanmazsa kayıt sessizce kaybolur ve hiçbir yere iz düşmez.
        # Bu yüzden önce kritik olay olarak loglanır, sonra istemciye 500 döner.
        dispatcher.notify(
            {
                "type": "error",
                "level": "CRITICAL",
                "message": f"Record processing failed: {type(exc).__name__}: {exc}",
                "record": payload,
                "context": context,
            }
        )
        response.status_code = 500
        # Yanıtta yalnızca hata türü paylaşılır. Exception mesajı kaydın kendisinden
        # maskelenmemiş veri taşıyabileceği için sadece log dosyasına yazılır.
        return {"status": "error", "error": type(exc).__name__}


def _process(payload: dict, context: dict) -> dict:
    processed = pipeline.handle(payload, context)
    if processed is None:
        dispatcher.notify(
            {
                "type": "dropped",
                "level": payload.get("level", "INFO"),
                "message": "Record dropped by filter",
                "record": payload,
                "context": context,
            }
        )
        return {"status": "dropped", "reason": context.get("dropped_by")}

    channel = context.get("channel", "general")
    role = payload.get("role") or payload.get("user_role") or payload.get("recipient_role")
    formats = _formats_for_role(role)
    formatted_by_format = {}
    for format_name in formats:
        formatter = formatter_factory.create(format_name)
        formatted_by_format[format_name] = formatter.format(processed)

    # uuid4 çakışması pratikte imkânsız; olası bir FileExistsError yukarıdaki
    # hata yakalayıcıya düşer ve kritik olay olarak loglanır.
    request_id = str(uuid.uuid4())
    storage.write_all(formatted_by_format, request_id=request_id, channel=channel)

    dispatcher.notify(
        {
            "type": "processed",
            "level": processed.get("level", "INFO"),
            "message": "Record processed",
            "record": processed,
            "context": context,
        }
    )
    result = {"status": "ok", "channel": channel, "formats": formats}
    if role is not None:
        result["role"] = role
    return result
