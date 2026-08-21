# Chain of Responsibility deseninin testleri.
import pytest

from middleware.pipeline import Step, build_chain


def test_adimlar_sirayla_calisir():
    izler: list[str] = []

    def adim(ad: str):
        def handler(record: dict, context: dict) -> dict:
            izler.append(ad)
            return {**record, ad: True}

        return handler

    zincir = build_chain([("bir", adim("bir")), ("iki", adim("iki")), ("uc", adim("uc"))])
    sonuc = zincir.handle({"x": 1}, {})

    assert izler == ["bir", "iki", "uc"]
    assert sonuc == {"x": 1, "bir": True, "iki": True, "uc": True}


def test_none_donen_adim_zinciri_kisa_devre_eder():
    izler: list[str] = []

    def gecen(record: dict, context: dict) -> dict:
        izler.append("gecen")
        return record

    def dusuren(record: dict, context: dict) -> None:
        izler.append("dusuren")
        return None

    def calismamali(record: dict, context: dict) -> dict:
        izler.append("calismamali")
        return record

    zincir = build_chain(
        [("gecen", gecen), ("dusuren", dusuren), ("calismamali", calismamali)]
    )
    context: dict = {}
    sonuc = zincir.handle({"x": 1}, context)

    assert sonuc is None
    assert izler == ["gecen", "dusuren"]
    # Hangi adimin dusurdugu context'e yazilmali; API bunu istemciye rapor ediyor.
    assert context["dropped_by"] == "dusuren"


def test_adimlar_context_uzerinden_haberlesir():
    def yazan(record: dict, context: dict) -> dict:
        context["kanal"] = "kritik"
        return record

    def okuyan(record: dict, context: dict) -> dict:
        return {**record, "kanal": context["kanal"]}

    context: dict = {}
    sonuc = build_chain([("yazan", yazan), ("okuyan", okuyan)]).handle({}, context)
    assert sonuc == {"kanal": "kritik"}


def test_tek_adimli_zincir():
    zincir = build_chain([("tek", lambda r, c: {**r, "ok": True})])
    assert zincir.handle({}, {}) == {"ok": True}


def test_bos_zincir_hata_verir():
    with pytest.raises(ValueError):
        build_chain([])


def test_set_next_sonraki_adimi_dondurur():
    # Akici (fluent) baglama build_chain tarafindan kullaniliyor.
    ilk = Step("ilk", lambda r, c: r)
    ikinci = Step("ikinci", lambda r, c: r)
    assert ilk.set_next(ikinci) is ikinci
