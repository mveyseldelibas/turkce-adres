"""Kural tabanlı Türkçe adres ayrıştırıcı. Model, ağ ya da ek paket kullanmaz.

Yöntem: metin bir de "katlanmış" (küçük harf, Türkçe karakter ASCII) biçimde tutulur. Desenler katlanmış metinde
aranır, değer aynı konumdan özgün metinden alınır; böylece 'CAFERAGA MH' ile 'Caferağa Mah.' aynı desene uyar.
İl, ilçe ve (sözlükte varsa) mahalle her zaman doğru yazımla döner; ASCII yazılmış sözcükler yazım sözlüğüyle
Türkçe harflerine kavuşturulur (duzelt=False ile yazıldığı gibi kalır).
"""
from __future__ import annotations

import collections
import re

from .metin import buyuk_bas, duzle, katla
from .sozluk import Sozluk, varsayilan

ALANLAR = ("il", "ilce", "mahalle", "koy", "yol", "yol_turu", "ust_yol", "no", "ic_kapi", "kat", "blok", "bina",
           "posta_kodu", "tarif", "kalan")
EK_ALANLAR = ("guven", "notlar")

_K = r"(?:\d+/\w+\.?|[\w.'’-]+)"  # "195/1", "678/2." ve "451/A." gibi eğik çizgili sokak numaraları tek sözcük
_AD = rf"{_K}(?:\s+{_K}){{0,4}}?"
_SON = r"(?=[\s,/;]|$)"
_TUR_DESEN = {
    "mahalle": r"(?:mahallesi|mahalle|mah|mh)",
    "cikmaz": r"(?:cikmazi|cikmaz|cikm|cik)",
    "sokak": r"(?:sokagi|sokak|sokk|sok|sk)",
    "cadde": r"(?:caddesi|cadde|cad|cd)",
    "bulvar": r"(?:bulvari|bulvar|bulv|blv)",
    "meydan": r"(?:meydani|meydan|myd)",
    "yol": r"(?:yolu)",
    "koy": r"(?:koyu)",
}


def _ic(d: str) -> str:
    """'(?:a|b)' -> 'a|b'"""
    return d[3:-1]


_SONRA_YOL = r"(?:sokagi|sokak|sokk|sok|sk|caddesi|cadde|cad|cd|bulvari|bulvar|bulv|blv)"
# "Sevdalı Çıkmazı Sokak", "Kızılay Meydanı Cd." gibi: ardından sokak/cadde geliyorsa çıkmaz/meydan/yolu adın parçasıdır
_ADIN_PARCASI = rf"(?!\s+{_SONRA_YOL}\.?(?:[\s,]|$))"
_TURLER = [(t, re.compile(rf"(?:^|[\s,/;])({_AD})\s+{d}\.?{_ADIN_PARCASI if t in ('cikmaz', 'meydan', 'yol') else ''}{_SON}"))
           for t, d in _TUR_DESEN.items()]
_YOL_TURLERI = ("cikmaz", "sokak", "cadde", "bulvar", "meydan", "yol")
_YOL_KELIME = re.compile(rf"^(?:{'|'.join(_ic(_TUR_DESEN[t]) for t in ('cadde', 'bulvar', 'meydan'))})\.?$")
_TUR_KELIME = re.compile(rf"^(?:{'|'.join(_ic(d) for d in _TUR_DESEN.values())})\.?$")
_TUR_SOZ = "|".join(_ic(d) for d in _TUR_DESEN.values())
_DUR = {"no", "numara", "kat", "daire", "d", "blok", "apt", "bina", "kapi", "ic", "turkiye", "k"}
_DUR_AD = {"no", "numara", "kat", "daire", "d"}  # ad içinden atılanlar ("Yeni Kapı Sk." korunur)
_TAM = {"cikmaz": "Çıkmazı", "sokak": "Sokak", "cadde": "Caddesi", "bulvar": "Bulvarı", "meydan": "Meydanı", "yol": "Yolu"}

