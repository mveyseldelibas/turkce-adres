# turkce-adres

[English](README.en.md)

Türkçe adresler için internetsiz, ek paket gerektirmeyen bir Python kütüphanesi ve komut satırı aracı:

- **Ayrıştırır:** dağınık yazılmış adresi il, ilçe, mahalle/köy, cadde/sokak/bulvar/çıkmaz/meydan, kapı no, blok, kat, daire, bina, posta kodu ve "Migros karşısı" gibi tarif ifadelerine ayırır.
- **Düzeltir:** BÜYÜK ASCII yazımı Türkçe harflerine kavuşturur (`CAFERAGA` → `Caferağa`, `BUYUKDERE` → `Büyükdere`), il ve ilçe adlarındaki yazım hatalarını düzeltir (`Istnbul` → `İstanbul`), standart (kargo) ya da resmî yazıma çevirir.
- **Doğrular:** 66.687 mahalle, köy ve semtlik sözlükle mahallenin o ilçede olup olmadığına bakar; il ya da ilçe yazılmamışsa mahalleden ya da posta kodundan bulur.
- **Konum verir (internetsiz):** adresin yaklaşık koordinatını sokak, mahalle, ilçe ya da il düzeyinde döndürür. Hiçbir servise istek atmaz.
- **Eşleştirir:** iki adresin aynı yeri gösterip göstermediğini söyler; CSV'de tekrarlanan kayıtları gruplar.
- **KVKK için genelleştirir:** paylaşmadan önce kapı no, daire, posta kodu gibi ayrıntıları atıp adresi mahalle, ilçe ya da il düzeyine indirir.
- **Teslimat denetimi:** kargo için eksik ya da çelişkili öğeleri listeler (kapı no yok, ilçe bu ile ait değil...).
- **İki dil:** alan adları, notlar ve komut satırı Türkçe ya da İngilizce.

```bash
pip install turkce-adres
```

## Kullanım

```python
from turkce_adres import ayristir, bicimle, konum, benzerlik, genellestir, eksikler

a = ayristir("ISTANBUL BESIKTAS LEVENT MAH. BUYUKDERE CAD NO 185 D 4")
a["il"], a["ilce"], a["mahalle"], a["yol"], a["no"], a["ic_kapi"]
# ('İstanbul', 'Beşiktaş', 'Levent', 'Büyükdere', '185', '4')

bicimle(a)                 # 'Levent Mah. Büyükdere Cad. No:185 D:4, Beşiktaş/İstanbul'
bicimle(a, "resmi")        # 'Levent Mahallesi Büyükdere Caddesi Dış Kapı No: 185 İç Kapı No: 4, Beşiktaş/İSTANBUL'

konum(a)                   # {'enlem': ..., 'boylam': ..., 'duzey': 'sokak', 'kaynak': 'OpenStreetMap (ODbL)'}

benzerlik("CAFERAGA MH MODA CD NO 12 KADIKOY ISTANBUL",
          "Caferağa Mahallesi, Moda Caddesi No:12, Kadıköy/İstanbul")      # 1.0
benzerlik("Moda Cad. No:12 Kadıköy", "Moda Cad. No:14 Kadıköy")             # 0.6 (başka bina)

genellestir("Caferağa Mah. Moda Cad. No:12 D:3 Kadıköy/İstanbul 34710")["metin"]
# 'Caferağa Mah., Kadıköy/İstanbul'

eksikler("Moda Cad. Kadıköy")
# ['mahalle ya da köy yok', 'dış kapı numarası yok', 'posta kodu yok (önerilir)']
```

Her sonuçta ayrıca `guven` (0-1) ve `notlar` vardır: ne düzeltildi, il nereden bulundu ("il ilçeden bulundu", "yazım düzeltildi: Istnbul -> İstanbul").
`duzelt=False` verilirse sözcükler yazıldığı gibi kalır. İngilizce alan adları için `parse(metin)` ya da `ayristir(metin, dil="en")`.

### Komut satırı

```bash
# tek adres
turkce-adres "kızılay meydanı ziya gökalp cd 12 çankaya ankara" --bicim --konum

# CSV: adres sütununun yanına alanları, standart yazımı, konumu, eksikleri ve tekrar gruplarını ekler
turkce-adres musteriler.csv --sutun adres --bicim --konum --eksik --tekil -o musteriler_ayrik.csv

# KVKK: yalnız mahalle düzeyine kadar yaz
turkce-adres musteriler.csv --sutun adres --genellestir mahalle -o paylasim.csv

# İngilizce sütun adları ve mesajlar
turkce-adres customers.csv --column address --lang en --geocode -o out.csv
```

Excel'den "CSV UTF-8" olarak kaydedilen dosyalar doğrudan okunur; çıktı Excel'in Türkçe karakterleri doğru açacağı biçimde yazılır. Dosyanızda `il`, `no` gibi aynı adlı bir sütun varsa hiçbir sütun ezilmez, yeni sütunlar `adres_` ön ekiyle yazılır.

