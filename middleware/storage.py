
import os
import threading
from datetime import datetime, timezone
from typing import Mapping


class OutputStorage:
    """Çıktı dosyalarını kanal ve güne göre alt klasörlere ayırarak yazar.

    Tek düz klasörde kayıt başına 3 dosya hızla birikiyordu (5000 istek -> 15000
    dosya). Kanala göre ayırmak ayrıca pipeline'daki `routing_step` sonucunun
    çıktıya gerçekten yansımasını sağlar; önceden kanal yalnızca HTTP yanıtında
    geçiyordu.

    Yerleşim: outputs/<kanal>/<YYYY-AA-GG>/data_<request_id>.<format>
    """

    def __init__(self, outputs_dir: str) -> None:
        self.outputs_dir = outputs_dir
        self._lock = threading.Lock()

    def target_dir(self, channel: str) -> str:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return os.path.join(self.outputs_dir, _safe_segment(channel), day)

    def write_all(
        self, contents: Mapping[str, str], request_id: str, channel: str = "general"
    ) -> list[str]:
        directory = self.target_dir(channel)
        os.makedirs(directory, exist_ok=True)
        paths = {
            format_name: os.path.join(directory, f"data_{request_id}.{format_name}")
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


def _safe_segment(value: str) -> str:
    # Kanal adı kayıttan türediği için doğrudan yola konmaz; outputs/ dışına
    # yazılmasını engellemek adına yalnızca güvenli karakterler bırakılır.
    text = os.path.basename(str(value or "")).strip()
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch in {"-", "_"})
    return cleaned or "general"
