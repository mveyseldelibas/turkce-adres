"""Komut satırı: tek adres ya da CSV dosyası.

    turkce-adres "Caferağa Mah. Moda Cad. No:12 Kadıköy/İstanbul" --konum
    turkce-adres adresler.csv --sutun adres --bicim --konum --eksik --tekil -o sonuc.csv
    turkce-adres adresler.csv --sutun adres --genellestir mahalle -o paylasim.csv
    turkce-adres adresler.csv --sutun adres --dil en
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import __version__, ayristir, bicimle
from .ayristirici import ALANLAR, EK_ALANLAR
from .dil import ALAN_EN
from .ozellik import _DUZEYLER, benzerlik, eksikler, eslestirme_anahtari, genellestir, konum

M = {
    "tr": {
        "aciklama": "Dağınık yazılmış Türkçe adresleri alanlarına ayırır (il, ilçe, mahalle, sokak, no...), standart "
                    "yazıma çevirir, yaklaşık konum verir, tekrarlanan adresleri bulur. İnternetsiz çalışır.",
        "girdi": "adres metni ya da .csv dosyası ('-' = standart girdi, satır başına bir adres)",
        "sutun": "CSV'de adres sütununun adı (verilmezse ilk sütun)",
        "cikti": "çıktı dosyası (verilmezse standart çıktı)",
        "dil": "alan adlarının dili: tr ya da en",
        "bicim": "standart yazım sütunu ekle (kargo biçimi)",
        "resmi": "standart yazımı resmî biçimde yaz (Mahallesi, Caddesi, Dış Kapı No...)",
        "konum": "internetsiz yaklaşık konum sütunları ekle (enlem, boylam, düzey)",
        "eksik": "teslimat için eksik öğeler sütunu ekle",
        "tekil": "aynı yeri gösteren kayıtları bul (tekil_grup sütunu)",
        "genel": "KVKK için genelleştir: yalnız bu düzeye kadar yaz (il, ilce, mahalle, yol)",
        "ham": "yazımı düzeltme (ASCII sözcükleri yazıldığı gibi bırak)",
        "ayrac": "CSV ayracı (verilmezse kendisi bulur)",
        "yok": "sütun bulunamadı: {s}. Sütunlar: {l}",
        "bitti": "{n} adres işlendi -> {c}",
        "standart": "standart_adres",
        "tekil_grup": "tekil_grup",
        "eksikler": "eksikler",
        "onek": "uyarı: dosyadaki bir sütun adı yeni alanlarla aynı; yeni sütunlar '{o}' ön ekiyle yazıldı",
        "tekil_ozet": "{g} grupta {n} tekrar eden kayıt bulundu",
    },
    "en": {
        "aciklama": "Splits messy Turkish addresses into fields (province, district, neighbourhood, street, number...), "
                    "standardises them, gives approximate locations and finds duplicates. Works offline.",
        "girdi": "address text or a .csv file ('-' = stdin, one address per line)",
        "sutun": "name of the address column in the CSV (default: first column)",
        "cikti": "output file (default: stdout)",
        "dil": "language of field names: tr or en",
        "bicim": "add a standardised address column (cargo style)",
        "resmi": "write the standardised address in official style",
        "konum": "add offline approximate location columns (lat, lon, level)",
        "eksik": "add a column listing what is missing for delivery",
        "tekil": "find records that point to the same place (duplicate_group column)",
        "genel": "generalise for privacy: keep only down to this level (il, ilce, mahalle, yol)",
        "ham": "do not correct spelling (leave ASCII words as written)",
        "ayrac": "CSV delimiter (auto-detected if omitted)",
        "yok": "column not found: {s}. Columns: {l}",
        "bitti": "{n} addresses processed -> {c}",
        "standart": "formatted_address",
        "tekil_grup": "duplicate_group",
        "eksikler": "missing",
        "onek": "warning: a column in the file has the same name as a new field; new columns are prefixed with '{o}'",
        "tekil_ozet": "{n} duplicate records found in {g} groups",
    },
}


def _dil_on(argv: list[str]) -> str:
    for i, a in enumerate(argv):
        if a in ("--dil", "--lang") and i + 1 < len(argv):
            return "en" if argv[i + 1].lower() == "en" else "tr"
        if a.startswith(("--dil=", "--lang=")):
            return "en" if a.split("=", 1)[1].lower() == "en" else "tr"
    return "tr"


def _oku(yol: str, a: argparse.Namespace) -> tuple[list[dict], list[str], str, str]:
    """CSV dosyası ya da standart girdi (satır başına bir adres) -> (satırlar, başlıklar, adres sütunu, ayraç)."""
    if yol == "-":
        satirlar = [{"adres": x.strip()} for x in sys.stdin if x.strip()]
        return satirlar, ["adres"], "adres", a.ayrac or ","
    metin = Path(yol).read_text(encoding="utf-8-sig")
    try:
        ayrac = a.ayrac or csv.Sniffer().sniff(metin[:8192], delimiters=",;\t|").delimiter
    except csv.Error:
        ayrac = ","  # tek sütunlu dosya
    okuyucu = csv.DictReader(metin.splitlines(), delimiter=ayrac)
    satirlar = list(okuyucu)
    basliklar = list(okuyucu.fieldnames or [])
    return satirlar, basliklar, a.sutun or (basliklar[0] if basliklar else ""), ayrac


def _ek_sutunlar(a, dil: str, m: dict) -> list[str]:
    tr = dil == "tr"
    if a.genellestir:
        alanlar = [k for k in _DUZEYLER[a.genellestir]] + ["metin"]
        return [k if tr else ALAN_EN.get(k, "text" if k == "metin" else k) for k in alanlar]
    out = [ALAN_EN[k] if not tr else k for k in (*ALANLAR, *EK_ALANLAR)]
    if a.bicim or a.resmi:
        out.append(m["standart"])
    if a.konum:
        out += ["enlem", "boylam", "konum_duzeyi"] if tr else ["lat", "lon", "location_level"]
    if a.eksik:
        out.append(m["eksikler"])
    if a.tekil:
        out.append(m["tekil_grup"])
    return out


def _isle(adres: str, a, dil: str, m: dict) -> dict:
    tr = dil == "tr"
    if a.genellestir:
        g = genellestir(adres, a.genellestir, dil)
        alanlar = _DUZEYLER[a.genellestir]
        return {(k if tr else ALAN_EN.get(k, k)): g.get(k if tr else ALAN_EN.get(k, k)) for k in alanlar} | \
               {("metin" if tr else "text"): g.get("metin" if tr else "text", g.get("metin"))}
    s = ayristir(adres, dil, duzelt=not a.ham)
    if a.bicim or a.resmi:
        s[m["standart"]] = bicimle(s, "resmi" if a.resmi else "kargo")
    if a.konum:
        k = konum(s)
        e, b, d = (k["enlem"], k["boylam"], k["duzey"]) if k else (None, None, None)
        if not tr and d:
            d = {"sokak": "street", "mahalle": "neighbourhood", "ilce": "district", "il": "province"}[d]
        s.update(dict(zip(["enlem", "boylam", "konum_duzeyi"] if tr else ["lat", "lon", "location_level"], (e, b, d))))
    if a.eksik:
        s[m["eksikler"]] = "; ".join(eksikler(s, dil))
    return s


def _tekil_gruplar(sonuclar: list[dict]) -> list[str | None]:
    """Aynı il|ilçe|mahalle anahtarındaki kayıtları benzerlikle karşılaştırıp grup numarası verir."""
    bloklar: dict[str, list[int]] = {}
    for i, s in enumerate(sonuclar):
        bloklar.setdefault(eslestirme_anahtari(s), []).append(i)
    ust = list(range(len(sonuclar)))

    def bul(x):
        while ust[x] != x:
            ust[x] = ust[ust[x]]
            x = ust[x]
        return x
    for idx in bloklar.values():
        for p in range(len(idx)):
            for q in range(p + 1, len(idx)):
                if benzerlik(sonuclar[idx[p]], sonuclar[idx[q]]) >= 0.9:
                    ust[bul(idx[q])] = bul(idx[p])
    kok = [bul(i) for i in range(len(sonuclar))]
    say: dict[int, int] = {}
    for k in kok:
        say[k] = say.get(k, 0) + 1
    numara: dict[int, int] = {}
    out = []
    for k in kok:
        if say[k] < 2:
            out.append(None)
        else:
            numara.setdefault(k, len(numara) + 1)
            out.append(str(numara[k]))
    return out


def _yaz_deger(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return "; ".join(map(str, v))
    return v


def _csv(yol: str, a: argparse.Namespace, m: dict, dil: str) -> int:
    satirlar, basliklar, sutun, ayrac = _oku(yol, a)
    if not satirlar:
        return 0
    if sutun not in basliklar:
        print(m["yok"].format(s=sutun, l=", ".join(basliklar)), file=sys.stderr)
        return 2
    alanlar = _ek_sutunlar(a, dil, m)
    # Kullanıcının sütunlarından biri (ör. "no", "il") yeni alanlarla çakışırsa hiçbir sütun ezilmez:
    # bütün yeni sütunlar ön ek alır.
    onek = "adres_" if set(alanlar) & set(basliklar) else ""
    if onek:
        print(m["onek"].format(o=onek), file=sys.stderr)
    sonuclar = [_isle(r.get(sutun) or "", a, dil, m) for r in satirlar]
    if a.tekil:
        gruplar = _tekil_gruplar([ayristir(r.get(sutun) or "") for r in satirlar])
        for s, g in zip(sonuclar, gruplar):
            s[m["tekil_grup"]] = g
        tek = [g for g in gruplar if g]
        print(m["tekil_ozet"].format(n=len(tek), g=len(set(tek))), file=sys.stderr)
    hedef = open(a.cikti, "w", encoding="utf-8-sig", newline="") if a.cikti else sys.stdout
    with hedef:
        w = csv.DictWriter(hedef, fieldnames=basliklar + [onek + x for x in alanlar], delimiter=ayrac, extrasaction="ignore")
        w.writeheader()
        for r, s in zip(satirlar, sonuclar):
            r.update({onek + k: _yaz_deger(v) for k, v in s.items()})
            w.writerow(r)
    if a.cikti:
        print(m["bitti"].format(n=len(satirlar), c=a.cikti), file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dil = _dil_on(argv)
    m = M[dil]
    p = argparse.ArgumentParser(prog="turkce-adres", description=m["aciklama"])
    p.add_argument("girdi", help=m["girdi"])
    p.add_argument("--sutun", "--column", help=m["sutun"])
    p.add_argument("-o", "--cikti", "--output", help=m["cikti"])
    p.add_argument("--dil", "--lang", default="tr", choices=["tr", "en"], help=m["dil"])
    p.add_argument("--bicim", "--format", action="store_true", help=m["bicim"])
    p.add_argument("--resmi", "--official", action="store_true", help=m["resmi"])
    p.add_argument("--konum", "--geocode", action="store_true", help=m["konum"])
    p.add_argument("--eksik", "--missing", action="store_true", help=m["eksik"])
    p.add_argument("--tekil", "--dedupe", action="store_true", help=m["tekil"])
    p.add_argument("--genellestir", "--generalise", choices=list(_DUZEYLER), help=m["genel"])
    p.add_argument("--ham", "--raw", action="store_true", help=m["ham"])
    p.add_argument("--ayrac", "--delimiter", help=m["ayrac"])
    p.add_argument("--version", action="version", version=f"turkce-adres {__version__}")
    a = p.parse_args(argv)
    for akis in (sys.stdout, sys.stderr):
        if hasattr(akis, "reconfigure"):
            akis.reconfigure(encoding="utf-8")
    if a.girdi == "-" or (a.girdi.lower().endswith((".csv", ".tsv", ".txt")) and Path(a.girdi).is_file()):
        return _csv(a.girdi, a, m, dil)
    print(json.dumps(_isle(a.girdi, a, dil, m), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
