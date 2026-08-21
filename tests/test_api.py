# /logs endpoint'inin uctan uca testleri.
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from middleware import main
from middleware.observers import Observer


class KaydedenObserver(Observer):
    def __init__(self) -> None:
        self.olaylar: list[dict] = []

    def notify(self, event: dict) -> None:
        self.olaylar.append(event)


@pytest.fixture
def gozlemci(monkeypatch) -> KaydedenObserver:
    # Testler gercek logs/ klasorune yazmasin; olaylari bellekte topla.
    kaydeden = KaydedenObserver()
    monkeypatch.setattr(main, "dispatcher", main.EventDispatcher([kaydeden]))
    return kaydeden


@pytest.fixture
def cikti_dizini(monkeypatch, tmp_path):
    # Testler gercek outputs/ klasorunu kirletmesin.
    monkeypatch.setattr(main.storage, "outputs_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(gozlemci, cikti_dizini) -> TestClient:
    return TestClient(main.app)


def _cikti_dosyalari(kok) -> list:
    # Cikti artik outputs/<kanal>/<gun>/ altinda; duz listeleme yetmez.
    return sorted(kok.rglob("data_*.*"))


def _kayit(**ek) -> dict:
    temel = {"level": "ERROR", "event_type": "login_failed", "role": "cybersec"}
    temel.update(ek)
    return temel


def test_islenen_kayit_ok_doner(client):
    yanit = client.post("/logs", json=_kayit())
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["status"] == "ok"
    assert govde["channel"] == "critical"
    assert govde["role"] == "cybersec"


def test_islenen_kayit_uc_dosya_yazar(client, cikti_dizini):
    client.post("/logs", json=_kayit())
    uzantilar = sorted(p.suffix for p in _cikti_dosyalari(cikti_dizini))
    assert uzantilar == [".csv", ".html", ".json"]


def test_cikti_kanal_ve_gun_klasorune_yazilir(client, cikti_dizini):
    # routing_step'in hesapladigi kanal artik cikti yoluna yansiyor.
    client.post("/logs", json=_kayit(level="ERROR"))          # -> security -> critical
    client.post("/logs", json=_kayit(level="WARNING", event_type="payment"))  # -> finance -> general

    kanallar = sorted(p.name for p in cikti_dizini.iterdir())
    assert kanallar == ["critical", "general"]

    gun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for kanal in kanallar:
        assert (cikti_dizini / kanal / gun).is_dir()
        assert len(list((cikti_dizini / kanal / gun).iterdir())) == 3


def test_bilinmeyen_kanal_general_e_duser(client, cikti_dizini):
    # routing_step calismadan yazilirsa varsayilan kanal kullanilir.
    main.storage.write_all({"json": "{}"}, request_id="x")
    assert (cikti_dizini / "general").is_dir()


@pytest.mark.parametrize(
    "rol, beklenen_sira",
    [
        ("system_admin", ["html", "csv", "json"]),
        ("cybersec", ["json", "html", "csv"]),
        ("web_dev", ["csv", "html", "json"]),
        ("bilinmeyen", ["html", "csv", "json"]),
    ],
)
def test_format_sirasi_role_gore_degisir(client, rol, beklenen_sira):
    yanit = client.post("/logs", json=_kayit(role=rol))
    assert yanit.json()["formats"] == beklenen_sira


def test_filtrelenen_kayit_dropped_doner(client, cikti_dizini):
    yanit = client.post("/logs", json=_kayit(level="INFO"))
    assert yanit.status_code == 200
    assert yanit.json() == {"status": "dropped", "reason": "log_filter"}
    # Dusurulen kayit diske yazilmamali.
    assert list(cikti_dizini.iterdir()) == []


def test_pii_diske_maskelenmis_yazilir(client, cikti_dizini):
    client.post(
        "/logs",
        json=_kayit(
            email="ahmet@firma.com",
            message="TC 12345678901 ile 4111111111111111 kartindan odeme",
        ),
    )
    json_dosya = next(p for p in _cikti_dosyalari(cikti_dizini) if p.suffix == ".json")
    icerik = json_dosya.read_text(encoding="utf-8")
    for ham in ["ahmet@firma.com", "12345678901", "4111111111111111"]:
        assert ham not in icerik, f"{ham} maskelenmeden diske yazilmis"


def test_html_ciktisi_kacirilmis_yazilir(client, cikti_dizini):
    client.post("/logs", json=_kayit(message="<script>alert(1)</script>"))
    html_dosya = next(p for p in _cikti_dosyalari(cikti_dizini) if p.suffix == ".html")
    icerik = html_dosya.read_text(encoding="utf-8")
    assert "<script>" not in icerik
    assert "&lt;script&gt;" in icerik


def test_olaylar_yayinlanir(client, gozlemci):
    client.post("/logs", json=_kayit())
    assert [o["type"] for o in gozlemci.olaylar] == ["received", "processed"]


def test_dusurulen_kayit_icin_dropped_olayi_yayinlanir(client, gozlemci):
    client.post("/logs", json=_kayit(level="INFO"))
    assert [o["type"] for o in gozlemci.olaylar] == ["received", "dropped"]


# --- hata yolu -----------------------------------------------------------

@pytest.fixture
def bozuk_depolama(monkeypatch):
    def patla(*args, **kwargs):
        raise OSError("disk dolu: /outputs/data_x.json")

    monkeypatch.setattr(main.storage, "write_all", patla)


def test_isleme_hatasi_500_ve_hata_turu_doner(client, bozuk_depolama):
    yanit = client.post("/logs", json=_kayit())
    assert yanit.status_code == 500
    assert yanit.json() == {"status": "error", "error": "OSError"}


def test_isleme_hatasi_kritik_olay_olarak_loglanir(client, gozlemci, bozuk_depolama):
    client.post("/logs", json=_kayit())
    hatalar = [o for o in gozlemci.olaylar if o["type"] == "error"]
    assert len(hatalar) == 1, "hata sessizce kaybolmus"
    # CRITICAL oldugu icin critical.log'a da dusecek.
    assert hatalar[0]["level"] == "CRITICAL"
    assert "OSError" in hatalar[0]["message"]
    assert "disk dolu" in hatalar[0]["message"]


def test_hata_yanitinda_exception_detayi_sizmaz(client, bozuk_depolama):
    # Exception mesaji kaydin kendisinden maskelenmemis veri tasiyabilir; yanitta olmamali.
    yanit = client.post("/logs", json=_kayit())
    assert "disk dolu" not in yanit.text
    assert "/outputs/" not in yanit.text


def test_gecersiz_govde_422_doner(client):
    assert client.post("/logs", json=["liste", "degil", "sozluk"]).status_code == 422
