# OutputStorage testleri: kanal/gun klasorleme ve yazma butunlugu.
import os
from datetime import datetime, timezone

import pytest

from middleware.storage import OutputStorage, _safe_segment


@pytest.fixture
def depo(tmp_path) -> OutputStorage:
    return OutputStorage(outputs_dir=str(tmp_path))


def _bugun() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def test_dosyalar_kanal_ve_gun_klasorune_yazilir(depo, tmp_path):
    depo.write_all({"json": "{}", "csv": "a\n"}, request_id="abc", channel="critical")
    hedef = tmp_path / "critical" / _bugun()
    assert sorted(p.name for p in hedef.iterdir()) == ["data_abc.csv", "data_abc.json"]


def test_farkli_kanallar_ayri_klasorlere_gider(depo, tmp_path):
    depo.write_all({"json": "{}"}, request_id="a", channel="critical")
    depo.write_all({"json": "{}"}, request_id="b", channel="general")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["critical", "general"]


def test_yazilan_yollar_dondurulur(depo):
    yollar = depo.write_all({"json": "{}"}, request_id="a", channel="general")
    assert len(yollar) == 1 and os.path.exists(yollar[0])


def test_icerik_dogru_yazilir(depo, tmp_path):
    depo.write_all({"json": '{"x": 1}'}, request_id="a", channel="general")
    dosya = tmp_path / "general" / _bugun() / "data_a.json"
    assert dosya.read_text(encoding="utf-8") == '{"x": 1}'


def test_ayni_id_ikinci_kez_yazilamaz(depo):
    depo.write_all({"json": "{}"}, request_id="a", channel="general")
    with pytest.raises(FileExistsError):
        depo.write_all({"json": "{}"}, request_id="a", channel="general")


def test_kismi_yazim_geri_alinir(depo, tmp_path):
    # json zaten varsa, ayni istegin csv'si de diskte kalmamali (butunluk).
    hedef = tmp_path / "general" / _bugun()
    hedef.mkdir(parents=True)
    (hedef / "data_a.json").write_text("onceden var", encoding="utf-8")
    with pytest.raises(FileExistsError):
        depo.write_all({"csv": "a\n", "json": "{}"}, request_id="a", channel="general")
    assert not (hedef / "data_a.csv").exists()


@pytest.mark.parametrize(
    "kanal, beklenen",
    [
        ("critical", "critical"),
        ("general", "general"),
        ("", "general"),
        (None, "general"),
        ("../../kacis", "kacis"),
        ("..", "general"),
        ("kanal/alt", "alt"),
        ("bo$luk ve *", "bolukve"),
    ],
)
def test_kanal_adi_temizlenir(kanal, beklenen):
    # Kanal adi kayittan tureyebilir; outputs/ disina yazmayi denememeli.
    assert _safe_segment(kanal) == beklenen


def test_yol_gecisi_outputs_disina_yazamaz(depo, tmp_path):
    depo.write_all({"json": "{}"}, request_id="a", channel="../../kacis")
    assert not (tmp_path.parent / "kacis").exists()
    assert (tmp_path / "kacis" / _bugun() / "data_a.json").exists()
