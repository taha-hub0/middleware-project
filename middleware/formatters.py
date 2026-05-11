# Factory Pattern: JSON/CSV/HTML formatter seçim ve üretimini merkezileştirir.
import csv
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
        rows = "".join(
            f"<tr><td>{key}</td><td>{value}</td></tr>" for key, value in record.items()
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
