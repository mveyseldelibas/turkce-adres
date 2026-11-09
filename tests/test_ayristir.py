import csv
import io
import json

import pytest

from turkce_adres import ayristir, bicimle, parse
from turkce_adres.cli import main

DURUMLAR = [
    ("Caferağa Mah. Moda Cad. No:12 D:3 Kadıköy/İstanbul",
     {"mahalle": "Caferağa", "yol": "Moda", "yol_turu": "cadde", "no": "12", "ic_kapi": "3", "ilce": "Kadıköy", "il": "İstanbul"}),
    ("CAFERAGA MH MODA CD NO 12 DAIRE 3 KADIKOY ISTANBUL",
     {"mahalle": "Caferağa", "yol": "Moda", "yol_turu": "cadde", "no": "12", "ic_kapi": "3", "ilce": "Kadıköy", "il": "İstanbul"}),
    ("Güzelyalı Mahallesi, Turgut Özal Bulvarı No: 102, 01170 Çukurova/Adana",
     {"mahalle": "Güzelyalı", "yol": "Turgut Özal", "yol_turu": "bulvar", "no": "102", "posta_kodu": "01170", "ilce": "Çukurova", "il": "Adana"}),
    ("Serdivan Sakarya Kemalpaşa mah 2320 sk no:5/A kat 2",
     {"mahalle": "Kemalpaşa", "yol": "2320", "yol_turu": "sokak", "no": "5/A", "kat": "2", "ilce": "Serdivan", "il": "Sakarya"}),
    ("Atatürk Bulvarı 45. Sokak No 7, Çankaya, Ankara",
     {"yol": "45.", "yol_turu": "sokak", "ust_yol": "Atatürk Bulvarı", "no": "7", "ilce": "Çankaya", "il": "Ankara"}),
    ("Seyhan Adana", {"ilce": "Seyhan", "il": "Adana"}),
    # 5 haneli sokak adı posta kodu sanılmaz
    ("Kayacık Mahallesi 14027 Sk. No:14 Bandırma/Balıkesir", {"yol": "14027", "yol_turu": "sokak", "posta_kodu": None, "ilce": "Bandırma"}),
    ("Bentbaşı mah 20019 sk no 7, 10200 Bandırma/Balıkesir", {"yol": "20019", "posta_kodu": "10200", "il": "Balıkesir"}),
    # rakamla başlayan ilçe, il başta
    ("Samsun 19 Mayıs Fındıklı Mah. Yesifler Sokak No.2/2", {"il": "Samsun", "ilce": "19 Mayıs", "mahalle": "Fındıklı", "yol": "Yesifler", "no": "2/2"}),
    # yer adıyla başlayan gerçek adlar korunur
    ("Fatih Sultan Mehmet mah, Poligon Caddesi, No.8C/1, Ümraniye, İstanbul", {"mahalle": "Fatih Sultan Mehmet", "ilce": "Ümraniye", "no": "8C/1"}),
    ("Cumhuriyet Mahallesi Gürpınar Yolu Caddesi no 1, 34500 Büyükçekmece/İstanbul", {"yol": "Gürpınar Yolu", "ilce": "Büyükçekmece"}),
    ("Balıkesir Bandırma Kayacık MAH. Çanakkale Şehitleri sk No.2/1A", {"il": "Balıkesir", "yol": "Çanakkale Şehitleri"}),
    # eğik çizgili sokak numarası
    ("İzmir Buca İnönü Mahallesi 678/2. sk no 1", {"il": "İzmir", "ilce": "Buca", "mahalle": "İnönü", "yol": "678/2.", "no": "1"}),
    ("HASIRLI MH. YENI KAPI SK. NO.64 SUR DIYARBAKIR", {"yol": "Yeni Kapı", "il": "Diyarbakır", "ilce": "Sur"}),
    # bina adı önceki mahalle/cadde adını yutmaz
    ("Esentepe Mahallesi Büyükdere Caddesi Levent Plaza No 173 Şişli İstanbul Türkiye",
     {"mahalle": "Esentepe", "yol": "Büyükdere", "bina": "Levent Plaza", "no": "173", "ilce": "Şişli"}),
    ("Barbaros Bulvarı Yıldız İş Merkezi No:145 Kat:4 Beşiktaş", {"yol": "Barbaros", "yol_turu": "bulvar", "bina": "Yıldız İş Merkezi", "il": "İstanbul"}),
    # "No" yazılmadan kapı numarası
    ("kızılay meydanı ziya gökalp cd 12 çankaya ankara", {"no": "12", "yol_turu": "cadde", "ilce": "Çankaya"}),
    ("Hürriyet Cad. 25/3 Merkez Kars", {"no": "25/3", "il": "Kars", "ilce": "Kars Merkez"}),
    ("Yeni Mah. 1203 Sok. No 4 Daire 7", {"yol": "1203", "no": "4", "ic_kapi": "7"}),
    # posta kodundan il
    ("Moda Cad. No:5 34710", {"il": "İstanbul", "posta_kodu": "34710"}),
    ("", {"il": None, "yol": None, "kalan": None}),
]


