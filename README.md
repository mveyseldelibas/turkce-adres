# tr-adres

[English](README.en.md)

Dağınık yazılmış Türkçe adresleri alanlarına ayırır: il, ilçe, mahalle, sokak/cadde/bulvar, kapı no, kat, daire, bina, posta kodu. Standart yazıma da çevirir.

- **Çevrimdışı.** Ağ bağlantısı, model ya da ek paket yok; adresler bilgisayarınızdan çıkmaz.
- **Türkçe yazım çeşitlerini tanır.** `Mah. / Mh. / Mahallesi`, `Sk. / Sok. / Sokak`, `Cad. / Cd.`, `Bulv. / Blv.`, `No: / No. / no`, `Kat:`, `D: / Daire`, BÜYÜK ASCII yazım (`KADIKOY ISTANBUL`), il başta ya da sonda.
- **İl ve ilçe her zaman doğru yazımla döner** (`KADIKOY` -> `Kadıköy`; 81 il, 973 ilçe). İlçeden il, posta kodundan il bulunur.
- **İki dil:** alan adları Türkçe ya da İngilizce (`dil="en"`).

```bash
pip install tr-adres
```

## Kullanım

```python
from tr_adres import ayristir, bicimle

a = ayristir("CAFERAGA MH MODA CD NO 12 DAIRE 3 KADIKOY ISTANBUL")
# {'il': 'İstanbul', 'ilce': 'Kadıköy', 'mahalle': 'CAFERAGA', 'yol': 'MODA', 'yol_turu': 'cadde',
#  'ust_yol': None, 'no': '12', 'ic_kapi': '3', 'kat': None, 'bina': None, 'posta_kodu': None, 'kalan': None}

bicimle(a)
# 'Caferaga Mah. Moda Cad. No:12 D:3, Kadıköy/İstanbul'
```

İngilizce alan adları:

```python
from tr_adres import parse            # ya da ayristir(metin, dil="en")
parse("Güzelyalı Mah., Turgut Özal Bulvarı No: 102, 01170 Çukurova/Adana")
# {'province': 'Adana', 'district': 'Çukurova', 'neighbourhood': 'Güzelyalı', 'street': 'Turgut Özal',
#  'street_type': 'boulevard', 'number': '102', 'postcode': '01170', ...}
```

### Komut satırı

```bash
# tek adres
tr-adres "Serdivan Sakarya Kemalpaşa mah 2320 sk no:5/A kat 2"

# CSV: adres sütununa alan sütunları ekler; ayraç (, ; sekme) kendiliğinden bulunur
tr-adres musteriler.csv --sutun adres --bicim -o musteriler_ayrik.csv

# İngilizce sütun adları ve mesajlar
tr-adres customers.csv --column address --lang en -o out.csv
```

Excel'den "CSV UTF-8" olarak kaydedilen dosyalar doğrudan okunur; çıktı da Excel'in Türkçe karakterleri doğru açacağı biçimde (UTF-8 BOM) yazılır. Dosyanızda `il`, `no` gibi aynı adlı bir sütun varsa hiçbir sütun ezilmez: yeni sütunlar `tr_adres_` ön ekiyle yazılır.

## Alanlar

| Türkçe | English | Örnek |
|---|---|---|
| `il` | `province` | İstanbul |
| `ilce` | `district` | Kadıköy |
| `mahalle` | `neighbourhood` | Caferağa |
| `yol` | `street` | Moda |
| `yol_turu` | `street_type` | sokak / cadde / bulvar (street / avenue / boulevard) |
| `ust_yol` | `parent_street` | "Atatürk Bulvarı 45. Sokak" içindeki Atatürk |
| `no` | `number` | 12, 5/A |
| `ic_kapi` | `unit` | daire no |
| `kat` | `floor` | 2 |
| `bina` | `building` | Levent Plaza, Ali Kırca Apt. |
| `posta_kodu` | `postcode` | 34710 |
| `kalan` | `unparsed` | ayrılamayan sözcükler |

## Ölçüm

Sınama verisi OpenStreetMap'teki Türkiye adreslerinden üretildi (il, ilçe, mahalle, yol ve kapı no'su dolu ve il-ilçe sözlüğüyle tutarlı 66.842 tekil adres). Her adres altı biçimden birinde metne çevrildi: düzgün yazım, BÜYÜK ASCII, il başta, virgüllü, posta kodlu, kat-daireli; kısaltmalar rastgele seçildi.

Kurallar `bench/gelistirme.jsonl` (6.000 adres) üzerinde düzeltildi. Asıl sonuç, geliştirme sırasında hiç bakılmayan **ayrı** 6.000 adreslik `bench/sinama.jsonl` setindedir (iki sette ortak adres yok):

| Alan | Doğru |
|---|---|
| Tüm alanlar birlikte doğru | **%99,5** (5.968 / 6.000) |
| il | %100 (6.000 / 6.000) |
| ilçe | %100 (5.999 / 6.000) |
| mahalle | %99,6 |
| yol | %99,7 |
| kapı no | %100 |
| posta kodu | %100 (735 / 735) |
| kat, daire | %100 (1.265 / 1.265) |

Karşılaştırma büyük/küçük harf ve Türkçe karakter farkını yok sayar (`CAFERAGA` = `Caferağa`). Kalan hataların çoğu OpenStreetMap etiketlerindeki karışıklıktan geliyor (ör. mahalle alanına sokak adı yazılmış). Yeniden ölçmek için: `python bench/degerlendir.py sinama`.

**Sınırlar, dürüstçe:**

- Sınama metinleri şablonla üretildi; gerçek insan yazımı (yazım hatası, eksik sözcük, alışılmadık sıra) daha zordur ve sonuç daha düşük olur. Gerçek adres örneği gönderirseniz (kişisel veri içermeyen) teste ekleriz.
- Mahalle ve sokak adları sözlükle doğrulanmaz, yazıldığı gibi alınır. BÜYÜK ASCII yazımda Türkçe harfler geri kazanılmaz (`CAFERAGA`).
- İl yazılmamışsa adresin başındaki ilçe adı ayrılmaz; yoksa "Fatih Sultan Mehmet Mah." gibi adlar bozulur.
- "Meydan", "Çarşı", "Yolu" gibi yol türleri ayrı tanınmaz.
- Koordinat bulma (geocoding) ve resmî adres kaydıyla (UAVT) doğrulama yapmaz.

## Verinin yeniden üretilmesi

```bash
pip install requests
python scripts/osm_cek.py                                  # Overpass API'den il il ham veri (~125 MB, ham/)
python scripts/hazirla.py --ad gelistirme --atla 0
python scripts/hazirla.py --ad sinama --atla 6000
```

## Lisans

- Kod: [MIT](LICENSE).
- İl-ilçe sözlüğü (`src/tr_adres/veri/gazetteer.json`) ve sınama setleri (`bench/*.jsonl`): OpenStreetMap verisinden türetilmiştir, **© OpenStreetMap katkıcıları**, [ODbL 1.0](LICENSE-DATA.md).