_POSTA = re.compile(r"(?<![\w/-])(\d{5})(?![\w/-])")
_POSTA_SONRA_YOL = re.compile(rf"\s*\.?\s*(?:{_TUR_SOZ})\.?{_SON}")
_POSTA_ONCE_NO = re.compile(r"(?:no|numara|kapi\s*no)\s*[:.]?\s*$")
_IC_KAPI = re.compile(r"(?:^|[\s,/;-])(?:daire|ic\s*kapi(?:\s*no)?|d)\s*[:.]?\s*(\d+[a-z]?)(?=[\s,/;]|$)")
_KAT_DEGER = r"(-?\d+|zemin|bodrum|cati|asma|giris|z)"
_KAT = re.compile(rf"(?:^|[\s,/;-])(?:kat\s*[:.]?|k\s*[:.])\s*{_KAT_DEGER}(?=[\s,/;.]|$)")
_KAT_ONCE = re.compile(rf"(?:^|[\s,/;-]){_KAT_DEGER}\s*\.?\s*kat(?=[\s,/;]|$)")
_KAT_AD = {"zemin": "Zemin", "z": "Zemin", "bodrum": "Bodrum", "cati": "Çatı", "asma": "Asma", "giris": "Giriş"}
_NO = re.compile(r"(?:^|[\s,/;-])(?:dis\s*kapi\s*no|kapi\s*no|numara|no|nu|#)\s*[:.]?\s*(\d+[a-z]?(?:\s*[/-]\s*\d*[a-z\d]+)?)(?=[\s,;]|$)")
_BLOK = re.compile(r"(?:^|[\s,/;-])(?:blok|blk)\s*[:.]?\s*([a-z]{1,2}\d{0,3}[a-z]?(?:-\d+)?|\d{1,3}[a-z]?(?:-\d+)?)(?=[\s,/;]|$)")
_BLOK_ONCE = re.compile(r"(?:^|[\s,/;-])((?:[a-z]{1,2}\d{0,2}|\d{1,2}[a-z]?)(?:-\d+)?)\s*\.?\s*(?:blok|blk)\.?(?=[\s,/;]|$)")
# Bina adı mahalle/sokak/cadde sözcüğünü içeremez: "Esentepe Mah. Büyükdere Cad. Levent Plaza" -> "Levent Plaza"
_BK = rf"(?!(?:{_TUR_SOZ})\.?(?:[\s,]|$)){_K}"
_BINA_TUR = r"(?:apartmani|apartman|apart|apt|ap|sitesi|sit|konutlari|evleri|rezidans|residence|plaza|is\s*merkezi|is\s*hani|ishani|kuleleri)"
# "Işıkpınarı Evleri Sk.", "Şemistan Şit sk": ardından yol türü geliyorsa bina değil sokak adıdır
_BINA = re.compile(rf"(?:^|[\s,/;])({_BK}(?:\s+{_BK}){{0,4}}?\s+{_BINA_TUR}\.?){_SON}(?!\s+(?:{_TUR_SOZ})\.?(?:[\s,]|$))")
# "No" yazılmadan yol adının hemen ardından gelen kapı numarası: "Ziya Gökalp Cd 12"
_CIPLAK_NO = re.compile(rf"(?:{'|'.join(_ic(_TUR_DESEN[t]) for t in ('sokak', 'cadde', 'bulvar', 'cikmaz'))})\.?[\s,]+"
                        rf"(\d+[a-z]?(?:\s*/\s*\w+)?)(?=[\s,;]|$)(?!\s*\.?\s*(?:{_TUR_SOZ})\.?(?:[\s,]|$))")
_ULKE = re.compile(r"\b(?:turkiye|turkey|tr)\s*$")
_BOL = re.compile(r"[\s,;/()-]+")
_TARIF = re.compile(r"((?:[\w.'’]+\s+){1,3}?)(karsisi|karsisinda|yani|yaninda|arkasi|arkasinda|onu|onunde|bitisigi|"
                    r"bitisiginde|ustu|ustunde|civari|civarinda)(?=\s|$)")