@pytest.mark.parametrize("girdi,bek", DURUMLAR, ids=[d[0][:40] or "bos" for d in DURUMLAR])
def test_ayristir(girdi, bek):
    s = ayristir(girdi)
    for k, v in bek.items():
        assert s[k] == v, (k, s)


def test_ham_yazim():
    s = ayristir("CAFERAGA MH MODA CD NO 12 KADIKOY ISTANBUL", duzelt=False)
    assert s["mahalle"] == "CAFERAGA" and s["yol"] == "MODA" and s["ilce"] == "Kadıköy"


def test_ilceden_il():
    assert ayristir("Moda Cad. No:1 Kadıköy")["il"] == "İstanbul"
    # il yazılmamışsa baştaki ilçe adı ayrılmaz: "Fatih Sultan Mehmet" gibi adlar bozulmasın diye
    assert ayristir("Fatih Sultan Mehmet Mah. 5. Sk. No:3")["mahalle"] == "Fatih Sultan Mehmet"


def test_bicimle():
    s = ayristir("CAFERAGA MH MODA CD NO 12 DAIRE 3 KADIKOY ISTANBUL")
    assert bicimle(s) == "Caferağa Mah. Moda Cad. No:12 D:3, Kadıköy/İstanbul"
    assert bicimle(ayristir("ISTIKLAL CAD NO 5 BEYOGLU ISTANBUL")) == "İstiklal Cad. No:5, Beyoğlu/İstanbul"


def test_ingilizce():
    s = parse("Caferağa Mah. Moda Cad. No:12 D:3 Kadıköy/İstanbul")
    assert s["province"] == "İstanbul" and s["district"] == "Kadıköy" and s["neighbourhood"] == "Caferağa"
    assert s["street"] == "Moda" and s["street_type"] == "avenue" and s["number"] == "12" and s["unit"] == "3"
    assert ayristir("x", dil="en").keys() == s.keys()
    assert bicimle(s) == "Caferağa Mah. Moda Cad. No:12 D:3, Kadıköy/İstanbul"


def test_dil_hatasi():
    with pytest.raises(ValueError):
        ayristir("x", dil="de")


def test_cli_tek(capsys):
    assert main(["Moda Cad. No:5 Kadıköy İstanbul", "--dil", "en", "--bicim"]) == 0
    s = json.loads(capsys.readouterr().out)
    assert s["district"] == "Kadıköy" and s["formatted_address"] == "Moda Cad. No:5, Kadıköy/İstanbul"


def test_cli_csv(tmp_path):
    g = tmp_path / "a.csv"
    g.write_text("kod;adres\n1;Caferağa Mah. Moda Cad. No:12 Kadıköy/İstanbul\n2;SERDIVAN SAKARYA KEMALPASA MAH 2320 SK NO 5\n", encoding="utf-8")
    c = tmp_path / "b.csv"
    assert main([str(g), "--sutun", "adres", "-o", str(c), "--bicim"]) == 0
    r = list(csv.DictReader(io.StringIO(c.read_text(encoding="utf-8-sig")), delimiter=";"))
    assert [x["il"] for x in r] == ["İstanbul", "Sakarya"]
    assert r[1]["ilce"] == "Serdivan" and r[1]["yol"] == "2320" and r[0]["kod"] == "1"
    assert r[0]["standart_adres"] == "Caferağa Mah. Moda Cad. No:12, Kadıköy/İstanbul"


