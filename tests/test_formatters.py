# Factory Pattern ve formatlayicilarin testleri.
import csv
import io
import json

import pytest

from middleware.formatters import (
    CsvFormatter,
    FormatterFactory,
    HtmlFormatter,
    JsonFormatter,
)


@pytest.fixture
def factory() -> FormatterFactory:
    return FormatterFactory()


@pytest.mark.parametrize(
    "ad, beklenen",
    [
        ("json", JsonFormatter),
        ("csv", CsvFormatter),
        ("html", HtmlFormatter),
        ("JSON", JsonFormatter),
        ("Html", HtmlFormatter),
    ],
)
def test_factory_dogru_formatlayiciyi_uretir(factory, ad, beklenen):
    assert isinstance(factory.create(ad), beklenen)


def test_factory_bilinmeyen_formatta_hata_verir(factory):
    with pytest.raises(ValueError):
        factory.create("xml")


def test_json_turkce_karakterleri_bozmaz(factory):
    kayit = {"isim": "Ayşe Çağrı", "level": "ERROR"}
    assert json.loads(factory.create("json").format(kayit)) == kayit


def test_csv_baslik_ve_satir_uretir(factory):
    kayit = {"a": "1", "b": "2"}
    satirlar = list(csv.reader(io.StringIO(factory.create("csv").format(kayit))))
    assert satirlar[0] == ["a", "b"]
    assert satirlar[1] == ["1", "2"]


def test_html_tablo_uretir(factory):
    cikti = factory.create("html").format({"level": "ERROR"})
    assert cikti.startswith("<table>") and cikti.endswith("</table>")
    assert "<td>level</td><td>ERROR</td>" in cikti


@pytest.mark.parametrize(
    "kotu_deger",
    [
        "<script>alert('XSS')</script>",
        '" onmouseover="alert(1)',
        "<img src=x onerror=alert(1)>",
    ],
)
def test_html_degerleri_kacirir(factory, kotu_deger):
    # HTML injection: log icerigi cikti dosyasinda calistirilabilir olmamali.
    cikti = factory.create("html").format({"message": kotu_deger})
    assert kotu_deger not in cikti
    assert "<script>" not in cikti
    assert "onerror=alert(1)>" not in cikti


def test_html_anahtarlari_da_kacirir(factory):
    # Alan adlari da dis kaynaktan geliyor, onlar da kacirilmali.
    cikti = factory.create("html").format({"<img src=x onerror=alert(1)>": "deger"})
    assert "<img" not in cikti
    assert "&lt;img" in cikti


def test_html_zararsiz_metni_korur(factory):
    cikti = factory.create("html").format({"note": "5 < 10 & 10 > 5"})
    assert "5 &lt; 10 &amp; 10 &gt; 5" in cikti
