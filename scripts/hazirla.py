"""OSM ham verisinden il-ilçe sözlüğü ve sınama seti üretir (ODbL, © OpenStreetMap katkıcıları).
Sınama: il, ilçe, mahalle, yol ve kapı no'su tam ve sözlükle tutarlı adresler; her biri tohumlu biçim, kısaltma ve yazım değişkeniyle metne çevrilir.
Önce ham veri: python scripts/osm_cek.py (ham/ klasörüne, ~125 MB, depoya konmaz).
Kullanım: python scripts/hazirla.py --ad gelistirme --atla 0      (ilk 6000 tekil adres)
          python scripts/hazirla.py --ad sinama --atla 6000      (sonraki 6000, geliştirmede görülmedi)
Çıktı: bench/<ad>.jsonl, bench/ozet_<ad>.json, src/tr_adres/veri/gazetteer.json
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
HAM = KOK / "ham"
ILCE_DEGIL = {"Kara Ada"}
sys.stdout.reconfigure(encoding="utf-8")
TOHUM = 20261108
N = 6000
YOL_TUR = [("bulvar", r"\s+(bulvarı|bulvari|bulvar|blv\.?|bulv\.?)$"), ("cadde", r"\s+(caddesi|cadde|cad\.?|cd\.?)$"), ("sokak", r"\s+(sokağı|sokagi|sokak|sok\.?|sk\.?)$")]


def kucuk(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def katla(s: str) -> str:
    return kucuk(s).translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))


def ascii_buyuk(s: str) -> str:
    return katla(s).upper()


def main() -> None:
    global HAM
    ap = argparse.ArgumentParser()
    ap.add_argument("--ham", type=Path, default=HAM)
    ap.add_argument("--ad", default="sinama")
    ap.add_argument("--atla", type=int, default=0)
    ap.add_argument("--n", type=int, default=N)
    arg = ap.parse_args()
    HAM = arg.ham
    iller = {x["id"]: x["tags"].get("name") for x in json.load(open(HAM / "iller.json", encoding="utf-8")) if x["tags"].get("ISO3166-2", "").startswith("TR-")}
    gaz: dict[str, set] = {}
    adresler = []
    for oid, il in iller.items():
        yer = json.load(open(HAM / f"il_{oid}_yer.json", encoding="utf-8"))
        gaz[il] = {e["tags"]["name"] for e in yer if e["type"] == "relation" and e["tags"].get("admin_level") == "6" and e["tags"].get("name")}
        # sınır komşusu ülkeden sızan ve ilçe olmayan kayıtlar (ör. Yunanca bölge adı, "Kara Ada")
        gaz[il] = {x for x in gaz[il] if x not in ILCE_DEGIL and all(c.isascii() or "À" <= c <= "ɏ" for c in x)}
        for e in json.load(open(HAM / f"il_{oid}_adres.json", encoding="utf-8")):
            t = e.get("tags", {})
            adresler.append((il, t))
    say = collections.Counter()
    temiz = []
    for il, t in adresler:
        say["ham"] += 1
        c, d, m, s, n = (t.get(k, "").strip() for k in ("addr:city", "addr:district", "addr:neighbourhood", "addr:street", "addr:housenumber"))
        if not all((c, d, m, s, n)):
            continue
        say["tam"] += 1
        if katla(c) != katla(il) or katla(d) not in {katla(x) for x in gaz[il]}:
            continue
        ilce = next(x for x in gaz[il] if katla(x) == katla(d))
        mah = re.sub(r"\s+(mahallesi|mahalle|mah\.?|mh\.?)$", "", m, flags=re.I).strip()
        tur = next(((a, re.sub(r, "", s, flags=re.I).strip()) for a, r in YOL_TUR if re.search(r, s, flags=re.I)), None)
        if not tur or not mah or not tur[1] or not re.fullmatch(r"\d+[A-Za-z]?(/\d+[A-Za-z]?)?", n) or katla(mah) == katla(ilce):
            continue
        say["tutarli"] += 1
        temiz.append({"il": il, "ilce": ilce, "mahalle": mah, "yol": tur[1], "yol_turu": tur[0], "no": n.upper(), "posta_kodu": t.get("addr:postcode")})
    tek = list({json.dumps(x, sort_keys=True, ensure_ascii=False): x for x in temiz}.values())
    rnd = random.Random(TOHUM)
    rnd.shuffle(tek)
    MAH = ["Mahallesi", "Mah.", "Mh.", "mah", "MAH."]
    KIS = {"sokak": ["Sokak", "Sk.", "Sok.", "sk"], "cadde": ["Caddesi", "Cad.", "Cd.", "cd"], "bulvar": ["Bulvarı", "Blv.", "Bulv."]}
    BIC = ["kanonik", "buyuk_ascii", "il_basta", "virgullu", "postali", "daireli"]
    with open(KOK / "bench" / f"{arg.ad}.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for i, x in enumerate(tek[arg.atla:arg.atla + arg.n], start=arg.atla):
            b = BIC[i % len(BIC)]
            mh, yk = rnd.choice(MAH), rnd.choice(KIS[x["yol_turu"]])
            no = rnd.choice([f"No:{x['no']}", f"No: {x['no']}", f"no {x['no']}", f"No.{x['no']}"])
            govde = f"{x['mahalle']} {mh} {x['yol']} {yk} {no}"
            ek = {}
            if b == "kanonik":
                metin = f"{govde} {x['ilce']}/{x['il']}"
            elif b == "buyuk_ascii":
                metin = ascii_buyuk(f"{govde} {x['ilce']} {x['il']}")
            elif b == "il_basta":
                metin = f"{x['il']} {x['ilce']} {govde}"
            elif b == "virgullu":
                metin = f"{x['mahalle']} {mh}, {x['yol']} {yk}, {no}, {x['ilce']}, {x['il']}"
            elif b == "postali" and x["posta_kodu"] and re.fullmatch(r"\d{5}", x["posta_kodu"]):
                metin, ek["posta_kodu"] = f"{govde}, {x['posta_kodu']} {x['ilce']}/{x['il']}", x["posta_kodu"]
            else:
                d, k = rnd.randint(1, 30), rnd.randint(1, 12)
                metin, ek = f"{govde} Kat:{k} D:{d} {x['ilce']}/{x['il']}", {"kat": str(k), "ic_kapi": str(d)}
                b = "daireli"
            altin = {"il": x["il"], "ilce": x["ilce"], "mahalle": x["mahalle"], "yol": x["yol"], "yol_turu": x["yol_turu"], "no": x["no"], **ek}
            f.write(json.dumps({"id": f"tradres-{i:05d}", "bicim": b, "metin": metin, "altin": altin}, ensure_ascii=False) + "\n")
    (KOK / "src" / "tr_adres" / "veri" / "gazetteer.json").write_text(json.dumps({"kaynak": "© OpenStreetMap katkıcıları, ODbL 1.0", "iller": {il: {"ilceler": sorted(v)} for il, v in sorted(gaz.items())}}, ensure_ascii=False), encoding="utf-8")
    o = {"il": len(gaz), "ilce": sum(len(v) for v in gaz.values()), "sayac": say, "tekil_tutarli": len(tek), "ad": arg.ad, "atla": arg.atla, "n": len(tek[arg.atla:arg.atla + arg.n])}
    (KOK / "bench" / f"ozet_{arg.ad}.json").write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(o, ensure_ascii=False))


if __name__ == "__main__":
    main()
