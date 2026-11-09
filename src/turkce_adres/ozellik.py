"""Ayrıştırmanın üstüne kurulan araçlar: internetsiz yaklaşık konum, adres eşleştirme, KVKK genelleştirmesi,
teslimat için eksik alan denetimi. Hepsi Türkçe ya da İngilizce anahtarlı sözlük ya da düz adres metni kabul eder.
"""
from __future__ import annotations

from .dil import ALAN_EN, cevir, dil_denetle, turkceye
from .metin import katla
from .sozluk import Sozluk, varsayilan


def _alanlar(a, sozluk: Sozluk | None = None) -> dict:
    if isinstance(a, str):
        from .ayristirici import ayristir_tr
        return ayristir_tr(a, sozluk)
    return turkceye(a)


def _n(x) -> str:
    return " ".join(katla(str(x)).replace(".", " ").split()) if x else ""


def sokak_anahtar(yol: str, tur: str | None) -> str:
    return f"{_n(yol)}#{tur or ''}"


# ---------------------------------------------------------------- konum

def konum(adres, dil: str = "tr", sozluk: Sozluk | None = None) -> dict | None:
    """İnternetsiz yaklaşık konum (OpenStreetMap verisinden). En ince bulunan düzeyi döndürür:
    sokak (o sokaktaki OSM adreslerinin ortalaması) > mahalle/köy merkezi > ilçe > il.

    >>> k = konum("Caferağa Mah. Moda Cad. No:12 Kadıköy/İstanbul")
    >>> k["duzey"] in ("sokak", "mahalle", "ilce", "il")
    True
    """
    z = sozluk or varsayilan()
    s = _alanlar(adres, z)
    il, ilce = s.get("il"), s.get("ilce")
    sonuc = None
    if il and ilce and s.get("yol"):
        v = z.sokak.get((il, ilce, sokak_anahtar(s["yol"], s.get("yol_turu"))))
        if v:
            sonuc = (v[0], v[1], "sokak")
    if not sonuc and il and (s.get("mahalle") or s.get("koy")):
        y = z.mahalle_mi(il, ilce, s.get("mahalle") or s.get("koy"))
        if y and y.enlem is not None:
            sonuc = (y.enlem, y.boylam, "mahalle")
    if not sonuc and il and ilce and (il, ilce) in z.ilce_merkez:
        sonuc = (*z.ilce_merkez[(il, ilce)], "ilce")
    if not sonuc and il in z.il_merkez:
        sonuc = (*z.il_merkez[il], "il")
    if not sonuc:
        return None
    out = {"enlem": round(sonuc[0], 6), "boylam": round(sonuc[1], 6), "duzey": sonuc[2], "kaynak": "OpenStreetMap (ODbL)"}
    if dil_denetle(dil) == "en":
        out = {"lat": out["enlem"], "lon": out["boylam"], "level": {"sokak": "street", "mahalle": "neighbourhood",
               "ilce": "district", "il": "province"}[out["duzey"]], "source": out["kaynak"]}
    return out


# ---------------------------------------------------------------- eşleştirme

_AGIRLIK = {"il": 0.08, "ilce": 0.12, "mahalle": 0.18, "koy": 0.18, "yol": 0.24, "no": 0.22, "ic_kapi": 0.1,
            "blok": 0.04, "kat": 0.02}


def _sim(a: str, b: str) -> float:
    from .ayristirici import osa
    if a == b:
        return 1.0
    m = max(len(a), len(b))
    return max(0.0, 1 - osa(a, b) / m) if m else 0.0


def benzerlik(a, b, sozluk: Sozluk | None = None) -> float:
    """İki adresin aynı yeri gösterme benzerliği, 0-1. Yazım farkını (Mah./Mahallesi, büyük harf, Türkçe karakter,
    sıra) yok sayar; il ya da ilçe farklıysa 0, kapı no farklıysa en çok 0,6, daire farklıysa en çok 0,8.

    >>> benzerlik("CAFERAGA MH MODA CD NO 12 KADIKOY ISTANBUL", "Caferağa Mahallesi, Moda Caddesi No:12, Kadıköy/İstanbul")
    1.0
    """
    z = sozluk or varsayilan()
    x, y = _alanlar(a, z), _alanlar(b, z)
    for k in ("il", "ilce"):
        if x.get(k) and y.get(k) and x[k] != y[k]:
            return 0.0
    pay = payda = 0.0
    tavan = 1.0
    for k, w in _AGIRLIK.items():
        p, q = _n(x.get(k)), _n(y.get(k))
        if not p and not q:
            continue
        payda += w
        if p and q:
            sim = _sim(p, q)
            if k in ("no", "ic_kapi") and sim < 1:
                tavan = min(tavan, 0.6 if k == "no" else 0.8)
                sim = 0.0
            pay += w * (sim if sim >= 0.75 else 0.0)
        else:
            pay += w * 0.5  # bir tarafta yok: ne kanıt ne karşı kanıt
    if payda == 0:
        return 0.0
    return round(min(tavan, pay / payda), 2)


