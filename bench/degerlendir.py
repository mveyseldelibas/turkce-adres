"""Ayrıştırıcıyı ölçer. İki set var (OpenStreetMap'ten üretilmiş, ODbL):
  gelistirme.jsonl: kurallar bu sette bakılarak düzeltildi (iyimser sonuç verir)
  sinama.jsonl:     geliştirmede hiç bakılmadı, asıl sonuç budur

Karşılaştırma büyük/küçük harf ve Türkçe karakter farkını yok sayar (CAFERAGA = Caferağa); başka normalleştirme yoktur.
Kullanım: python bench/degerlendir.py [sinama|gelistirme] [--yaz]   (--yaz sonucu bench/sonuc_<set>.json dosyasına yazar)
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK.parent / "src"))
from tr_adres import ayristir, katla  # noqa: E402

ALANLAR = ["il", "ilce", "mahalle", "yol", "yol_turu", "no", "posta_kodu", "kat", "ic_kapi"]


def esit(a, b) -> bool:
    return a is not None and b is not None and " ".join(katla(str(a)).split()) == " ".join(katla(str(b)).split())


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ad = next((a for a in sys.argv[1:] if not a.startswith("-")), "sinama")
    satirlar = [json.loads(x) for x in (KOK / f"{ad}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    alan = collections.defaultdict(lambda: [0, 0])
    bicim = collections.defaultdict(lambda: [0, 0])
    hatalar = []
    for r in satirlar:
        c = ayristir(r["metin"])
        tam = True
        for a in ALANLAR:
            if a not in r["altin"]:
                continue
            alan[a][1] += 1
            if esit(c[a], r["altin"][a]):
                alan[a][0] += 1
            else:
                tam = False
                hatalar.append({"alan": a, "metin": r["metin"], "bulunan": c[a], "altin": r["altin"][a]})
        bicim[r["bicim"]][1] += 1
        bicim[r["bicim"]][0] += tam
    yuzde = lambda d, n: f"{d}/{n} %{100 * d / n:.1f}"  # noqa: E731
    sonuc = {
        "set": ad,
        "n": len(satirlar),
        "tum_alanlar_dogru": yuzde(sum(v[0] for v in bicim.values()), len(satirlar)),
        "alan": {k: yuzde(*v) for k, v in alan.items()},
        "bicim_tam": {k: yuzde(*v) for k, v in bicim.items()},
    }
    print(json.dumps(sonuc, ensure_ascii=False, indent=1))
    tur = collections.Counter(h["alan"] for h in hatalar)
    print("hata sayısı (alan):", dict(tur))
    for h in hatalar[:: max(1, len(hatalar) // 15)][:15]:
        print(json.dumps(h, ensure_ascii=False))
    if "--yaz" in sys.argv:
        sonuc["ornek_hatalar"] = hatalar[:30]
        (KOK / f"sonuc_{ad}.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
