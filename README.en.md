# tr-adres

[Türkçe](README.md)

A parser for Turkish addresses. It splits free-text addresses into province, district, neighbourhood, street, house number, floor, unit, building and postcode, and formats them into a standard spelling.

- **Offline.** No network, no model, no dependencies; addresses never leave your machine.
- **Knows Turkish spelling variants:** `Mah. / Mh. / Mahallesi`, `Sk. / Sok. / Sokak`, `Cad. / Cd.`, `Bulv. / Blv.`, `No: / No. / no`, `Kat:`, `D: / Daire`, all-caps ASCII (`KADIKOY ISTANBUL`), province first or last.
- **Province and district always come back correctly spelled** (`KADIKOY` -> `Kadıköy`; 81 provinces, 973 districts). The province is inferred from the district or the postcode.
- **Field names in English or Turkish.**

```bash
pip install tr-adres
```

## Usage

```python
from tr_adres import parse, format_address

a = parse("CAFERAGA MH MODA CD NO 12 DAIRE 3 KADIKOY ISTANBUL")
# {'province': 'İstanbul', 'district': 'Kadıköy', 'neighbourhood': 'CAFERAGA', 'street': 'MODA',
#  'street_type': 'avenue', 'parent_street': None, 'number': '12', 'unit': '3', 'floor': None,
#  'building': None, 'postcode': None, 'unparsed': None}

format_address(a)
# 'Caferaga Mah. Moda Cad. No:12 D:3, Kadıköy/İstanbul'
```

Turkish field names: `from tr_adres import ayristir`.

### Command line

```bash
tr-adres "Serdivan Sakarya Kemalpaşa mah 2320 sk no:5/A kat 2" --lang en

# CSV: adds the field columns next to your address column; the delimiter is detected
tr-adres customers.csv --column address --format --lang en -o customers_parsed.csv
```

If your file already has a column with the same name as a new field (`number`, `province`...), nothing is overwritten: all new columns get the `tr_adres_` prefix.

## Fields

| English | Turkish | Example |
|---|---|---|
| `province` | `il` | İstanbul |
| `district` | `ilce` | Kadıköy |
| `neighbourhood` | `mahalle` | Caferağa |
| `street` | `yol` | Moda |
| `street_type` | `yol_turu` | street / avenue / boulevard (sokak / cadde / bulvar) |
| `parent_street` | `ust_yol` | Atatürk in "Atatürk Bulvarı 45. Sokak" |
| `number` | `no` | 12, 5/A |
| `unit` | `ic_kapi` | flat number |
| `floor` | `kat` | 2 |
| `building` | `bina` | Levent Plaza |
| `postcode` | `posta_kodu` | 34710 |
| `unparsed` | `kalan` | leftover words |

## Evaluation

Test data comes from Turkish addresses in OpenStreetMap: 66,842 unique addresses with all components filled in and consistent with the province/district list. Each address was rendered as text in one of six styles (canonical, all-caps ASCII, province first, comma-separated, with postcode, with floor and unit), with randomly chosen abbreviations.

The rules were tuned on `bench/gelistirme.jsonl` (6,000 addresses). The headline number is from a **separate** set of 6,000 addresses, `bench/sinama.jsonl`, never looked at during development (no overlap):

| Field | Correct |
|---|---|
| All fields correct | **99.5%** (5,968 / 6,000) |
| province | 100% |
| district | 100% (5,999 / 6,000) |
| neighbourhood | 99.6% |
| street | 99.7% |
| house number | 100% |
| postcode | 100% (735 / 735) |
| floor, unit | 100% (1,265 / 1,265) |

Comparison ignores case and Turkish diacritics. Most remaining errors come from messy OpenStreetMap tags. Re-run with `python bench/degerlendir.py sinama`.

**Limits:**

- The test texts are template-generated; real human writing (typos, missing words, unusual order) is harder and will score lower.
- Neighbourhood and street names are not checked against a list. All-caps ASCII input does not get its Turkish letters back.
- A district name at the very start is not split off unless a province is also given, so names like "Fatih Sultan Mehmet Mah." stay intact.
- No geocoding and no validation against the official national address registry.

## License

- Code: [MIT](LICENSE).
- Province/district list (`src/tr_adres/veri/gazetteer.json`) and test sets (`bench/*.jsonl`) are derived from OpenStreetMap data, **© OpenStreetMap contributors**, [ODbL 1.0](LICENSE-DATA.md).
