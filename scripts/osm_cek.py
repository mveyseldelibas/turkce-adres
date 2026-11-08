"""OpenStreetMap'ten (ODbL) Türkiye adres verisini il il çeker. Kaynak yalnız Overpass API. Devam ettirilebilir, istekler arası bekler.
Çıktı: ham/iller.json, ham/il_<osmid>_adres.json, ham/il_<osmid>_yer.json. Kullanım: python scripts/osm_cek.py (requests gerekir)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

KOK = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
HAM = KOK / "ham"
UC = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "tr-adres-acik-veri/0.1"}
BEKLE = 8


def sorgu(q: str) -> dict:
    for deneme in range(6):
        try:
            r = requests.post(UC, data={"data": q}, headers=UA, timeout=330)
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
        time.sleep(90 * (deneme + 1))
    raise SystemExit("Overpass yanıt vermedi; sonra yeniden çalıştırın")


def main() -> None:
    HAM.mkdir(exist_ok=True)
    yol = HAM / "iller.json"
    if not yol.exists():
        d = sorgu('[out:json][timeout:120];area["ISO3166-1"="TR"][admin_level=2]->.t;rel(area.t)[boundary=administrative][admin_level=4];out tags;')
        yol.write_text(json.dumps(d["elements"], ensure_ascii=False), encoding="utf-8")
        time.sleep(BEKLE)
    iller = json.loads(yol.read_text(encoding="utf-8"))
    print("il", len(iller), flush=True)
    for i, il in enumerate(sorted(iller, key=lambda x: x["tags"].get("name", ""))):
        ad, oid = il["tags"].get("name", "?"), il["id"]
        alan = 3600000000 + oid
        y1, y2 = HAM / f"il_{oid}_adres.json", HAM / f"il_{oid}_yer.json"
        if not y1.exists():
            d = sorgu(f'[out:json][timeout:300];area({alan})->.a;nwr["addr:street"]["addr:housenumber"](area.a);out tags center;')
            y1.write_text(json.dumps(d["elements"], ensure_ascii=False), encoding="utf-8")
            time.sleep(BEKLE)
        if not y2.exists():
            d = sorgu(f'[out:json][timeout:300];area({alan})->.a;(rel(area.a)[boundary=administrative][admin_level~"^(6|8|9|10)$"];node(area.a)[place~"^(suburb|neighbourhood|quarter|village)$"];way(area.a)[highway~"^(primary|secondary|tertiary|residential|unclassified|living_street)$"][name];);out tags;')
            y2.write_text(json.dumps(d["elements"], ensure_ascii=False), encoding="utf-8")
            time.sleep(BEKLE)
        print(i + 1, ad, y1.stat().st_size // 1024, "KB", y2.stat().st_size // 1024, "KB", flush=True)


if __name__ == "__main__":
    main()
