"""tr-adres: dağınık yazılmış Türkçe adresleri alanlarına ayırır ve standart yazıma çevirir.

    >>> from tr_adres import ayristir, bicimle
    >>> a = ayristir("CAFERAGA MH MODA CD NO 12 DAIRE 3 KADIKOY ISTANBUL")
    >>> a["il"], a["ilce"], a["mahalle"], a["yol"], a["no"]
    ('İstanbul', 'Kadıköy', 'CAFERAGA', 'MODA', '12')
    >>> bicimle(a)
    'Caferaga Mah. Moda Cad. No:12 D:3, Kadıköy/İstanbul'

English field names: ``parse(text)`` or ``ayristir(text, dil="en")``.
"""
from __future__ import annotations

import re

from .ayristirici import ALANLAR, ayristir_tr
from .dil import cevir, dil_denetle, turkceye
from .metin import buyuk_bas, katla
from .sozluk import PLAKA, Sozluk, sozluk_kur, varsayilan

__version__ = "0.1.0"
__all__ = ["ayristir", "bicimle", "parse", "format_address", "ALANLAR", "PLAKA", "Sozluk", "sozluk_kur", "katla", "__version__"]

_KISA = {"mahalle": "Mah.", "sokak": "Sk.", "cadde": "Cad.", "bulvar": "Bulv."}


def ayristir(metin: str, dil: str = "tr", sozluk: Sozluk | None = None) -> dict:
    """Adres metnini alanlara ayırır. Bulunamayan alan None olur.

    dil="tr": il, ilce, mahalle, yol, yol_turu (sokak/cadde/bulvar), ust_yol, no, ic_kapi, kat, bina, posta_kodu, kalan
    dil="en": province, district, neighbourhood, street, street_type (street/avenue/boulevard), parent_street,
              number, unit, floor, building, postcode, unparsed
    """
    return cevir(ayristir_tr(metin, sozluk), dil_denetle(dil))


def parse(text: str, sozluk: Sozluk | None = None) -> dict:
    """English alias: ``ayristir(text, dil="en")``."""
    return ayristir(text, "en", sozluk)


def bicimle(alanlar: dict) -> str:
    """Alanları standart yazıma çevirir: 'Caferağa Mah. Moda Cad. No:12 D:3, Kadıköy/İstanbul 34710'.
    Türkçe ya da İngilizce anahtarlı sözlük kabul eder."""
    s = turkceye(alanlar)
    p = []
    if s.get("mahalle"):
        p.append(f"{buyuk_bas(s['mahalle'])} {_KISA['mahalle']}")
    if s.get("ust_yol"):
        p.append(buyuk_bas(s["ust_yol"]))
    if s.get("yol"):
        ad = s["yol"] if re.fullmatch(r"\d+\.?", s["yol"]) else buyuk_bas(s["yol"])
        p.append(f"{ad} {_KISA.get(s.get('yol_turu') or '', '')}".strip())
    if s.get("bina"):
        p.append(buyuk_bas(s["bina"]))
    if s.get("no"):
        p.append(f"No:{s['no']}")
    if s.get("kat"):
        p.append(f"Kat:{s['kat']}")
    if s.get("ic_kapi"):
        p.append(f"D:{s['ic_kapi']}")
    yer = "/".join(x for x in (s.get("ilce"), s.get("il")) if x)
    out = ", ".join(x for x in (" ".join(p), yer) if x)
    if s.get("posta_kodu"):
        out += f" {s['posta_kodu']}"
    return out


format_address = bicimle
