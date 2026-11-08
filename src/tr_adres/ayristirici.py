"""Kural tabanlı Türkçe adres ayrıştırıcı. Model, ağ ya da ek paket kullanmaz.

Yöntem: metin bir de "katlanmış" (küçük harf, Türkçe karakter ASCII) biçimde tutulur. Desenler katlanmış metinde
aranır, değer aynı konumdan özgün metinden alınır; böylece 'CAFERAGA MH' ile 'Caferağa Mah.' aynı desene uyar,
çıktıda yazıldığı gibi kalır. İl ve ilçe her zaman sözlükteki doğru yazımla döner.
"""
from __future__ import annotations

import collections
import re

from .metin import duzle, katla
from .sozluk import Sozluk, varsayilan

ALANLAR = ("il", "ilce", "mahalle", "yol", "yol_turu", "ust_yol", "no", "ic_kapi", "kat", "bina", "posta_kodu", "kalan")

_K = r"(?:\d+/\w+\.?|[\w.'’-]+)"  # "195/1", "678/2." ve "451/A." gibi eğik çizgili sokak numaraları tek sözcük
_AD = rf"{_K}(?:\s+{_K}){{0,4}}?"
_SON = r"(?=[\s,/;]|$)"
_TUR_DESEN = {
    "mahalle": r"(?:mahallesi|mahalle|mah|mh)",
    "sokak": r"(?:sokagi|sokak|sokk|sok|sk)",
    "cadde": r"(?:caddesi|cadde|cad|cd)",
    "bulvar": r"(?:bulvari|bulvar|bulv|blv)",
}
_TURLER = [(t, re.compile(rf"(?:^|[\s,/;])({_AD})\s+{d}\.?{_SON}")) for t, d in _TUR_DESEN.items()]
_YOL_KELIME = re.compile(rf"^(?:{_TUR_DESEN['bulvar'][3:-1]}|{_TUR_DESEN['cadde'][3:-1]})\.?$")
_DUR = {"no", "numara", "kat", "daire", "d", "blok", "apt", "bina", "kapi", "ic", "turkiye"}
_DUR_AD = {"no", "numara", "kat", "daire", "d"}  # ad içinden atılanlar ("Yeni Kapı Sk." korunur)

_POSTA = re.compile(r"(?<![\w/-])(\d{5})(?![\w/-])")
_POSTA_SONRA_YOL = re.compile(rf"\s*\.?\s*(?:{'|'.join(d[3:-1] for d in _TUR_DESEN.values())})\.?{_SON}")
_POSTA_ONCE_NO = re.compile(r"(?:no|numara|kapi\s*no)\s*[:.]?\s*$")
_IC_KAPI = re.compile(r"(?:^|[\s,/;-])(?:daire|ic\s*kapi(?:\s*no)?|d)\s*[:.]?\s*(\d+[a-z]?)(?=[\s,/;]|$)")
_KAT = re.compile(r"(?:^|[\s,/;-])kat\s*[:.]?\s*(-?\d+)(?=[\s,/;]|$)")
_KAT_ONCE = re.compile(r"(?:^|[\s,/;-])(\d+)\s*\.?\s*kat(?=[\s,/;]|$)")
_NO = re.compile(r"(?:^|[\s,/;-])(?:dis\s*kapi\s*no|kapi\s*no|numara|no|nu)\s*[:.]?\s*(\d+[a-z]?(?:\s*[/-]\s*\d*[a-z\d]+)?)(?=[\s,;]|$)")
_TUR_SOZ = "|".join(d[3:-1] for d in _TUR_DESEN.values())
# Bina adı mahalle/sokak/cadde sözcüğünü içeremez: "Esentepe Mah. Büyükdere Cad. Levent Plaza" -> "Levent Plaza"
_BK = rf"(?!(?:{_TUR_SOZ})\.?(?:[\s,]|$)){_K}"
_BINA = re.compile(rf"(?:^|[\s,/;])({_BK}(?:\s+{_BK}){{0,4}}?\s+(?:apartmani|apt|sitesi|sit|plaza|is\s*merkezi)\.?(?:\s+\w+\s+blok)?){_SON}")
# "No" yazılmadan sokak/cadde/bulvar adının hemen ardından gelen kapı numarası: "Ziya Gökalp Cd 12"
_CIPLAK_NO = re.compile(rf"(?:sokagi|sokak|sokk|sok|sk|caddesi|cadde|cad|cd|bulvari|bulvar|bulv|blv)\.?[\s,]+(\d+[a-z]?(?:\s*/\s*\w+)?)(?=[\s,;]|$)(?!\s*\.?\s*(?:{_TUR_SOZ})\.?(?:[\s,]|$))")
_ULKE = re.compile(r"\b(?:turkiye|turkey|tr)\s*$")
_BOL = re.compile(r"[\s,;/()-]+")


