# Observer Pattern: log olaylarını dinleyip farklı hedeflere yazmak için kullanılır.
import logging
from typing import Iterable

from middleware.logger import get_logger


class EventDispatcher:
    def __init__(self, observers: Iterable["Observer"]) -> None:
        self._observers = list(observers)

    def notify(self, event: dict) -> None:
        for observer in self._observers:
            observer.notify(event)


class Observer:
    def notify(self, event: dict) -> None:
        raise NotImplementedError


class NormalLogObserver(Observer):
    def __init__(self, filename: str = "middleware.log") -> None:
        self._logger = get_logger("middleware.normal", filename)

    def notify(self, event: dict) -> None:
        level = _level_from_event(event)
        message = _format_event(event)
        self._logger.log(level, message)


class CriticalLogObserver(Observer):
    def __init__(self, filename: str = "critical.log") -> None:
        self._logger = get_logger("middleware.critical", filename)

    def notify(self, event: dict) -> None:
        level_name = str(event.get("level", "INFO")).upper()
        if level_name in {"ERROR", "CRITICAL"}:
            level = _level_from_event(event)
            message = _format_event(event)
            self._logger.log(level, message)


def _level_from_event(event: dict) -> int:
    level_name = str(event.get("level", "INFO")).upper()
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }.get(level_name, logging.INFO)


def _format_event(event: dict) -> str:
    event_type = event.get("type", "event")
    message = event.get("message", "")
    return f"{event_type} | {message}"
