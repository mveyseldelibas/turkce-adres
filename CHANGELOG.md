# Changelog

## 0.2.0 (2026-11-09), first release as turkce-adres

- Renamed: package `turkce-adres`, module `turkce_adres`, command `turkce-adres` (the name `tr-adres` on PyPI belongs to an independent project).
- Neighbourhood/village gazetteer from OpenStreetMap: 66,687 entries in 81 provinces and 973 districts, with centre points. Validates the neighbourhood, infers a missing district or province, restores correct spelling.
- Offline approximate geocoding (`konum` / `geocode`): street (14,777 OSM streets), neighbourhood/village, district or province level.
- Address matching (`benzerlik`, `ayni_mi`) and duplicate grouping in the CLI (`--tekil`).
- Privacy generalisation (`genellestir`) to province, district, neighbourhood or street level.
- Delivery check (`eksikler`): missing or inconsistent elements.
- Parser: labelled fields ("Mahalle: X, Cadde: Y"), typo tolerance for province/district names, ASCII spelling restored with a word list from OSM, site/block, village ("Köyü"), dead end, square, "Kat: Zemin", landmark phrases ("X karşısı"), "12/3" read as house 12 unit 3, postcode to district (OSM-derived), aliases (K.Maraş, Antep, İst.).
- `guven` (confidence) and `notlar` (notes) in every result; official output style (`bicimle(a, "resmi")`).
- New hand-labelled hard set `bench/zor.tsv` (58 addresses). Held-out OSM set: 99.5% of addresses with every field correct.

## 0.1.0 (2026-11-09)

- First release: rule-based parser (`ayristir` / `parse`), formatter (`bicimle` / `format_address`), command line tool with CSV support.
- Turkish and English field names and CLI messages (`dil="en"`, `--lang en`).
- 5-digit street names (`14027 Sk.`) are no longer mistaken for postcodes; postcode must start with a valid province code (01-81). Province is inferred from the postcode.
- Ordinal and slashed street numbers kept as written (`716. Sk.`, `678/2. Sk.`, `451/A Sk.`).
- "Province District Neighbourhood" prefixes split off (`Samsun 19 Mayıs Fındıklı Mah.`), while real names starting with a place name are kept (`Fatih Sultan Mehmet Mah.`, `Gürpınar Yolu Cad.`).
- Building names no longer swallow the street before them; house number without "No" after the street (`Ziya Gökalp Cd 12`).
- Held-out evaluation set (6,000 OpenStreetMap addresses): 99.5% of addresses with every field correct. The earlier browser prototype scored 74.5% on the development set.
