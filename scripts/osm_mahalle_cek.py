"""OpenStreetMap'ten (ODbL) her ilçenin mahalle, köy ve semtlerini merkez koordinatlarıyla çeker. Kaynak yalnız Overpass API.
Devam ettirilebilir; istekler arası bekler. Önce scripts/osm_cek.py ile ham/iller.json oluşmalı (ya da --iller verin).
Çıktı: ham/mahalle/il_<osmid>.json (Overpass öğeleri; her ilçe öğesini o ilçenin mahalleleri izler).
Kullanım: python scripts/osm_mahalle_cek.py [--iller ham/iller.json]   (requests gerekir)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

KOK = Path(__file__).resolve().parents[1]
UC = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "turkce-adres-acik-veri/0.2"}
BEKLE = 10

SORGU = """[out:json][timeout:900];
rel({oid});map_to_area->.il;
rel(area.il)[boundary=administrative][admin_level=6];
foreach->.ilce(
  .ilce out tags;
  .ilce map_to_area->.a;
  (rel(area.a)[boundary=administrative][admin_level~"^(7|8|9|10)$"];
   node(area.a)[place~"^(neighbourhood|quarter|suburb|village|hamlet)$"];);
  out center tags;
);"""


ILCELER = """[out:json][timeout:180];
rel({oid});map_to_area->.il;
rel(area.il)[boundary=administrative][admin_level=6];
out tags;"""

ILCE = """[out:json][timeout:300];
rel({oid});map_to_area->.a;
(rel(area.a)[boundary=administrative][admin_level~"^(7|8|9|10)$"];
 node(area.a)[place~"^(neighbourhood|quarter|suburb|village|hamlet)$"];);
out center tags;"""


def sorgu(q: str, deneme_sayisi: int = 6) -> dict | None:
    for deneme in range(deneme_sayisi):
        try:
            r = requests.post(UC, data={"data": q}, headers=UA, timeout=960)
        except requests.RequestException as e:
            print("  ag", type(e).__name__, flush=True)
            time.sleep(60)
            continue
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                print("  json degil", r.text[:120], flush=True)
        else:
            print("  durum", r.status_code, flush=True)
        time.sleep(60 * (deneme + 1))
    if deneme_sayisi >= 6:
        raise SystemExit("Overpass yanıt vermedi; sonra yeniden çalıştırın")
    return None


def il_cek(oid: int) -> list:
    """Önce tek sorgu; sunucu yetişemezse (504) ilçe ilçe küçük sorgular. Çıktı biçimi aynı: ilçe öğesi, ardından mahalleleri."""
    d = sorgu(SORGU.format(oid=oid), deneme_sayisi=2)
    if d is not None:
        return d["elements"]
    print("  ilçe ilçe çekiliyor", flush=True)
    out = []
    for ilce in sorgu(ILCELER.format(oid=oid))["elements"]:
        out.append(ilce)
        out += sorgu(ILCE.format(oid=ilce["id"]))["elements"]
        time.sleep(3)
    return out


def main() -> None:
    global UC
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--iller", type=Path, default=KOK / "ham" / "iller.json")
    ap.add_argument("--cikti", type=Path, default=KOK / "ham" / "mahalle")
    ap.add_argument("--uc", default=UC, help="Overpass adresi")
    ap.add_argument("--ters", action="store_true", help="illeri ters sırada çek (ikinci süreç için)")
    a = ap.parse_args()
    UC = a.uc
    a.cikti.mkdir(parents=True, exist_ok=True)
    iller = [x for x in json.loads(a.iller.read_text(encoding="utf-8")) if x["tags"].get("ISO3166-2", "").startswith("TR-")]
    for i, il in enumerate(sorted(iller, key=lambda x: x["tags"].get("name", ""), reverse=a.ters)):
        y = a.cikti / f"il_{il['id']}.json"
        if not y.exists():
            y.write_text(json.dumps(il_cek(il["id"]), ensure_ascii=False), encoding="utf-8")
            time.sleep(BEKLE)
        n = len(json.loads(y.read_text(encoding="utf-8")))
        print(i + 1, il["tags"].get("name"), n, "öğe", flush=True)


if __name__ == "__main__":
    main()
