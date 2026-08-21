# Central logging configuration for the middleware.
# Bu dosya: log dosyalarının yolunu ve FileHandler yapılandırmasını sağlar.
# Diğer modüller (`middleware.observers`) kayıtları buradaki logger aracılığıyla yazar.
import logging
import os
from typing import Optional


def get_logger(name: str, filename: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        path = _build_log_path(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def _build_log_path(filename: str) -> str:
    safe_name = os.path.basename(filename)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    logs_dir = os.path.join(project_root, "logs")
    return os.path.join(logs_dir, safe_name)
