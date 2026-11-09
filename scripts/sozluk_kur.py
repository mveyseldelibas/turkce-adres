"""OSM ham verisinden paketin genişletilmiş sözlüklerini kurar (hepsi © OpenStreetMap katkıcıları, ODbL 1.0):

  src/turkce_adres/veri/mahalle.json.gz : il -> ilçe -> [ad, tür, enlem, boylam]  (+ ilçe ve il merkezleri)
  src/turkce_adres/veri/sokak.json.gz   : "il|ilçe|yol#tür" -> [enlem, boylam, adres sayısı]; posta kodu -> [ilçe, il]
  src/turkce_adres/veri/kelime.json.gz  : ASCII yazım -> Türkçe yazım (yer ve yol adlarındaki sözcüklerden)

Posta kodu tablosu yalnız OSM'deki adres etiketlerinden türetilir (PTT listesi kullanılmaz).
Kullanım: python scripts/sozluk_kur.py --ham <osm_cek.py çıktısı> --mahalle ham/mahalle
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import statistics
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))
from turkce_adres.metin import buyuk_bas, katla  # noqa: E402
from turkce_adres.ozellik import sokak_anahtar  # noqa: E402
from turkce_adres.sozluk import _mah_anahtar  # noqa: E402

VERI = KOK / "src" / "turkce_adres" / "veri"
YOL_TUR = [("bulvar", r"\s+(bulvarı|bulvari|bulvar|blv\.?|bulv\.?)$"), ("cadde", r"\s+(caddesi|cadde|cad\.?|cd\.?)$"),
           ("sokak", r"\s+(sokağı|sokagi|sokak|sok\.?|sk\.?)$")]
TR_HARF = set("çğıöşüÇĞİÖŞÜâîûÂÎÛ")
LATIN = lambda s: all(c.isascii() or "À" <= c <= "ɏ" for c in s)  # noqa: E731


def ad_temizle(ad: str) -> tuple[str, str | None]:
    """'Caferağa Mahallesi' -> ('Caferağa', 'mahalle'), 'Yeniköy Köyü' -> ('Yeniköy', 'koy'),
    'Yeni Mahalle Mahallesi' -> ('Yeni', 'mahalle') (ekler tümüyle atılır; kullanıcı 'Yeni Mah.' yazar)."""
    a, bulunan = ad.strip(), None
    degisti = True
    while degisti:
        degisti = False
        for desen, tur in ((r"\s+(mahallesi|mahalle|mah\.?|mh\.?)$", "mahalle"), (r"\s+(köyü|koyu)$", "koy")):
            if re.search(desen, a, flags=re.I) and len(a.split()) > 1:
                a, bulunan, degisti = re.sub(desen, "", a, flags=re.I).strip(), bulunan or tur, True
    return a, bulunan


def gz_yaz(ad: str, veri) -> int:
    b = gzip.compress(json.dumps(veri, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), compresslevel=9, mtime=0)
    (VERI / ad).write_bytes(b)
    return len(b)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ham", type=Path, required=True, help="osm_cek.py çıktısı (iller.json, il_*_adres.json, il_*_yer.json)")
    ap.add_argument("--mahalle", type=Path, default=KOK / "ham" / "mahalle", help="osm_mahalle_cek.py çıktısı")
    a = ap.parse_args()

    gaz = json.loads((VERI / "gazetteer.json").read_text(encoding="utf-8"))["iller"]
    ilce_bul = {(katla(il), katla(ilce)): (ilce, il) for il, v in gaz.items() for ilce in v["ilceler"]}
    il_bul = {katla(il): il for il in gaz}
    iller = {x["id"]: x["tags"].get("name") for x in json.loads((a.ham / "iller.json").read_text(encoding="utf-8"))
             if x["tags"].get("ISO3166-2", "").startswith("TR-")}

    # ---------------- mahalle / köy
    mahalle: dict[str, dict[str, dict[str, list]]] = {}
    kelime_say: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    eksik_il = []
    for oid, il_ad in iller.items():
        y = a.mahalle / f"il_{oid}.json"
        il = il_bul.get(katla(il_ad or ""))
        if not y.exists() or not il:
            eksik_il.append(il_ad)
            continue
        cur = None
        # önce resmî sınırlar (relation), sonra yer noktaları (node)
        ogeler = json.loads(y.read_text(encoding="utf-8"))
        sirali = []
        for e in ogeler:
            if e["type"] == "relation" and e["tags"].get("admin_level") == "6":
                cur = ilce_bul.get((katla(il), katla(e["tags"].get("name", ""))))
                continue
            if cur:
                sirali.append((0 if e["type"] == "relation" else 1, cur, e))
        for _, (ilce, _il), e in sorted(sirali, key=lambda x: x[0]):
            t = e["tags"]
            ham_ad = t.get("name:tr") or t.get("name")
            if not ham_ad or not LATIN(ham_ad):
                continue
            ad, tur = ad_temizle(ham_ad)
            if not ad or re.fullmatch(r"[\d\s.]+", ad):
                continue
            if tur is None:
                tur = {"village": "koy", "hamlet": "koy", "suburb": "semt"}.get(t.get("place", ""), "mahalle")
            c = e.get("center") or ({"lat": e["lat"], "lon": e["lon"]} if "lat" in e else None)
            if not c:
                continue
            d = mahalle.setdefault(il, {}).setdefault(ilce, {})
            k = _mah_anahtar(ad)
            if k not in d:
                d[k] = [ad, tur, round(c["lat"], 5), round(c["lon"], 5)]
            for w in ad.split():
                kelime_say[katla(w)][buyuk_bas(w)] += 1
    ilce_merkez, il_merkez = {}, {}
    for il, ilceler in mahalle.items():
        noktalar_il = []
        for ilce, d in ilceler.items():
            en = [v[2] for v in d.values()]
            boy = [v[3] for v in d.values()]
            if en:
                ilce_merkez[f"{il}|{ilce}"] = [round(statistics.median(en), 5), round(statistics.median(boy), 5)]
                noktalar_il.append(ilce_merkez[f"{il}|{ilce}"])
        if noktalar_il:
            il_merkez[il] = [round(statistics.median(p[0] for p in noktalar_il), 5),
                             round(statistics.median(p[1] for p in noktalar_il), 5)]
    mah_cikti = {"kaynak": "© OpenStreetMap katkıcıları, ODbL 1.0",
                 "iller": {il: {ilce: sorted(d.values()) for ilce, d in sorted(v.items())} for il, v in sorted(mahalle.items())},
                 "ilce_merkez": ilce_merkez, "il_merkez": il_merkez}
    n_mah = sum(len(d) for v in mahalle.values() for d in v.values())

    # ---------------- sokak merkezleri, posta kodu
    sokak = collections.defaultdict(list)
    posta = collections.defaultdict(collections.Counter)
    for oid, il_ad in iller.items():
        il = il_bul.get(katla(il_ad or ""))
        y = a.ham / f"il_{oid}_adres.json"
        if not il or not y.exists():
            continue
        for e in json.loads(y.read_text(encoding="utf-8")):
            t = e.get("tags", {})
            d, s, pk = (t.get(k, "").strip() for k in ("addr:district", "addr:street", "addr:postcode"))
            ic = ilce_bul.get((katla(il), katla(d)))
            if not ic:
                continue
            ilce = ic[0]
            if re.fullmatch(r"\d{5}", pk) and int(pk[:2]) <= 81:
                posta[pk][(ilce, il)] += 1
            c = e.get("center") or ({"lat": e["lat"], "lon": e["lon"]} if "lat" in e else None)
            tur = next(((ad, re.sub(r, "", s, flags=re.I).strip()) for ad, r in YOL_TUR if re.search(r, s, flags=re.I)), None)
            if not c or not tur or not tur[1]:
                continue
            sokak[f"{il}|{ilce}|{sokak_anahtar(tur[1], tur[0])}"].append((c["lat"], c["lon"]))
            for w in tur[1].split():
                kelime_say[katla(w)][buyuk_bas(w)] += 1
        yer = a.ham / f"il_{oid}_yer.json"
        if yer.exists():
            for e in json.loads(yer.read_text(encoding="utf-8")):
                n = e.get("tags", {}).get("name")
                if e["type"] == "way" and n and LATIN(n):
                    for w in n.split():
                        kelime_say[katla(w)][buyuk_bas(w)] += 1
    sokak_cikti = {k: [round(statistics.median(p[0] for p in v), 5), round(statistics.median(p[1] for p in v), 5), len(v)]
                   for k, v in sokak.items()}
    posta_cikti = {}
    for pk, c in posta.items():
        (ilce_il, n), toplam = c.most_common(1)[0], sum(c.values())
        if n >= 3 and n / toplam >= 0.8:
            posta_cikti[pk] = list(ilce_il)

    # ---------------- yazım sözlüğü: yalnız Türkçe harf içeren ve yazımı tutarlı sözcükler
    kelime = {}
    for k, c in kelime_say.items():
        (yazim, n), toplam = c.most_common(1)[0], sum(c.values())
        if len(k) >= 3 and toplam >= 2 and n / toplam >= 0.9 and any(ch in TR_HARF for ch in yazim) and k.isalpha():
            kelime[k] = yazim

    b1 = gz_yaz("mahalle.json.gz", mah_cikti)
    b2 = gz_yaz("sokak.json.gz", {"kaynak": "© OpenStreetMap katkıcıları, ODbL 1.0", "sokak": sokak_cikti, "posta": posta_cikti})
    b3 = gz_yaz("kelime.json.gz", {"kaynak": "© OpenStreetMap katkıcıları, ODbL 1.0", "kelime": dict(sorted(kelime.items()))})
    ozet = {"mahalle_koy_semt": n_mah, "il_mahalleli": len(mahalle), "ilce_mahalleli": len(ilce_merkez),
            "sokak": len(sokak_cikti), "posta_kodu": len(posta_cikti), "kelime": len(kelime),
            "bayt": {"mahalle": b1, "sokak": b2, "kelime": b3}, "mahalle_verisi_olmayan_iller": eksik_il}
    (KOK / "bench" / "ozet_sozluk.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(ozet, ensure_ascii=False))


if __name__ == "__main__":
    main()
