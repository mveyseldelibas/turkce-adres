"""Yer sözlükleri (OpenStreetMap, ODbL): il, ilçe, mahalle/köy ve merkez koordinatları, sokak merkezleri,
yazım sözlüğü, posta kodu -> ilçe. Plaka kodları Türkiye standardındandır.

Büyük dosyalar (mahalle, sokak, kelime) ilk gerektiğinde yüklenir; paket onlarsız da çalışır.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources

from .metin import katla

# Plaka kodu = posta kodunun ilk iki hanesi.
PLAKA = {
    "Adana": 1, "Adıyaman": 2, "Afyonkarahisar": 3, "Ağrı": 4, "Amasya": 5, "Ankara": 6, "Antalya": 7, "Artvin": 8,
    "Aydın": 9, "Balıkesir": 10, "Bilecik": 11, "Bingöl": 12, "Bitlis": 13, "Bolu": 14, "Burdur": 15, "Bursa": 16,
    "Çanakkale": 17, "Çankırı": 18, "Çorum": 19, "Denizli": 20, "Diyarbakır": 21, "Edirne": 22, "Elâzığ": 23,
    "Erzincan": 24, "Erzurum": 25, "Eskişehir": 26, "Gaziantep": 27, "Giresun": 28, "Gümüşhane": 29, "Hakkâri": 30,
    "Hatay": 31, "Isparta": 32, "Mersin": 33, "İstanbul": 34, "İzmir": 35, "Kars": 36, "Kastamonu": 37, "Kayseri": 38,
    "Kırklareli": 39, "Kırşehir": 40, "Kocaeli": 41, "Konya": 42, "Kütahya": 43, "Malatya": 44, "Manisa": 45,
    "Kahramanmaraş": 46, "Mardin": 47, "Muğla": 48, "Muş": 49, "Nevşehir": 50, "Niğde": 51, "Ordu": 52, "Rize": 53,
    "Sakarya": 54, "Samsun": 55, "Siirt": 56, "Sinop": 57, "Sivas": 58, "Tekirdağ": 59, "Tokat": 60, "Trabzon": 61,
    "Tunceli": 62, "Şanlıurfa": 63, "Uşak": 64, "Van": 65, "Yozgat": 66, "Zonguldak": 67, "Aksaray": 68, "Bayburt": 69,
    "Karaman": 70, "Kırıkkale": 71, "Batman": 72, "Şırnak": 73, "Bartın": 74, "Ardahan": 75, "Iğdır": 76, "Yalova": 77,
    "Karabük": 78, "Kilis": 79, "Osmaniye": 80, "Düzce": 81,
}

# Yaygın eski/kısa yazımlar -> sözlükteki ad
_IL_TAKMA = {"afyon": "Afyonkarahisar", "icel": "Mersin", "maras": "Kahramanmaraş", "k.maras": "Kahramanmaraş",
             "kmaras": "Kahramanmaraş", "k. maras": "Kahramanmaraş", "urfa": "Şanlıurfa", "s.urfa": "Şanlıurfa",
             "antep": "Gaziantep", "g.antep": "Gaziantep", "elazig": "Elâzığ", "hakkari": "Hakkâri", "ist": "İstanbul"}
_ILCE_TAKMA = {"eyup": ("Eyüpsultan", "İstanbul"), "kazan": ("Kahramankazan", "Ankara"),
               "karadeniz eregli": ("Ereğli", "Zonguldak"), "k.eregli": ("Ereğli", "Zonguldak"),
               "izmit": ("İzmit", "Kocaeli"), "adapazari": ("Adapazarı", "Sakarya"), "antakya": ("Antakya", "Hatay")}


@dataclass
class Yer:
    ad: str
    il: str
    ilce: str
    tur: str            # mahalle / koy / semt
    enlem: float | None
    boylam: float | None


@dataclass
class Sozluk:
    iller: dict[str, str] = field(default_factory=dict)                       # katlanmış ad -> il
    ilceler: dict[str, list[tuple[str, str]]] = field(default_factory=dict)   # katlanmış ad -> [(ilçe, il)]
    plaka_il: dict[int, str] = field(default_factory=dict)
    # genişletilmiş (isteğe bağlı) veriler
    mahalle: dict[tuple[str, str], dict[str, Yer]] = field(default_factory=dict)   # (il, ilçe) -> katlanmış ad -> Yer
    mahalle_ad: dict[str, list[Yer]] = field(default_factory=dict)                  # katlanmış ad -> [Yer]
    sokak: dict[tuple[str, str, str], tuple[float, float, int]] = field(default_factory=dict)  # (il, ilçe, katlanmış yol) -> (enlem, boylam, n)
    kelime: dict[str, str] = field(default_factory=dict)                            # katlanmış sözcük -> doğru yazım
    posta: dict[str, tuple[str, str]] = field(default_factory=dict)                 # posta kodu -> (ilçe, il)
    ilce_merkez: dict[tuple[str, str], tuple[float, float]] = field(default_factory=dict)
    il_merkez: dict[str, tuple[float, float]] = field(default_factory=dict)

    def yer_mi(self, s: str) -> bool:
        k = katla(s)
        return k in self.iller or k in self.ilceler

    def mahalle_mi(self, il: str | None, ilce: str | None, ad: str) -> Yer | None:
        k = _mah_anahtar(ad)
        if il and ilce:
            return self.mahalle.get((il, ilce), {}).get(k)
        aday = [y for y in self.mahalle_ad.get(k, []) if (il is None or y.il == il) and (ilce is None or y.ilce == ilce)]
        return aday[0] if len(aday) == 1 else None


def _mah_anahtar(ad: str) -> str:
    k = katla(ad).strip()
    for son in (" mahallesi", " mahalle", " mah.", " mah", " koyu", " koy"):
        if k.endswith(son):
            k = k[: -len(son)].strip()
    return k


def sozluk_kur(veri: dict) -> Sozluk:
    """{'iller': {'İl': {'ilceler': [...]}}} biçiminden arama tablosu kurar."""
    z = Sozluk()
    for il, v in veri["iller"].items():
        z.iller[katla(il)] = il
        for ilce in v["ilceler"]:
            z.ilceler.setdefault(katla(ilce), []).append((ilce, il))
            # "Adıyaman Merkez" -> "Merkez" de tanınsın (il bilgisiyle çözülür)
            if katla(ilce).endswith(" merkez"):
                z.ilceler.setdefault("merkez", []).append((ilce, il))
    for k, il in _IL_TAKMA.items():
        if katla(il) in z.iller:
            z.iller.setdefault(k, il)
    for k, (ilce, il) in _ILCE_TAKMA.items():
        if k != katla(ilce) and (ilce, il) in z.ilceler.get(katla(ilce), []):
            z.ilceler.setdefault(k, []).append((ilce, il))
    z.plaka_il = {n: il for il, n in PLAKA.items() if katla(il) in z.iller}
    return z


def _oku_gz(ad: str):
    yol = resources.files("turkce_adres").joinpath(f"veri/{ad}")
    if not yol.is_file():
        return None
    return json.loads(gzip.decompress(yol.read_bytes()).decode("utf-8"))


def genislet(z: Sozluk) -> Sozluk:
    """Mahalle, sokak, yazım ve posta kodu sözlüklerini (varsa) yükler."""
    m = _oku_gz("mahalle.json.gz")
    if m:
        for il, ilceler in m["iller"].items():
            for ilce, liste in ilceler.items():
                d = z.mahalle.setdefault((il, ilce), {})
                for ad, tur, en, boy in liste:
                    y = Yer(ad, il, ilce, tur, en, boy)
                    d.setdefault(_mah_anahtar(ad), y)
                    z.mahalle_ad.setdefault(_mah_anahtar(ad), []).append(y)
        z.ilce_merkez = {tuple(k.split("|")): tuple(v) for k, v in m.get("ilce_merkez", {}).items()}
        z.il_merkez = {k: tuple(v) for k, v in m.get("il_merkez", {}).items()}
    s = _oku_gz("sokak.json.gz")
    if s:
        for k, v in s["sokak"].items():
            il, ilce, yol = k.split("|")
            z.sokak[(il, ilce, yol)] = tuple(v)
        z.posta = {k: tuple(v) for k, v in s.get("posta", {}).items()}
    k = _oku_gz("kelime.json.gz")
    if k:
        z.kelime = k["kelime"]
    return z


@lru_cache(maxsize=1)
def varsayilan() -> Sozluk:
    metin = resources.files("turkce_adres").joinpath("veri/gazetteer.json").read_text(encoding="utf-8")
    return genislet(sozluk_kur(json.loads(metin)))
