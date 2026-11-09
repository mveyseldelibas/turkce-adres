"""Elle etiketlenmiş zor setin (bench/zor.tsv) ölçümü.

Kurallar (iki paket için de aynı): harf boyu ve Türkçe karakter farkı yok sayılır; "12/3" yazımında dış kapı 12
sayılır; "Kırşehir Merkez" = "Kırşehir" = "Merkez" (merkez ilçe adlandırma farkı); mahalle alanı köyü de kapsar.
Kullanım: python bench/zor_degerlendir.py [--ayrinti]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK.parent / "src"))
from turkce_adres import ayristir, katla  # noqa: E402

ALANLAR = ["il", "ilce", "mahalle", "yol", "yol_turu", "no", "ic_kapi", "kat", "blok", "posta_kodu"]


def oku():
    for ln in (KOK / "zor.tsv").read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        p = ln.split("\t")
        yield p[0], dict(x.split("=", 1) for x in p[1:])


def _n(v) -> str:
    return " ".join(katla(str(v)).split()) if v not in (None, "") else ""


def esit(alan, tahmin, altin, il) -> bool:
    t, g = _n(tahmin), _n(altin)
    if alan == "ilce":
        ik = _n(il)
        t, g = (x.replace(f"{ik} merkez", "merkez") if x != ik else "merkez" for x in (t, g))
    return t == g


def dis_kapi(no, ic):
    if no and ic and str(no).endswith(f"/{ic}"):
        return str(no)[: -len(str(ic)) - 1]
    return no


def puanla(tahmin_fn, ayrinti=False):
    n = tam = 0
    alan_say = {a: [0, 0] for a in ALANLAR}
    hatalar = []
    for metin, altin in oku():
        s = tahmin_fn(metin)
        s = dict(s)
        s["mahalle"] = s.get("mahalle") or s.get("koy")
        s["no"] = dis_kapi(s.get("no"), s.get("ic_kapi"))
        ok = True
        for a in ALANLAR:
            if a not in altin:
                continue
            alan_say[a][1] += 1
            if esit(a, s.get(a), altin[a], altin.get("il")):
                alan_say[a][0] += 1
            else:
                ok = False
                hatalar.append((metin, a, s.get(a), altin[a]))
        n += 1
        tam += ok
    sonuc = {"n": n, "tum_alanlar_dogru": f"{tam}/{n} %{100 * tam / n:.1f}",
             "alan": {a: f"{d}/{t} %{100 * d / t:.1f}" for a, (d, t) in alan_say.items() if t}}
    if ayrinti:
        for h in hatalar:
            print("  ", h)
    return sonuc


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(puanla(ayristir, "--ayrinti" in sys.argv), ensure_ascii=False, indent=1))