class _Metin:
    """Özgün ve katlanmış metni aynı uzunlukta birlikte tutar."""

    def __init__(self, s: str):
        self.o = " " + s + " "
        self.k = katla(self.o)

    def kes(self, m: re.Match, grup: int = 1) -> str:
        a, b = m.span(grup)
        deger = self.o[a:b].strip()
        s, e = m.span(0)
        self.o = self.o[:s] + " , " + self.o[e:]
        self.k = self.k[:s] + " , " + self.k[e:]
        return deger

    def kes_grup(self, m: re.Match, grup: int = 1) -> str:
        """Yalnız grubu keser, eşleşmenin geri kalanı metinde kalır."""
        a, b = m.span(grup)
        deger = self.o[a:b].strip()
        self.o = self.o[:a] + " , " + self.o[b:]
        self.k = self.k[:a] + " , " + self.k[b:]
        return deger

    def al(self, desen: re.Pattern) -> str | None:
        m = desen.search(self.k)
        return self.kes(m) if m else None


def _posta_kodu(t: _Metin, z: Sozluk) -> str | None:
    aday = None
    for m in _POSTA.finditer(t.k):
        if _POSTA_SONRA_YOL.match(t.k, m.end()):      # "20019 Sk." sokak adıdır
            continue
        if _POSTA_ONCE_NO.search(t.k, 0, m.start()):  # "No: 12345" kapı numarasıdır
            continue
        if int(m.group(1)[:2]) not in z.plaka_il:     # ilk iki hane 01-81 olmalı
            continue
        aday = m                                      # sondaki aday tercih edilir
    return t.kes(aday) if aday else None


def _onek(ad: list[str], tablo: dict) -> int:
    """ad'ın başında tablodaki bir ada uyan en uzun ön ek (en çok 3 sözcük, en az bir sözcük artmalı)."""
    for n in (3, 2, 1):
        if n < len(ad) and katla(" ".join(ad[:n])) in tablo:
            return n
    return 0


def _metindeki_iller(k: str, z: Sozluk) -> collections.Counter:
    """Katlanmış metinde geçen illeri sayar (en çok 3 sözcüklük adlar)."""
    w = [x.strip(".:") for x in _BOL.split(k) if x.strip(".:")]
    say: collections.Counter = collections.Counter()
    for i in range(len(w)):
        for n in (1, 2, 3):
            a = " ".join(w[i:i + n])
            if a in z.iller:
                say[z.iller[a]] += 1
    return say


def _bas_yer_soy(ad: list[str], z: Sozluk, iller: collections.Counter) -> tuple[list[str], list[str]]:
    """'İl İlçe Mahalle' ya da 'İlçe İl Mahalle' diye yazılmış adın başındaki yer adlarını ayırır:
    'Samsun 19 Mayıs Fındıklı' -> ['Fındıklı']. Yer adıyla başlayan gerçek adlar korunur:
    'Fatih Sultan Mehmet', 'Gürpınar Yolu', 'Ömerli 33' (tek başına ilçe adı ayrılmaz)."""
    n = _onek(ad, z.iller)
    if n:
        il = z.iller[katla(" ".join(ad[:n]))]
        kalan = ad[n:]
        m = _onek(kalan, z.ilceler)
        if m and any(x[1] == il for x in z.ilceler[katla(" ".join(kalan[:m]))]):
            return kalan[m:], ad[:n + m]
        # yalnız il: metindeki tek il adıysa ve "Ankara Yolu" gibi bir ad değilse
        # ("Çanakkale Şehitleri Sk. ... Balıkesir" içinde Çanakkale sokak adıdır)
        if list(iller.items()) == [(il, 1)] and katla(kalan[0]).rstrip(".") not in {"yolu", "asfalti"}:
            return kalan, ad[:n]
        return ad, []
    n = _onek(ad, z.ilceler)
    if n:
        kalan = ad[n:]
        m = _onek(kalan, z.iller)
        if m and any(x[1] == z.iller[katla(" ".join(kalan[:m]))] for x in z.ilceler[katla(" ".join(ad[:n]))]):
            return kalan[m:], ad[:n + m]
    return ad, []


