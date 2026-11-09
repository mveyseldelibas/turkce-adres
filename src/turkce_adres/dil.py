"""Türkçe/İngilizce alan adları, değerleri ve not metinleri."""
from __future__ import annotations

ALAN_EN = {
    "il": "province",
    "ilce": "district",
    "mahalle": "neighbourhood",
    "koy": "village",
    "yol": "street",
    "yol_turu": "street_type",
    "ust_yol": "parent_street",
    "no": "number",
    "ic_kapi": "unit",
    "kat": "floor",
    "blok": "block",
    "bina": "building",
    "posta_kodu": "postcode",
    "tarif": "landmark",
    "kalan": "unparsed",
    "guven": "confidence",
    "notlar": "notes",
}
EN_ALAN = {v: k for k, v in ALAN_EN.items()}
YOL_TURU_EN = {"sokak": "street", "cadde": "avenue", "bulvar": "boulevard", "cikmaz": "dead_end", "meydan": "square", "yol": "road"}
EN_YOL_TURU = {v: k for k, v in YOL_TURU_EN.items()}
DILLER = ("tr", "en")


def dil_denetle(dil: str) -> str:
    d = (dil or "tr").lower()
    if d not in DILLER:
        raise ValueError(f"dil 'tr' ya da 'en' olmalı / lang must be 'tr' or 'en': {dil!r}")
    return d


def notlari_yaz(notlar: list, dil: str) -> list[str]:
    from .ayristirici import NOT
    i = 0 if dil == "tr" else 1
    return [NOT[kod][i].format(**arg) for kod, arg in notlar]


def cevir(s: dict, dil: str) -> dict:
    """Türkçe anahtarlı sonucu istenen dile çevirir; not kodlarını o dilde metne çevirir."""
    dil = dil_denetle(dil)
    s = dict(s)
    if isinstance(s.get("notlar"), list):
        s["notlar"] = notlari_yaz(s["notlar"], dil)
    if dil == "tr":
        return s
    out = {ALAN_EN.get(k, k): v for k, v in s.items()}
    if out.get("street_type"):
        out["street_type"] = YOL_TURU_EN.get(out["street_type"], out["street_type"])
    return out


def turkceye(s: dict) -> dict:
    """İki dildeki anahtarları da kabul eder, Türkçeye çevirir."""
    out = {EN_ALAN.get(k, k): v for k, v in s.items()}
    if out.get("yol_turu") in EN_YOL_TURU:
        out["yol_turu"] = EN_YOL_TURU[out["yol_turu"]]
    return out
