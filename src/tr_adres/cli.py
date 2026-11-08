"""Komut satırı: tek adres ya da CSV dosyası.

    tr-adres "Caferağa Mah. Moda Cad. No:12 Kadıköy/İstanbul"
    tr-adres adresler.csv --sutun adres -o sonuc.csv
    tr-adres adresler.csv --sutun adres --dil en
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import __version__, ayristir, bicimle
from .ayristirici import ALANLAR
from .dil import ALAN_EN

M = {
    "tr": {
        "aciklama": "Dağınık yazılmış Türkçe adresleri alanlarına ayırır (il, ilçe, mahalle, sokak, no...). Çevrimdışı çalışır.",
        "girdi": "adres metni ya da .csv dosyası ('-' = standart girdi, satır başına bir adres)",
        "sutun": "CSV'de adres sütununun adı (verilmezse ilk sütun)",
        "cikti": "çıktı dosyası (verilmezse standart çıktı)",
        "dil": "alan adlarının dili: tr ya da en",
        "bicim": "her adrese standart yazım sütunu ekle",
        "ayrac": "CSV ayracı (verilmezse kendisi bulur)",
        "yok": "sütun bulunamadı: {s}. Sütunlar: {l}",
        "bitti": "{n} adres ayrıştırıldı -> {c}",
        "standart": "standart_adres",
        "onek": "uyarı: dosyadaki bir sütun adı yeni alanlarla aynı; yeni sütunlar '{o}' ön ekiyle yazıldı",
    },
    "en": {
        "aciklama": "Splits messy Turkish addresses into fields (province, district, neighbourhood, street, number...). Works offline.",
        "girdi": "address text or a .csv file ('-' = stdin, one address per line)",
        "sutun": "name of the address column in the CSV (default: first column)",
        "cikti": "output file (default: stdout)",
        "dil": "language of field names: tr or en",
        "bicim": "add a standardised address column",
        "ayrac": "CSV delimiter (auto-detected if omitted)",
        "yok": "column not found: {s}. Columns: {l}",
        "bitti": "{n} addresses parsed -> {c}",
        "standart": "formatted_address",
        "onek": "warning: a column in the file has the same name as a new field; new columns are prefixed with '{o}'",
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


def _csv(yol: str, a: argparse.Namespace, m: dict, dil: str) -> int:
    satirlar, basliklar, sutun, ayrac = _oku(yol, a)
    if not satirlar:
        return 0
    if sutun not in basliklar:
        print(m["yok"].format(s=sutun, l=", ".join(basliklar)), file=sys.stderr)
        return 2
    alanlar = [ALAN_EN[k] if dil == "en" else k for k in ALANLAR] + ([m["standart"]] if a.bicim else [])
    # Kullanıcının sütunlarından biri (ör. "no", "il") yeni alanlarla çakışırsa hiçbir sütun ezilmez:
    # bütün yeni sütunlar ön ek alır.
    onek = "tr_adres_" if set(alanlar) & set(basliklar) else ""
    if onek:
        print(m["onek"].format(o=onek), file=sys.stderr)
    hedef = open(a.cikti, "w", encoding="utf-8-sig", newline="") if a.cikti else sys.stdout
    with hedef:
        w = csv.DictWriter(hedef, fieldnames=basliklar + [onek + x for x in alanlar], delimiter=ayrac)
        w.writeheader()
        for r in satirlar:
            s = ayristir(r.get(sutun) or "", dil)
            if a.bicim:
                s[m["standart"]] = bicimle(s)
            r.update({onek + k: ("" if v is None else v) for k, v in s.items()})
            w.writerow(r)
    if a.cikti:
        print(m["bitti"].format(n=len(satirlar), c=a.cikti), file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dil = _dil_on(argv)
    m = M[dil]
    p = argparse.ArgumentParser(prog="tr-adres", description=m["aciklama"])
    p.add_argument("girdi", help=m["girdi"])
    p.add_argument("--sutun", "--column", help=m["sutun"])
    p.add_argument("-o", "--cikti", "--output", help=m["cikti"])
    p.add_argument("--dil", "--lang", default="tr", choices=["tr", "en"], help=m["dil"])
    p.add_argument("--bicim", "--format", action="store_true", help=m["bicim"])
    p.add_argument("--ayrac", "--delimiter", help=m["ayrac"])
    p.add_argument("--version", action="version", version=f"tr-adres {__version__}")
    a = p.parse_args(argv)
    for akis in (sys.stdout, sys.stderr):
        if hasattr(akis, "reconfigure"):
            akis.reconfigure(encoding="utf-8")
    if a.girdi == "-" or (a.girdi.lower().endswith((".csv", ".tsv", ".txt")) and Path(a.girdi).is_file()):
        return _csv(a.girdi, a, m, dil)
    s = ayristir(a.girdi, dil)
    if a.bicim:
        s[m["standart"]] = bicimle(s)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
