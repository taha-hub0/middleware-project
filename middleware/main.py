# Middleware API: receive logs and run the processing pipeline.
import uuid
from fastapi import FastAPI

from middleware.formatters import FormatterFactory
from middleware.observers import CriticalLogObserver, EventDispatcher, NormalLogObserver
from middleware.pipeline import build_chain
from middleware.steps import (
    enrichment_step,
    kvkk_mask_step,
    log_filter_step,
    routing_step,
)
from middleware.storage import OutputStorage

app = FastAPI()

dispatcher = EventDispatcher([NormalLogObserver(), CriticalLogObserver()])
pipeline = build_chain(
    [
        ("log_filter", log_filter_step),
        ("kvkk_mask", kvkk_mask_step),
        ("enrichment", enrichment_step),
        ("routing", routing_step),
    ]
)
formatter_factory = FormatterFactory()
storage = OutputStorage(outputs_dir="outputs")


@app.post("/logs")
def receive_log(payload: dict) -> dict:
    context: dict = {}
    dispatcher.notify(
        {
            "type": "received",
            "level": payload.get("level", "INFO"),
            "message": "Log received",
            "record": payload,
        }
    )
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
    formats = ["json", "csv", "html"]
    formatted_by_format = {}
    for format_name in formats:
        formatter = formatter_factory.create(format_name)
        formatted_by_format[format_name] = formatter.format(processed)

    last_error: FileExistsError | None = None
    request_id = ""
    for _ in range(3):
        request_id = str(uuid.uuid4())
        try:
            storage.write_all(formatted_by_format, request_id=request_id)
            last_error = None
            break
        except FileExistsError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    dispatcher.notify(
        {
            "type": "processed",
            "level": processed.get("level", "INFO"),
            "message": "Record processed",
            "record": processed,
            "context": context,
        }
    )
    return {"status": "ok", "channel": channel, "formats": formats}