# Etiketli yazım: "Mahalle: Caferağa, Cadde: Moda, İlçe: Kadıköy"
_ETIKET = re.compile(r"(?:^|(?<=[\s,;]))(mahallesi|mahalle|mah|koyu|koy|caddesi|cadde|cad|sokagi|sokak|sok|bulvari|bulvar|"
                     r"ilcesi|ilce|ili|il|sehir|semt|posta\s*kodu|pk|sitesi|site|apartmani|apartman|apt|bina)\s*:\s*")
_ETIKET_EK = {"mahalle": " Mah.", "koy": " Köyü", "cadde": " Cad.", "sokak": " Sk.", "bulvar": " Bulv.", "site": " Sitesi",
              "apartman": " Apt."}
_ETIKET_KOK = {"mahallesi": "mahalle", "mahalle": "mahalle", "mah": "mahalle", "koyu": "koy", "koy": "koy",
               "caddesi": "cadde", "cadde": "cadde", "cad": "cadde", "sokagi": "sokak", "sokak": "sokak", "sok": "sokak",
               "bulvari": "bulvar", "bulvar": "bulvar", "sitesi": "site", "site": "site", "apartmani": "apartman",
               "apartman": "apartman", "apt": "apartman"}

NOT = {
    "il_ilceden": ("il ilçeden bulundu", "province inferred from district"),
    "il_postadan": ("il posta kodundan bulundu", "province inferred from postcode"),
    "il_mahalleden": ("il mahalleden bulundu", "province inferred from neighbourhood"),
    "ilce_postadan": ("ilçe posta kodundan bulundu", "district inferred from postcode"),
    "ilce_mahalleden": ("ilçe mahalleden bulundu", "district inferred from neighbourhood"),
    "yazim": ("yazım düzeltildi: {a} -> {b}", "spelling corrected: {a} -> {b}"),
    "ilce_uyumsuz": ("ilçe {a} bu ile ait değil, alınmadı", "district {a} does not belong to this province, ignored"),
    "mahalle_yok": ("mahalle sözlükte yok: {a}", "neighbourhood not in gazetteer: {a}"),
    "ic_kapi_egik": ("iç kapı no {a} yazımından alındı", "unit number taken from {a}"),
}


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

    def al(self, desen: re.Pattern, grup: int = 1) -> str | None:
        m = desen.search(self.k)
        return self.kes(m, grup) if m else None


def _etiketleri_ac(s: str) -> str:
    """'Mahalle: Caferağa, Cadde: Moda, İlçe: Kadıköy' -> 'Caferağa Mah., Moda Cad., Kadıköy'."""
    k = katla(s)
    ms = list(_ETIKET.finditer(k))
    if not ms:
        return s
    out, son = [], 0
    for i, m in enumerate(ms):
        out.append(s[son:m.start()])
        bit = ms[i + 1].start() if i + 1 < len(ms) else len(s)
        v = re.search(r"[,;\n]", s[m.end():bit])
        vbit = m.end() + v.start() if v else bit
        deger = s[m.end():vbit].strip()
        kok = _ETIKET_KOK.get(re.sub(r"\s+", " ", m.group(1)))
        out.append(deger + (_ETIKET_EK.get(kok, "") if deger else ""))
        son = vbit
    out.append(s[son:])
    return "".join(out)


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
        if n < len(ad) and katla(" ".join(ad[:n])).rstrip(".") in tablo:
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


