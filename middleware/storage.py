# Output storage helper that writes files to disk.
import os
import threading
from typing import Mapping


class OutputStorage:
    def __init__(self, outputs_dir: str) -> None:
        self.outputs_dir = outputs_dir
        self._lock = threading.Lock()

    def write_all(self, contents: Mapping[str, str], request_id: str) -> list[str]:
        os.makedirs(self.outputs_dir, exist_ok=True)
        paths = {
            format_name: os.path.join(
                self.outputs_dir, f"data_{request_id}.{format_name}"
            )
            for format_name in contents.keys()
        }
        with self._lock:
            for path in paths.values():
                if os.path.exists(path):
                    raise FileExistsError(f"File already exists: {path}")
            written: list[str] = []
            try:
                for format_name, path in paths.items():
                    with open(path, "x", encoding="utf-8") as handle:
                        handle.write(contents[format_name])
                    written.append(path)
            except FileExistsError:
                for path in written:
                    try:
                        os.remove(path)
                    except FileNotFoundError:
                        pass
                raise
        return list(paths.values())
