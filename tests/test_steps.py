# Pipeline adimlarinin testleri: filtreleme, KVKK maskeleme, zenginlestirme, yonlendirme.
import pytest

from middleware import steps
from middleware.steps import (
    LEVEL_SEVERITY,
    enrichment_step,
    kvkk_mask_step,
    log_filter_step,
    prune_step,
    routing_step,
)


# --- prune ---------------------------------------------------------------

def test_prune_gurultu_alanlarini_atar():
    kayit = {"level": "ERROR", "trace_id": "abc", "debug": {"x": 1}, "message": "m"}
    assert prune_step(kayit, {}) == {"level": "ERROR", "message": "m"}


def test_prune_orijinal_kaydi_degistirmez():
    kayit = {"level": "ERROR", "trace_id": "abc"}
    prune_step(kayit, {})
    assert "trace_id" in kayit


# --- filtre --------------------------------------------------------------

@pytest.mark.parametrize(
    "seviye, gecmeli",
    [
        ("DEBUG", False),
        ("INFO", False),
        ("WARNING", True),
        ("ERROR", True),
        ("CRITICAL", True),
        ("critical", True),
    ],
)
def test_filtre_varsayilan_esik_warning(seviye, gecmeli):
    sonuc = log_filter_step({"level": seviye}, {})
    assert (sonuc is not None) == gecmeli


def test_filtre_bilinmeyen_ve_eksik_seviyeyi_dusurur():
    assert log_filter_step({"level": "TRACE"}, {}) is None
    assert log_filter_step({}, {}) is None


def test_filtre_esigi_yapilandirilabilir(monkeypatch):
    monkeypatch.setattr(steps, "THRESHOLD_SEVERITY", LEVEL_SEVERITY["ERROR"])
    assert log_filter_step({"level": "WARNING"}, {}) is None
    assert log_filter_step({"level": "ERROR"}, {}) is not None

    monkeypatch.setattr(steps, "THRESHOLD_SEVERITY", LEVEL_SEVERITY["DEBUG"])
    assert log_filter_step({"level": "DEBUG"}, {}) is not None


# --- KVKK maskeleme ------------------------------------------------------

def test_maskeleme_bilinen_alanlari_kapatir():
    kayit = {
        "user_name": "Ahmet Yilmaz",
        "email": "ahmet@firma.com",
        "phone": "05551234567",
        "ip": "88.230.44.12",
        "tc": "12345678901",
        "credit_card": "4111111111111111",
    }
    m = kvkk_mask_step(kayit, {})
    for anahtar, ham in kayit.items():
        assert m[anahtar] != ham, f"{anahtar} maskelenmemis"
    assert m["email"].endswith("@firma.com")
    assert m["ip"].startswith("88.230.")
    assert m["credit_card"].endswith("1111")


def test_maskeleme_turkce_alan_adlarini_da_kapsar():
    m = kvkk_mask_step(
        {"isim": "Ayse Kaya", "eposta": "a@b.com", "telefon": "05551234567", "tckn": "98765432109"},
        {},
    )
    assert m["isim"].startswith("A") and "*" in m["isim"]
    assert m["eposta"].endswith("@b.com") and "*" in m["eposta"]
    assert "*" in m["telefon"]
    assert m["tckn"].endswith("2109") and "*" in m["tckn"]


@pytest.mark.parametrize(
    "metin, sizmamali",
    [
        ("Kullanici ahmet.yilmaz@firma.com.tr giris denedi", "ahmet.yilmaz@firma.com.tr"),
        ("TC 12345678901 ile kayit acildi", "12345678901"),
        ("Odeme 4111 1111 1111 1111 karti ile alindi", "4111 1111 1111 1111"),
        ("Iade: 5500-0000-0000-0004", "5500-0000-0000-0004"),
        ("192.168.1.55 adresinden istek geldi", "192.168.1.55"),
        ("0532 123 45 67 numarasi arandi", "0532 123 45 67"),
    ],
)
def test_maskeleme_message_govdesindeki_pii_yi_yakalar(metin, sizmamali):
    # Alan adi bazli maskeleme yetmez: PII serbest metne gomulu de gelebilir.
    m = kvkk_mask_step({"message": metin}, {})
    assert sizmamali not in m["message"]
    assert "*" in m["message"]


@pytest.mark.parametrize(
    "zararsiz",
    [
        "Siparis 12345 tutari 250.50 TL",
        "3 adet urun, 2 gun icinde teslim",
        "2026-08-21T11:10:24.833938+00:00",
        "surum 1.2.3 yayinlandi",
    ],
)
def test_maskeleme_yanlis_pozitif_uretmez(zararsiz):
    assert kvkk_mask_step({"message": zararsiz}, {})["message"] == zararsiz


def test_maskeleme_idempotent():
    kayit = {"email": "x@y.com", "message": "TC 12345678901 ve mail z@w.com"}
    bir = kvkk_mask_step(kayit, {})
    iki = kvkk_mask_step(bir, {})
    assert bir == iki


def test_maskeleme_orijinal_kaydi_degistirmez():
    kayit = {"email": "a@b.com"}
    kvkk_mask_step(kayit, {})
    assert kayit["email"] == "a@b.com"


def test_maskeleme_hangi_alanlari_kapattigini_bildirir():
    context: dict = {}
    kvkk_mask_step({"email": "a@b.com", "tc": "12345678901"}, context)
    assert set(context["masked_fields"]) == {"email", "tc"}


# --- zenginlestirme ve yonlendirme ---------------------------------------

@pytest.mark.parametrize(
    "kayit, beklenen",
    [
        ({"event_type": "login_failed", "level": "ERROR"}, "security"),
        ({"event_type": "logout", "level": "CRITICAL"}, "security"),
        ({"event_type": "payment", "level": "WARNING"}, "finance"),
        ({"event_type": "logout", "level": "WARNING"}, "general"),
    ],
)
def test_zenginlestirme_kategori_atar(kayit, beklenen):
    assert enrichment_step(kayit, {})["category"] == beklenen


def test_zenginlestirme_islenme_zamani_ekler():
    assert "processed_at" in enrichment_step({"level": "ERROR"}, {})


@pytest.mark.parametrize(
    "kategori, kanal",
    [("security", "critical"), ("finance", "general"), ("general", "general")],
)
def test_yonlendirme_kanali_context_e_yazar(kategori, kanal):
    context: dict = {}
    routing_step({"category": kategori}, context)
    assert context["channel"] == kanal