def _bas_yer_soy(ad: list[str], z: Sozluk, iller: collections.Counter, tur: str) -> tuple[list[str], list[str]]:
    """'İl İlçe Mahalle' ya da 'İlçe İl Mahalle' diye yazılmış adın başındaki yer adlarını ayırır:
    'Samsun 19 Mayıs Fındıklı' -> ['Fındıklı']. Yer adıyla başlayan gerçek adlar korunur:
    'Fatih Sultan Mehmet', 'Gürpınar Yolu', 'Ömerli 33'. Yalnız ilçe yazılmışsa (il yok) ilçe ancak geri kalan ad
    o ilçenin sözlükteki bir mahallesiyse ayrılır: 'Kadikoy Caferaga Mah.' -> 'Caferaga'."""
    n = _onek(ad, z.iller)
    if n:
        il = z.iller[katla(" ".join(ad[:n])).rstrip(".")]
        kalan = ad[n:]
        m = _onek(kalan, z.ilceler)
        if m and any(x[1] == il for x in z.ilceler[katla(" ".join(kalan[:m])).rstrip(".")]):
            return kalan[m:], ad[:n + m]
        # yalnız il: metindeki tek il adıysa ve "Ankara Yolu" gibi bir ad değilse
        if list(iller.items()) == [(il, 1)] and katla(kalan[0]).rstrip(".") not in {"yolu", "asfalti"}:
            return kalan, ad[:n]
        return ad, []
    n = _onek(ad, z.ilceler)
    if n:
        adaylar = z.ilceler[katla(" ".join(ad[:n])).rstrip(".")]
        if iller:  # metinde il yazılıysa yalnız o ilin ilçeleri ("Yıldırım Beyazıt Mah. ... Kayseri" değil)
            adaylar = [x for x in adaylar if x[1] in iller]
            if not adaylar:
                return ad, []
        kalan = ad[n:]
        m = _onek(kalan, z.iller)
        if m and any(x[1] == z.iller[katla(" ".join(kalan[:m])).rstrip(".")] for x in adaylar):
            return kalan[m:], ad[:n + m]
        if tur in ("mahalle", "koy") and z.mahalle:
            ad_geri = " ".join(kalan)
            if any(z.mahalle_mi(il, ilce, ad_geri) for ilce, il in adaylar):
                return kalan, ad[:n]
    return ad, []


def _temizle(deger: str) -> str:
    deger = deger.strip(" ,")
    # "716." ve "3." sıra sayısıdır, nokta adın parçası; "Moda." gibi sondaki noktayı at
    if not re.search(r"\d\.$", deger):
        deger = deger.rstrip(".")
    return deger.lstrip(".").strip()


