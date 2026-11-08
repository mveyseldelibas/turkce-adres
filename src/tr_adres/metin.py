"""Türkçe harf işlemleri. Hepsi karakter sayısını korur, böylece katlanmış metindeki konumlar özgün metne uyar."""
from __future__ import annotations

import unicodedata

_KATLA = str.maketrans({
    "İ": "i", "I": "i", "ı": "i", "Ç": "c", "ç": "c", "Ğ": "g", "ğ": "g", "Ö": "o", "ö": "o",
    "Ş": "s", "ş": "s", "Ü": "u", "ü": "u", "Â": "a", "â": "a", "Î": "i", "î": "i", "Û": "u", "û": "u",
})


def _tek(c: str) -> str:
    k = c.lower()
    return k if len(k) == 1 else c


def katla(s: str) -> str:
    """Büyük/küçük harf ve Türkçe karakter farkını siler: 'İSTİKLAL' -> 'istiklal', 'Çukurova' -> 'cukurova'."""
    return "".join(_tek(c) for c in s.translate(_KATLA))


def duzle(s: str) -> str:
    """NFC'ye çevirir; ayrık yazılmış noktalı i'yi (i + U+0307) tek harfe indirir."""
    return unicodedata.normalize("NFC", s).replace("i̇", "i")


def kucuk(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def buyuk(c: str) -> str:
    return {"i": "İ", "ı": "I"}.get(c, c.upper())


def _sozcuk(w: str) -> str:
    # Tamamı büyük ve Türkçe harfsiz sözcükte (ISTIKLAL) I'nın ı mı i mi olduğu bilinemez; i daha sık doğru çıkar.
    if w.isupper() and w.isascii():
        k = w.lower()
    else:
        k = kucuk(w)
    return buyuk(k[0]) + k[1:] if k and k[0].isalpha() else k


def buyuk_bas(s: str) -> str:
    """Her sözcüğün ilk harfini Türkçe kurala göre büyütür: 'caferağa' -> 'Caferağa', 'ISTIKLAL' -> 'İstiklal'.
    Büyük ASCII yazımda Türkçe karakter bilgisi yoktur (CAFERAGA -> Caferaga); harfler geri kazanılmaz."""
    out, w = [], ""
    for c in s:
        if c in " '’-/":
            out.append(_sozcuk(w) + c)
            w = ""
        else:
            w += c
    out.append(_sozcuk(w))
    return "".join(out)
