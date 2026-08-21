# Observer Pattern testleri.
import logging

import pytest

from middleware import logger as logger_modulu
from middleware import observers
from middleware.observers import (
    CriticalLogObserver,
    EventDispatcher,
    NormalLogObserver,
    Observer,
    _level_from_event,
)


class KaydedenObserver(Observer):
    def __init__(self) -> None:
        self.olaylar: list[dict] = []

    def notify(self, event: dict) -> None:
        self.olaylar.append(event)


@pytest.fixture
def izole_logger(monkeypatch):
    """Observer'lari gercek logs/ klasorune yazmadan kurar.

    get_logger dosya handler'i acar; testte bunun yerine caplog'un yakalayabilecegi
    handler'siz bir logger dondururuz.
    """
    istenen_dosyalar: dict[str, str] = {}

    def sahte_get_logger(name: str, filename: str, level: int = logging.INFO):
        istenen_dosyalar[name] = filename
        test_logger = logging.getLogger(f"test.{name}")
        test_logger.handlers.clear()
        test_logger.setLevel(logging.DEBUG)
        test_logger.propagate = True
        return test_logger

    monkeypatch.setattr(observers, "get_logger", sahte_get_logger)
    return istenen_dosyalar


# --- dispatcher ----------------------------------------------------------

def test_dispatcher_tum_observerlara_haber_verir():
    birinci, ikinci = KaydedenObserver(), KaydedenObserver()
    EventDispatcher([birinci, ikinci]).notify({"type": "received"})
    assert birinci.olaylar == [{"type": "received"}]
    assert ikinci.olaylar == [{"type": "received"}]


def test_dispatcher_observersiz_calisir():
    EventDispatcher([]).notify({"type": "received"})  # hata vermemeli


def test_observer_taban_sinifi_uygulanmali():
    with pytest.raises(NotImplementedError):
        Observer().notify({})


# --- observer davranisi --------------------------------------------------

def test_normal_observer_her_seviyeyi_yazar(izole_logger, caplog):
    gozlemci = NormalLogObserver()
    with caplog.at_level(logging.DEBUG, logger="test.middleware.normal"):
        for seviye in ["INFO", "WARNING", "ERROR", "CRITICAL"]:
            gozlemci.notify({"type": "received", "level": seviye, "message": "m"})
    assert [k.levelname for k in caplog.records] == [
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]


def test_critical_observer_sadece_kritikleri_yazar(izole_logger, caplog):
    gozlemci = CriticalLogObserver()
    with caplog.at_level(logging.DEBUG, logger="test.middleware.critical"):
        for seviye in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            gozlemci.notify({"type": "received", "level": seviye, "message": "m"})
    # Sadece ERROR ve CRITICAL kritik log dosyasina dusmeli.
    assert [k.levelname for k in caplog.records] == ["ERROR", "CRITICAL"]


def test_observerlar_ayri_dosyalara_yazar(izole_logger):
    NormalLogObserver()
    CriticalLogObserver()
    assert izole_logger["middleware.normal"] == "middleware.log"
    assert izole_logger["middleware.critical"] == "critical.log"


def test_olay_mesaji_tur_ve_metni_birlestirir(izole_logger, caplog):
    gozlemci = NormalLogObserver()
    with caplog.at_level(logging.DEBUG, logger="test.middleware.normal"):
        gozlemci.notify({"type": "error", "level": "CRITICAL", "message": "patladi"})
    assert caplog.records[0].getMessage() == "error | patladi"


@pytest.mark.parametrize(
    "olay, beklenen",
    [
        ({"level": "TRACE"}, logging.INFO),
        ({}, logging.INFO),
        ({"level": "critical"}, logging.CRITICAL),
        ({"level": "ERROR"}, logging.ERROR),
    ],
)
def test_seviye_cozumleme(olay, beklenen):
    assert _level_from_event(olay) == beklenen


# --- log yolu ------------------------------------------------------------

def test_log_yolu_dosya_adini_temizler():
    # Disaridan gelen bir ad logs/ disina yazamamali (path traversal).
    yol = logger_modulu._build_log_path("../../gizli.log")
    assert yol.endswith("gizli.log")
    assert "logs" in yol
    assert ".." not in yol
