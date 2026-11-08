"""İl-ilçe sözlüğü (OpenStreetMap, ODbL) ve plaka kodları."""
from __future__ import annotations

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
_IL_TAKMA = {"afyon": "Afyonkarahisar", "icel": "Mersin", "maras": "Kahramanmaraş", "urfa": "Şanlıurfa", "antep": "Gaziantep"}


@dataclass
class Sozluk:
    iller: dict[str, str] = field(default_factory=dict)            # katlanmış ad -> il
    ilceler: dict[str, list[tuple[str, str]]] = field(default_factory=dict)  # katlanmış ad -> [(ilçe, il)]
    plaka_il: dict[int, str] = field(default_factory=dict)

    def yer_mi(self, s: str) -> bool:
        k = katla(s)
        return k in self.iller or k in self.ilceler


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
    z.plaka_il = {n: il for il, n in PLAKA.items() if katla(il) in z.iller}
    return z


@lru_cache(maxsize=1)
def varsayilan() -> Sozluk:
    metin = resources.files("tr_adres").joinpath("veri/gazetteer.json").read_text(encoding="utf-8")
    return sozluk_kur(json.loads(metin))
