# Changelog

## 0.1.0 (unreleased)

- First release: rule-based parser (`ayristir` / `parse`), formatter (`bicimle` / `format_address`), command line tool with CSV support.
- Turkish and English field names and CLI messages (`dil="en"`, `--lang en`).
- 5-digit street names (`14027 Sk.`) are no longer mistaken for postcodes; postcode must start with a valid province code (01-81). Province is inferred from the postcode.
- Ordinal and slashed street numbers kept as written (`716. Sk.`, `678/2. Sk.`, `451/A Sk.`).
- "Province District Neighbourhood" prefixes split off (`Samsun 19 Mayıs Fındıklı Mah.`), while real names starting with a place name are kept (`Fatih Sultan Mehmet Mah.`, `Gürpınar Yolu Cad.`).
- Building names no longer swallow the street before them; house number without "No" after the street (`Ziya Gökalp Cd 12`).
- Held-out evaluation set (6,000 OpenStreetMap addresses): 99.5% of addresses with every field correct. The earlier browser prototype scored 74.5% on the development set.