def osa(a: str, b: str) -> int:
    """Damerau-Levenshtein (bitişik harf yer değiştirmesi dahil) uzaklığı."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def _yakin(sozcuk: str, adaylar) -> str | None:
    """Yazım hatası toleransı: 5-7 harfte 1, 8+ harfte 2 düzenleme. Tek en iyi aday yoksa None."""
    k = katla(sozcuk)
    if len(k) < 5 or not k.isalpha():
        return None
    esik = 1 if len(k) < 8 else 2
    en, kim = esik + 1, set()
    for a in adaylar:
        if abs(len(a) - len(k)) > esik:
            continue
        d = osa(k, a)
        if d < en:
            en, kim = d, {a}
        elif d == en:
            kim.add(a)
    return next(iter(kim)) if en <= esik and len(kim) == 1 else None


def _sozcuk_duzelt(deger: str | None, z: Sozluk) -> str | None:
    """ASCII yazılmış sözcükleri yazım sözlüğüyle Türkçe harflerine kavuşturur: 'BUYUKDERE' -> 'Büyükdere'."""
    if not deger:
        return deger
    tek_boy = deger.isupper() or deger.islower()  # "YENI KAPI", "kızılay meydanı": harf boyu da düzeltilir
    out = []
    for w in deger.split(" "):
        k = katla(w)
        if w.isascii() and k in z.kelime and (w.isupper() or w.islower() or katla(z.kelime[k]) == k):
            out.append(z.kelime[k])
        elif tek_boy:
            out.append(buyuk_bas(w))
        else:
            out.append(w)
    return " ".join(out)


def ayristir_tr(girdi: str, sozluk: Sozluk | None = None, duzelt: bool = True) -> dict:
    """Türkçe anahtarlı sonuç; 'notlar' kod listesidir: [(kod, {a:..., b:...}), ...]."""
    z = sozluk or varsayilan()
    s: dict = dict.fromkeys(ALANLAR)
    notlar: list = []
    duzeltme = 0
    metin = _etiketleri_ac(" ".join(duzle(str(girdi or "")).split()))
    t = _Metin(metin)
    m = _ULKE.search(t.k.rstrip())
    if m:
        t.kes(m, 0)

    s["posta_kodu"] = _posta_kodu(t, z)
    s["ic_kapi"] = t.al(_IC_KAPI)
    kat = t.al(_KAT) or t.al(_KAT_ONCE)
    s["kat"] = _KAT_AD.get(katla(kat), kat) if kat else None
    s["no"] = t.al(_NO)
    s["blok"] = t.al(_BLOK) or t.al(_BLOK_ONCE)
    if s["blok"]:
        s["blok"] = s["blok"].upper()
    if not s["no"]:
        m = _CIPLAK_NO.search(t.k)
        s["no"] = t.kes_grup(m) if m else None
    if s["no"]:
        s["no"] = re.sub(r"\s+", "", s["no"]).upper()
        s["no"] = re.sub(r"^(\d+)-([A-Z])$", r"\1/\2", s["no"])  # "15-A" -> "15/A"
        e = re.fullmatch(r"\d+[A-Z]?/(\d+)", s["no"])
        if e and not s["ic_kapi"]:
            s["ic_kapi"] = e.group(1)
            notlar.append(("ic_kapi_egik", {"a": s["no"]}))
    s["bina"] = t.al(_BINA)

    soyulan: list[str] = []
    iller = _metindeki_iller(t.k, z)
    for tur, desen in _TURLER:
        b = desen.search(t.k)
        if not b:
            continue
        a, e = b.span(1)
        ad = [w for w in t.o[a:e].split() if katla(w).replace(".", "").replace(":", "") not in _DUR_AD]
        ad, soy = _bas_yer_soy(ad, z, iller, tur)
        soyulan += soy
        ust = None
        if tur in _YOL_TURLERI and not s["koy"]:
            # "Yeşilyurt Köyü Merkez Sokak": köy adı yol adının önüne yazılmış
            kk = next((i for i, w in enumerate(ad[:-1]) if katla(w).rstrip(".") == "koyu"), -1)
            if kk > 0:
                s["koy"] = _temizle(" ".join(ad[:kk]))
                ad = ad[kk + 1:]
        if tur in ("cikmaz", "sokak", "cadde"):
            ic = max((i for i, w in enumerate(ad[:-1]) if _YOL_KELIME.match(katla(w))), default=-1)
            if ic >= 0:
                ust = _temizle(" ".join(ad[:ic + 1])) or None
                ad = ad[ic + 1:]
        while len(ad) > 1 and _TUR_KELIME.match(katla(ad[0])):  # "Mah. Vezneciler" -> "Vezneciler"
            ad = ad[1:]
        if not ad:
            continue
        deger = _temizle(" ".join(ad))
        if tur == "mahalle" and not s["mahalle"]:
            s["mahalle"] = deger
        elif tur == "koy" and not s["koy"]:
            s["koy"] = deger
        elif tur in _YOL_TURLERI and not s["yol"]:
            s["yol"], s["yol_turu"] = deger, tur
            s["ust_yol"] = s["ust_yol"] or ust
        elif tur in _YOL_TURLERI and not s["ust_yol"]:
            s["ust_yol"] = f"{deger} {_TAM[tur]}"
        else:
            continue
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
                        notlar.append(("il_ilceden", {}))
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
        if not u:
            notlar.append(("ilce_uyumsuz", {"a": s["ilce"]}))
        s["ilce"] = u[0] if u else None

    # yazım hatası toleransı (yalnız il/ilçe eksikse, artakalan sözcüklerde)
    if s["il"] is None or s["ilce"] is None:
        il_ad = {katla(v) for v in z.iller.values()}
        for j, w in enumerate(list(parca)):
            if katla(w) in _DUR or not w.isalpha():
                continue
            if s["il"] is None:
                y = _yakin(w, il_ad)
                if y:
                    s["il"] = z.iller[y]
                    notlar.append(("yazim", {"a": w, "b": s["il"]}))
                    parca[j] = ""
                    duzeltme += 1
                    continue
            if s["ilce"] is None:
                aday = {katla(x[0]) for v in z.ilceler.values() for x in v if s["il"] is None or x[1] == s["il"]}
                y = _yakin(w, aday)
                if y:
                    secenek = [x for x in z.ilceler[y] if s["il"] is None or x[1] == s["il"]]
                    if len(secenek) == 1:
                        s["ilce"] = secenek[0][0]
                        if s["il"] is None:
                            s["il"] = secenek[0][1]
                            notlar.append(("il_ilceden", {}))
                        notlar.append(("yazim", {"a": w, "b": s["ilce"]}))
                        parca[j] = ""
                        duzeltme += 1
        parca = [w for w in parca if w]

    # bulunan il/ilçenin artakalan tekrarlarını (ve yazım hatalı tekrarlarını) at: "ISTANBUL BESIKTAS ...", "Besiktas/Istnbul"
    if s["il"] or s["ilce"]:
        hedef = {katla(x) for x in (s["il"], s["ilce"]) if x}
        hedef |= {k for k, v in z.iller.items() if v == s["il"]}
        yeni = []
        for w in parca:
            k = katla(w)
            if k in hedef:
                continue
            y = _yakin(w, hedef)
            if y:
                notlar.append(("yazim", {"a": w, "b": z.iller.get(y) or s["ilce"]}))
                continue
            yeni.append(w)
        parca = yeni

    if s["posta_kodu"]:
        p = z.posta.get(s["posta_kodu"])
        if s["il"] is None:
            s["il"] = p[1] if p else z.plaka_il.get(int(s["posta_kodu"][:2]))
            if s["il"]:
                notlar.append(("il_postadan", {}))
        if s["ilce"] is None and p and p[1] == s["il"]:
            s["ilce"] = p[0]
            notlar.append(("ilce_postadan", {}))

    # mahalle / köy: sözlükle doğrula, doğru yazımı al, eksik ilçe/ili mahalleden bul
    for alan in ("mahalle", "koy"):
        if s[alan] and z.mahalle:
            y = z.mahalle_mi(s["il"], s["ilce"], s[alan])
            if y:
                if duzelt:
                    s[alan] = y.ad
                if s["ilce"] is None:
                    s["ilce"] = y.ilce
                    notlar.append(("ilce_mahalleden", {}))
                if s["il"] is None:
                    s["il"] = y.il
                    notlar.append(("il_mahalleden", {}))
            elif s["il"] and s["ilce"] and alan == "mahalle":
                notlar.append(("mahalle_yok", {"a": s[alan]}))

    kalan = [w for w in parca if katla(w) not in _DUR and not w.isdigit()]
    if kalan:
        km = " ".join(kalan)
        m = _TARIF.search(katla(km))
        if m:
            s["tarif"] = km[m.start():m.end()].strip()
            km = (km[:m.start()] + " " + km[m.end():]).strip()
        s["kalan"] = " ".join(km.split()) or None

    if duzelt:
        for alan in ("mahalle", "koy", "yol", "ust_yol", "bina"):
            s[alan] = _sozcuk_duzelt(s[alan], z)

    puan = 1.0 - 0.35 * (s["il"] is None) - 0.2 * (s["ilce"] is None) - 0.15 * (not (s["mahalle"] or s["koy"]))
    puan -= 0.15 * (s["yol"] is None) + 0.1 * (s["no"] is None) + 0.1 * duzeltme + 0.05 * bool(s["kalan"])
    s["guven"] = round(max(0.0, min(1.0, puan)), 2)
    s["notlar"] = notlar
    return s
