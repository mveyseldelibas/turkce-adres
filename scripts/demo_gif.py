"""README için terminal görünümlü demo GIF'i üretir: docs/demo.gif.

Ekrandaki her çıktı, betik çalışırken turkce_adres'in gerçek dönüş değerinden alınır.
Pillow gerekir (paketin kendisi gerektirmez): python scripts/demo_gif.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))
from turkce_adres import format_address, geocode, parse, similarity  # noqa: E402

W, H = 980, 560
BG, FG, PROMPT, OUT, DIM, GOLD = (16, 24, 38), (230, 236, 245), (120, 200, 255), (130, 225, 160), (120, 135, 160), (227, 176, 75)


def font(size):
    for n in ("consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"):
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            pass
    return ImageFont.load_default()


F = font(19)
GIRDI = "CAFERAGA MH MODA CD NO 12 D 3 KADIKOY ISTANBUL"
a = parse(GIRDI)
k = geocode(a, "en")
ADIMLAR = [
    ("from turkce_adres import parse, format_address, geocode, similarity", None),
    (f'a = parse("{GIRDI}")', None),
    ('a["province"], a["district"], a["neighbourhood"], a["street"], a["number"], a["unit"]',
     repr((a["province"], a["district"], a["neighbourhood"], a["street"], a["number"], a["unit"]))),
    ("format_address(a)", repr(format_address(a))),
    ('geocode(a, "en")', repr({"lat": k["lat"], "lon": k["lon"], "level": k["level"]})),
    ('similarity(a, "Caferağa Mahallesi, Moda Caddesi No:12 D:3, Kadıköy/İstanbul")',
     repr(similarity(a, "Caferağa Mahallesi, Moda Caddesi No:12 D:3, Kadıköy/İstanbul"))),
]


def sar(metin, genislik):
    out, s = [], ""
    for w in metin.split(" "):
        aday = (s + " " + w).strip()
        if F.getlength(aday) > genislik and s:
            out.append(s)
            s = w
        else:
            s = aday
    out.append(s)
    return out


def ciz(satirlar):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, 34], radius=0, fill=(28, 38, 58))
    for i, c in enumerate(((255, 95, 87), (255, 189, 46), (39, 201, 63))):
        d.ellipse([16 + i * 22, 11, 28 + i * 22, 23], fill=c)
    d.text((W // 2, 17), "turkce-adres · offline Turkish address parsing", font=font(15), fill=DIM, anchor="mm")
    y = 50
    for tur, metin in satirlar:
        renk = {"komut": FG, "cikti": OUT}[tur]
        ilk = True
        for parca in sar(metin, W - 70):
            if tur == "komut":
                d.text((18, y), ">>>" if ilk else "...", font=F, fill=PROMPT)
            d.text((62, y), parca, font=F, fill=renk)
            y += 27
            ilk = False
        if tur == "cikti":
            y += 8
    d.text((W - 18, H - 14), "pip install turkce-adres", font=font(15), fill=GOLD, anchor="rs")
    return im


def main():
    kareler, sure = [], []
    ekran = []
    for komut, cikti in ADIMLAR:
        for n in range(0, len(komut) + 1, 4):
            kareler.append(ciz(ekran + [("komut", komut[:n] + "▌")]))
            sure.append(35)
        ekran.append(("komut", komut))
        kareler.append(ciz(ekran))
        sure.append(350)
        if cikti:
            ekran.append(("cikti", cikti))
            kareler.append(ciz(ekran))
            sure.append(1400)
    sure[-1] = 4000
    hedef = KOK / "docs" / "demo.gif"
    hedef.parent.mkdir(exist_ok=True)
    paletli = [k.convert("P", palette=Image.Palette.ADAPTIVE, colors=32) for k in kareler]
    paletli[0].save(hedef, save_all=True, append_images=paletli[1:], duration=sure, loop=0, optimize=True)
    print(hedef, len(kareler), "kare", round(hedef.stat().st_size / 1e3), "KB", round(sum(sure) / 1000, 1), "sn")


if __name__ == "__main__":
    main()
