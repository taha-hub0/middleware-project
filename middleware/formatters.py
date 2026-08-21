#formatterfactory pattern
import csv
import html
import io
import json


class JsonFormatter:
    def format(self, record: dict) -> str:
        return json.dumps(record, ensure_ascii=False)


class CsvFormatter:
    def format(self, record: dict) -> str:
        buffer = io.StringIO()
        fieldnames = list(record.keys())
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(record)
        return buffer.getvalue()


class HtmlFormatter:
    def format(self, record: dict) -> str:
        # Anahtar ve değerler kaçırılmadan gömülürse, log içeriğindeki `<script>` gibi
        # işaretleme çıktı dosyasında çalıştırılabilir hale gelir (HTML injection).
        rows = "".join(
            f"<tr><td>{html.escape(str(key))}</td><td>{html.escape(str(value))}</td></tr>"
            for key, value in record.items()
        )
        return f"<table>{rows}</table>"


class FormatterFactory:
    def create(self, name: str):
        key = name.lower()
        if key == "json":
            return JsonFormatter()
        if key == "csv":
            return CsvFormatter()
        if key == "html":
            return HtmlFormatter()
        raise ValueError(f"Unknown format: {name}")
