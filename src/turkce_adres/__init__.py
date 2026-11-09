"""turkce-adres: dağınık yazılmış Türkçe adresleri alanlarına ayırır, standart yazıma çevirir, mahalle düzeyinde
internetsiz konum verir, iki adresin aynı olup olmadığını söyler ve KVKK için genelleştirir.

    >>> from turkce_adres import ayristir, bicimle
    >>> a = ayristir("CAFERAGA MH MODA CD NO 12 DAIRE 3 KADIKOY ISTANBUL")
    >>> a["il"], a["ilce"], a["no"], a["ic_kapi"]
    ('İstanbul', 'Kadıköy', '12', '3')

English field names: ``parse(text)`` or ``ayristir(text, dil="en")``.
"""
from __future__ import annotations

import re

from .ayristirici import ALANLAR, EK_ALANLAR, ayristir_tr
from .dil import cevir, dil_denetle, turkceye
from .metin import buyuk_bas, katla
from .sozluk import PLAKA, Sozluk, sozluk_kur, varsayilan

__version__ = "0.2.0"
__all__ = ["ayristir", "bicimle", "parse", "format_address", "konum", "geocode", "benzerlik", "ayni_mi", "same_address",
           "similarity", "genellestir", "generalise", "eksikler", "missing", "ALANLAR", "PLAKA", "Sozluk", "sozluk_kur",
           "katla", "__version__"]

_KISA = {"mahalle": "Mah.", "sokak": "Sk.", "cadde": "Cad.", "bulvar": "Bulv.", "cikmaz": "Çıkmazı", "meydan": "Meydanı",
         "yol": "Yolu"}
_RESMI = {"mahalle": "Mahallesi", "sokak": "Sokak", "cadde": "Caddesi", "bulvar": "Bulvarı", "cikmaz": "Çıkmazı",
          "meydan": "Meydanı", "yol": "Yolu"}


_BINA_TAM = {"sit": "Sitesi", "apt": "Apt.", "ap": "Apt.", "is mrk": "İş Merkezi"}
_BINA_AC = re.compile(r"\b(Sit|Apt|Ap)\.?$")


def ayristir(metin: str, dil: str = "tr", sozluk: Sozluk | None = None, duzelt: bool = True) -> dict:
    """Adres metnini alanlara ayırır. Bulunamayan alan None olur.

    dil="tr": il, ilce, mahalle, koy, yol, yol_turu (sokak/cadde/bulvar/cikmaz/meydan/yol), ust_yol, no, ic_kapi,
              kat, blok, bina, posta_kodu, tarif ("Migros karşısı" gibi), kalan, guven (0-1), notlar
    dil="en": province, district, neighbourhood, village, street, street_type, parent_street, number, unit, floor,
              block, building, postcode, landmark, unparsed, confidence, notes
    duzelt=True: il/ilçe/mahalle sözlükteki yazımla, ASCII yazılmış sözcükler Türkçe harfleriyle döner.
    """
    return cevir(ayristir_tr(metin, sozluk, duzelt), dil_denetle(dil))


def parse(text: str, sozluk: Sozluk | None = None, fix: bool = True) -> dict:
    """English alias: ``ayristir(text, dil="en")``."""
    return ayristir(text, "en", sozluk, fix)


def _yol_yaz(s: dict, tablo: dict) -> str | None:
    if not s.get("yol"):
        return None
    ad = s["yol"] if re.fullmatch(r"[\d/]+\.?", s["yol"]) else buyuk_bas(s["yol"])
    return f"{ad} {tablo.get(s.get('yol_turu') or '', '')}".strip()


def bicimle(alanlar: dict, bicim: str = "kargo") -> str:
    """Alanları standart yazıma çevirir. Türkçe ya da İngilizce anahtarlı sözlük ya da adres metni kabul eder.

    bicim="kargo": 'Caferağa Mah. Moda Cad. No:12 D:3, Kadıköy/İstanbul 34710'
    bicim="resmi": 'Caferağa Mahallesi Moda Caddesi Dış Kapı No: 12 İç Kapı No: 3, Kadıköy/İSTANBUL 34710'
    """
    s = turkceye(ayristir(alanlar) if isinstance(alanlar, str) else alanlar)
    resmi = bicim == "resmi"
    tablo = _RESMI if resmi else _KISA
    p = []
    if s.get("mahalle"):
        p.append(f"{buyuk_bas(s['mahalle'])} {tablo['mahalle']}")
    if s.get("koy"):
        p.append(f"{buyuk_bas(s['koy'])} Köyü")
    if s.get("ust_yol"):
        p.append(buyuk_bas(s["ust_yol"]))
    y = _yol_yaz(s, tablo)
    if y:
        p.append(y)
    if s.get("bina"):
        p.append(_BINA_AC.sub(lambda m: _BINA_TAM[katla(m.group(1))], buyuk_bas(s["bina"])))
    if s.get("blok"):
        p.append(f"{s['blok']} Blok")
    no, ic = s.get("no"), s.get("ic_kapi")
    if no and ic and no.endswith(f"/{ic}"):
        no = no[: -len(ic) - 1]
    if no:
        p.append(f"Dış Kapı No: {no}" if resmi else f"No:{no}")
    if s.get("kat"):
        p.append(f"Kat: {s['kat']}" if resmi else f"Kat:{s['kat']}")
    if ic:
        p.append(f"İç Kapı No: {ic}" if resmi else f"D:{ic}")
    il = s.get("il")
    if il and resmi:
        il = il.replace("i", "İ").upper() if il else il
    yer = "/".join(x for x in (s.get("ilce"), il) if x)
    out = ", ".join(x for x in (" ".join(p), yer) if x)
    if s.get("posta_kodu"):
        out += f" {s['posta_kodu']}"
    return out


format_address = bicimle

from .ozellik import ayni_mi, benzerlik, eksikler, genellestir, konum  # noqa: E402

geocode = konum
similarity = benzerlik
same_address = ayni_mi
generalise = genellestir
missing = eksikler