def test_cli_sutun_cakismasi(tmp_path):
    # kullanıcının "no" sütunu kapı numarasıyla ezilmemeli
    g = tmp_path / "a.csv"
    g.write_text("no,adres\n7,KONAK MAH. 1453 SOKAK NO:22 NILUFER/BURSA\n", encoding="utf-8")
    c = tmp_path / "b.csv"
    assert main([str(g), "--sutun", "adres", "-o", str(c)]) == 0
    r = next(csv.DictReader(io.StringIO(c.read_text(encoding="utf-8-sig"))))
    assert r["no"] == "7" and r["adres_no"] == "22" and r["adres_il"] == "Bursa"


def test_cli_yanlis_sutun(tmp_path, capsys):
    g = tmp_path / "a.csv"
    g.write_text("adres\nModa Cad. No:5\n", encoding="utf-8")
    assert main([str(g), "--sutun", "yok"]) == 2


# ------------------------------------------------------------------ 0.2.0 özellikleri

from turkce_adres import ayni_mi, benzerlik, eksikler, genellestir, konum  # noqa: E402


def test_etiketli_yazim():
    s = ayristir("Mahalle: Caferağa, Cadde: Moda, No: 5, İlçe: Kadıköy, İl: İstanbul")
    assert (s["mahalle"], s["yol"], s["yol_turu"], s["no"], s["ilce"], s["il"]) == ("Caferağa", "Moda", "cadde", "5", "Kadıköy", "İstanbul")


def test_yazim_hatasi():
    s = ayristir("Levent Mah. Büyükdere Cad. No:185 Besiktas/Istnbul")
    assert s["il"] == "İstanbul" and s["ilce"] == "Beşiktaş" and s["kalan"] is None
    assert any("Istnbul" in n for n in s["notlar"])


def test_site_blok_kat():
    s = ayristir("Yıldız Sit. B Blk. Kat 2 D:5, Çankaya / ANKARA")
    assert (s["blok"], s["kat"], s["ic_kapi"], s["ilce"]) == ("B", "2", "5", "Çankaya")
    assert ayristir("Gazi Cad. No:15-A Kat: Zemin Bayraklı İzmir")["kat"] == "Zemin"
    assert ayristir("Gazi Cad. No:15-A Bayraklı İzmir")["no"] == "15/A"


def test_koy_cikmaz_meydan():
    s = ayristir("Yeşilyurt Köyü Merkez Sokak No:7 Kızılcahamam Ankara")
    assert (s["koy"], s["yol"], s["yol_turu"]) == ("Yeşilyurt", "Merkez", "sokak")
    s = ayristir("Şemsi Paşa Çıkmazı No:4 Üsküdar İstanbul")
    assert (s["yol"], s["yol_turu"]) == ("Şemsi Paşa", "cikmaz")
    s = ayristir("kızılay meydanı ziya gökalp cd 12 çankaya ankara")
    assert (s["ust_yol"], s["yol"], s["no"]) == ("Kızılay Meydanı", "Ziya Gökalp", "12")
    # "Sevdalı Çıkmazı Sokak": çıkmaz adın parçası
    s = ayristir("Merkez Mah. Sevdalı Çıkmazı Sokak No: 14 Beykoz/İstanbul")
    assert (s["yol"], s["yol_turu"]) == ("Sevdalı Çıkmazı", "sokak")


def test_tarif():
    s = ayristir("Caferağa Mah. Moda Cad. No:12 Migros karşısı Kadıköy")
    assert s["tarif"] == "Migros karşısı" and s["ilce"] == "Kadıköy"


