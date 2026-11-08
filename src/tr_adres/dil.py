"""Türkçe/İngilizce alan adları ve değerleri."""
from __future__ import annotations

ALAN_EN = {
    "il": "province",
    "ilce": "district",
    "mahalle": "neighbourhood",
    "yol": "street",
    "yol_turu": "street_type",
    "ust_yol": "parent_street",
    "no": "number",
    "ic_kapi": "unit",
    "kat": "floor",
    "bina": "building",
    "posta_kodu": "postcode",
    "kalan": "unparsed",
}
EN_ALAN = {v: k for k, v in ALAN_EN.items()}
YOL_TURU_EN = {"sokak": "street", "cadde": "avenue", "bulvar": "boulevard"}
EN_YOL_TURU = {v: k for k, v in YOL_TURU_EN.items()}
DILLER = ("tr", "en")


def dil_denetle(dil: str) -> str:
    d = (dil or "tr").lower()
    if d not in DILLER:
        raise ValueError(f"dil 'tr' ya da 'en' olmalı / lang must be 'tr' or 'en': {dil!r}")
    return d


def cevir(s: dict, dil: str) -> dict:
    """Türkçe anahtarlı sonucu istenen dile çevirir."""
    if dil_denetle(dil) == "tr":
        return dict(s)
    out = {ALAN_EN[k]: v for k, v in s.items()}
    if out.get("street_type"):
        out["street_type"] = YOL_TURU_EN[out["street_type"]]
    return out


def turkceye(s: dict) -> dict:
    """İki dildeki anahtarları da kabul eder, Türkçeye çevirir."""
    out = {EN_ALAN.get(k, k): v for k, v in s.items()}
    if out.get("yol_turu") in EN_YOL_TURU:
        out["yol_turu"] = EN_YOL_TURU[out["yol_turu"]]
    return out