def ayni_mi(a, b, esik: float = 0.9, sozluk: Sozluk | None = None) -> bool:
    """İki adres aynı yer mi? (benzerlik >= esik)"""
    return benzerlik(a, b, sozluk) >= esik


def eslestirme_anahtari(a, sozluk: Sozluk | None = None) -> str:
    """Tekilleştirme için kaba anahtar: il|ilçe|mahalle (katlanmış). Aynı anahtarlı kayıtlar benzerlikle karşılaştırılır."""
    s = _alanlar(a, sozluk)
    return "|".join(_n(s.get(k)) for k in ("il", "ilce")) + "|" + _n(s.get("mahalle") or s.get("koy"))


# ---------------------------------------------------------------- KVKK genelleştirmesi

_DUZEYLER = {
    "il": ("il",),
    "ilce": ("il", "ilce"),
    "mahalle": ("il", "ilce", "mahalle", "koy"),
    "yol": ("il", "ilce", "mahalle", "koy", "yol", "yol_turu", "ust_yol"),
}


def genellestir(adres, duzey: str = "mahalle", dil: str = "tr", sozluk: Sozluk | None = None) -> dict:
    """Adresi seçilen düzeyden daha ayrıntılı bilgiyi atarak genelleştirir (kapı no, daire, kat, blok, bina, posta
    kodu, tarif her düzeyde atılır). Bu bir genelleştirmedir, tek başına anonimleştirme sayılmaz: az nüfuslu bir
    mahalle ya da başka verilerle birleşince kişi yine belirlenebilir.

    >>> genellestir("Caferağa Mah. Moda Cad. No:12 D:3 Kadıköy/İstanbul")["metin"]
    'Caferağa Mah., Kadıköy/İstanbul'
    """
    from . import bicimle
    if duzey not in _DUZEYLER:
        raise ValueError(f"duzey şunlardan biri olmalı: {', '.join(_DUZEYLER)}")
    s = _alanlar(adres, sozluk)
    tut = _DUZEYLER[duzey]
    g = {k: (s.get(k) if k in tut else None) for k in ALAN_EN if k not in ("guven", "notlar")}
    g["metin"] = bicimle(g)
    if dil_denetle(dil) == "en":
        g = cevir(g, dil)
        g["text"] = g.pop("metin")
    return g


# ---------------------------------------------------------------- teslimat denetimi

_EKSIK = {
    "il": ("il yok", "province missing"),
    "ilce": ("ilçe yok", "district missing"),
    "mahalle": ("mahalle ya da köy yok", "neighbourhood or village missing"),
    "yol": ("cadde/sokak yok", "street missing"),
    "no": ("dış kapı numarası yok", "house number missing"),
    "ic_kapi": ("iç kapı (daire) numarası yok, binada birden çok bağımsız bölüm var gibi", "unit number missing though the building seems to have several units"),
    "posta_kodu": ("posta kodu yok (önerilir)", "postcode missing (recommended)"),
    "uyumsuz": ("ilçe ile il uyuşmuyor", "district does not match province"),
}


def eksikler(adres, dil: str = "tr", sozluk: Sozluk | None = None) -> list[str]:
    """Kargo/teslimat için eksik ya da çelişkili adres öğeleri. Liste boşsa adres eksiksiz görünür.
    Öğeler Adres ve Numaralamaya İlişkin Yönetmelik'teki temel adres bileşenlerine dayanır.

    >>> eksikler("Moda Cad. Kadıköy")
    ['mahalle ya da köy yok', 'dış kapı numarası yok', 'posta kodu yok (önerilir)']
    """
    z = sozluk or varsayilan()
    s = _alanlar(adres, z)
    i = 0 if dil_denetle(dil) == "tr" else 1
    out = []
    if not s.get("il"):
        out.append("il")
    if not s.get("ilce"):
        out.append("ilce")
    elif s.get("il") and (s["ilce"], s["il"]) not in z.ilceler.get(katla(s["ilce"]), []):
        out.append("uyumsuz")
    if not (s.get("mahalle") or s.get("koy")):
        out.append("mahalle")
    if not s.get("yol") and not s.get("koy"):
        out.append("yol")
    if not s.get("no"):
        out.append("no")
    if not s.get("ic_kapi") and (s.get("kat") or s.get("blok") or s.get("bina")):
        out.append("ic_kapi")
    if not s.get("posta_kodu"):
        out.append("posta_kodu")
    return [_EKSIK[k][i] for k in out]