def test_egik_cizgi_ic_kapi():
    s = ayristir("Atatürk Mah. Cumhuriyet Cad. No:15/3 Serdivan/Sakarya")
    assert s["no"] == "15/3" and s["ic_kapi"] == "3"
    assert bicimle(s) == "Atatürk Mah. Cumhuriyet Cad. No:15 D:3, Serdivan/Sakarya"


def test_resmi_bicim():
    s = ayristir("Caferağa Mah. Moda Cad. No:12 D:3 Kadıköy/İstanbul 34710")
    assert bicimle(s, "resmi") == "Caferağa Mahallesi Moda Caddesi Dış Kapı No: 12 İç Kapı No: 3, Kadıköy/İSTANBUL 34710"


def test_guven_notlar_ingilizce():
    s = parse("Moda Cad. No:1 Kadıköy")
    assert 0 <= s["confidence"] <= 1 and any("inferred" in n for n in s["notes"])


def test_benzerlik():
    a = "CAFERAGA MH MODA CD NO 12 KADIKOY ISTANBUL"
    assert benzerlik(a, "Caferağa Mahallesi, Moda Caddesi No:12, Kadıköy/İstanbul") == 1.0
    assert ayni_mi(a, "Caferağa Mah. Moda Cd. 12 Kadıköy")
    assert benzerlik(a, "Caferağa Mah. Moda Cad. No:14 Kadıköy/İstanbul") <= 0.6     # başka bina
    assert benzerlik(a, "Caferağa Mah. Moda Cad. No:12 Çankaya/Ankara") == 0.0       # başka il
    assert not ayni_mi("Moda Cad. No:12 D:3 Kadıköy", "Moda Cad. No:12 D:4 Kadıköy")  # başka daire


def test_genellestir():
    g = genellestir("Caferağa Mah. Moda Cad. No:12 D:3 Kadıköy/İstanbul 34710")
    assert g["metin"] == "Caferağa Mah., Kadıköy/İstanbul" and g["no"] is None and g["posta_kodu"] is None
    assert genellestir("Caferağa Mah. Moda Cad. No:12 Kadıköy", "ilce")["metin"] == "Kadıköy/İstanbul"
    assert genellestir("Caferağa Mah. Moda Cad. No:12 Kadıköy", "yol")["metin"] == "Caferağa Mah. Moda Cad., Kadıköy/İstanbul"


def test_eksikler():
    assert eksikler("Caferağa Mah. Moda Cad. No:12 D:3 Kadıköy/İstanbul 34710") == []
    e = eksikler("Moda Cad. Levent Plaza Kat:3 Kadıköy", dil="en")
    assert "house number missing" in e and any("unit number" in x for x in e)


def test_konum():
    k = konum("Seyhan Adana")
    assert k and k["duzey"] in ("ilce", "il") and 36 < k["enlem"] < 38
    assert konum("bilinmeyen bir yer") is None


def test_cli_ozellikler(tmp_path):
    g = tmp_path / "a.csv"
    g.write_text("adres\nCaferağa Mah. Moda Cad. No:12 Kadıköy/İstanbul\nCAFERAGA MH MODA CD NO 12 KADIKOY ISTANBUL\n"
                 "Seyhan Adana\n", encoding="utf-8")
    c = tmp_path / "b.csv"
    assert main([str(g), "--konum", "--eksik", "--tekil", "-o", str(c)]) == 0
    r = list(csv.DictReader(io.StringIO(c.read_text(encoding="utf-8-sig"))))
    assert r[0]["tekil_grup"] == r[1]["tekil_grup"] == "1" and r[2]["tekil_grup"] == ""
    assert r[2]["enlem"] and "dış kapı" in r[2]["eksikler"]
    c2 = tmp_path / "c.csv"
    assert main([str(g), "--genellestir", "mahalle", "-o", str(c2)]) == 0
    r = list(csv.DictReader(io.StringIO(c2.read_text(encoding="utf-8-sig"))))
    assert "no" not in r[0] and r[0]["metin"] == "Caferağa Mah., Kadıköy/İstanbul"