## Alanlar

| Türkçe | English | Örnek |
|---|---|---|
| `il` / `ilce` | `province` / `district` | İstanbul / Kadıköy |
| `mahalle` / `koy` | `neighbourhood` / `village` | Caferağa / Yeşilyurt |
| `yol`, `yol_turu` | `street`, `street_type` | Moda, cadde (sokak, cadde, bulvar, cikmaz, meydan, yol) |
| `ust_yol` | `parent_street` | "Kızılay Meydanı Ziya Gökalp Cd." içindeki Kızılay Meydanı |
| `no`, `ic_kapi` | `number`, `unit` | 12/3 → no 12/3, iç kapı 3 |
| `kat`, `blok`, `bina` | `floor`, `block`, `building` | Zemin, B, Levent Plaza |
| `posta_kodu` | `postcode` | 34710 |
| `tarif` | `landmark` | Migros karşısı |
| `kalan` | `unparsed` | ayrılamayan sözcükler |
| `guven`, `notlar` | `confidence`, `notes` | 0,95, ["il ilçeden bulundu"] |

## Ölçüm

Üç sette ölçüldü. Karşılaştırma büyük/küçük harf ve Türkçe karakter farkını yok sayar. "Tüm alanlar doğru", adresin etiketlenmiş bütün alanlarının birlikte doğru olduğu adres oranıdır.

| Set | Nasıl üretildi | Tüm alanlar doğru |
|---|---|---|
| `bench/sinama.jsonl` (6.000) | OpenStreetMap'teki Türkiye adreslerinden şablonla; geliştirme sırasında hiç bakılmadı | **%99,5 (5.969 / 6.000)** |
| `bench/gelistirme.jsonl` (6.000) | Aynı yöntem; kurallar bu sette düzeltildi | %99,5 (5.973 / 6.000) |
| `bench/zor.tsv` (58) | Elle yazılmış ve elle etiketlenmiş dağınık adresler (etiketli yazım, yazım hatası, il yazılmadan ilçe, site/blok, köy, çıkmaz, tarif) | %100 (58 / 58), aşağıdaki nota bakın |

Yeniden ölçmek için: `python bench/degerlendir.py sinama` ve `python bench/zor_degerlendir.py`.

**Sınırlar, dürüstçe:**

- İlk iki set şablonla üretildi. Üçüncü seti bu projeyi geliştiren kişi yazdı ve bazı kurallar o sete bakılarak düzeltildi; bağımsız bir ölçüm değildir. Gerçek kullanıcı yazımında sonuç daha düşük olur. Yanlış ayrılan adres örnekleri (kişisel veri içermeden) çok değerli.
- Mahalle sözlüğü, konum ve yazım düzeltmesi OpenStreetMap'te ne varsa ona dayanır. OSM'de olmayan mahalle doğrulanamaz; sokak düzeyinde konum yalnız OSM'de adresi girilmiş sokaklarda vardır (14.777 sokak). Konum **yaklaşıktır**: mahalle/köy için OSM'deki merkez noktası, ilçe ve il için mahalle merkezlerinin ortancası.
- Mahalle adları zamanla değişir, birleşir. Sözlük Kasım 2026 tarihli OSM verisidir; `scripts/` altındaki betiklerle yenilenebilir.
- Posta kodundan ilçe tablosu yalnız OSM'deki adres etiketlerinden türetildi (792 posta kodu); PTT listesi kullanılmadı.
- `genellestir` bir **genelleştirmedir**, tek başına anonimleştirme sayılmaz: az nüfuslu bir mahalle ya da başka verilerle birleşince kişi yine belirlenebilir.
- Resmî adres kaydıyla (UAVT) doğrulama yapmaz; o veri herkese açık değildir.

## Verinin yeniden üretilmesi

```bash
pip install requests
python scripts/osm_cek.py                         # il il adresler ve yer adları (Overpass API, ~125 MB, ham/)
python scripts/osm_mahalle_cek.py                 # her ilçenin mahalle ve köyleri, merkez koordinatlarıyla
python scripts/hazirla.py --ad gelistirme --atla 0
python scripts/hazirla.py --ad sinama --atla 6000
python scripts/sozluk_kur.py --ham ham            # mahalle, sokak, posta kodu ve yazım sözlükleri
```

## Ad hakkında

Bu proje GitHub'da önce `tr-adres` adıyla açıldı. PyPI'daki `tr-adres` paketi başka bir geliştiricinin bağımsız projesidir; karışmaması için bu paket `turkce-adres` adıyla yayımlanır (modül `turkce_adres`, komut `turkce-adres`).

## Lisans

- Kod: [MIT](LICENSE).
- `src/turkce_adres/veri/` altındaki sözlükler ve `bench/*.jsonl` sınama setleri OpenStreetMap verisinden türetilmiştir, **© OpenStreetMap katkıcıları**, [ODbL 1.0](LICENSE-DATA.md).