def _temizle(deger: str) -> str:
    deger = deger.strip(" ,")
    # "716." ve "3." sıra sayısıdır, nokta adın parçası; "Moda." gibi sondaki noktayı at
    if not re.search(r"\d\.$", deger):
        deger = deger.rstrip(".")
    return deger.lstrip(".").strip()


def ayristir_tr(girdi: str, sozluk: Sozluk | None = None) -> dict:
    z = sozluk or varsayilan()
    s: dict = dict.fromkeys(ALANLAR)
    t = _Metin(" ".join(duzle(str(girdi)).split()))
    m = _ULKE.search(t.k.rstrip())
    if m:
        t.kes(m, 0)

    s["posta_kodu"] = _posta_kodu(t, z)
    s["ic_kapi"] = t.al(_IC_KAPI)
    s["kat"] = t.al(_KAT) or t.al(_KAT_ONCE)
    s["no"] = t.al(_NO)
    if not s["no"]:
        m = _CIPLAK_NO.search(t.k)
        s["no"] = t.kes_grup(m) if m else None
    if s["no"]:
        s["no"] = re.sub(r"\s+", "", s["no"]).upper()
    s["bina"] = t.al(_BINA)

    soyulan: list[str] = []
    iller = _metindeki_iller(t.k, z)
    for tur, desen in _TURLER:
        b = desen.search(t.k)
        if not b:
            continue
        a, e = b.span(1)
        ad = [w for w in t.o[a:e].split() if katla(w).replace(".", "").replace(":", "") not in _DUR_AD]
        ad, soy = _bas_yer_soy(ad, z, iller)
        soyulan += soy
        if tur == "sokak":
            ic = next((i for i, w in enumerate(ad[:-1]) if _YOL_KELIME.match(katla(w))), -1)
            if ic >= 0:
                s["ust_yol"] = _temizle(" ".join(ad[:ic])) or None
                ad = ad[ic + 1:]
        if not ad:
            continue
        deger = _temizle(" ".join(ad))
        if tur == "mahalle":
            s["mahalle"] = deger
        elif not s["yol"]:
            s["yol"], s["yol_turu"] = deger, tur
        elif not s["ust_yol"]:
            s["ust_yol"] = deger
        t.kes(b, 0)

    parca = [w.rstrip(".:") for w in soyulan + _BOL.split(t.o)]
    parca = [w for w in parca if w]
    cok_anlamli = False
    i = len(parca) - 1
    while i >= 0:
        bulundu = False
        for n in range(min(3, len(parca) - i), 0, -1):
            a = katla(" ".join(parca[i:i + n]))
            if s["il"] is None and a in z.iller:
                s["il"] = z.iller[a]
                bulundu = True
            elif s["ilce"] is None and a in z.ilceler:
                adaylar = z.ilceler[a]
                u = next((x for x in adaylar if x[1] == s["il"]), None) if s["il"] else (adaylar[0] if len(adaylar) == 1 else None)
                if u or not s["il"]:
                    s["ilce"] = (u or adaylar[0])[0]
                    if u and not s["il"]:
                        s["il"] = u[1]
                    cok_anlamli = not u
                    bulundu = True
            if bulundu:
                del parca[i:i + n]
                break
        if s["il"] and s["ilce"]:
            break
        i = len(parca) - 1 if bulundu else i - 1

    if s["ilce"] and s["il"] and cok_anlamli:
        # ilçe il bulunmadan seçildiyse, sonradan bulunan ilde gerçekten var mı?
        u = next((x for x in z.ilceler.get(katla(s["ilce"]), []) if x[1] == s["il"]), None)
        s["ilce"] = u[0] if u else None
    if s["il"] is None and s["posta_kodu"]:
        s["il"] = z.plaka_il.get(int(s["posta_kodu"][:2]))

    kalan = [w for w in parca if katla(w) not in _DUR and not w.isdigit()]
    s["kalan"] = " ".join(kalan) or None
    return s
