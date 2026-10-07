# Dataopdatering 7. okt. 2026 – fra Adtraction-feedet (udbydernes egne data)

Sandhedsgrundlag nu: `_build/data/plans.json` (oversigt i `_build/PLANS_OVERVIEW.txt`) og `_build/data/providers.json`. Priserne kommer fra udbydernes officielle Adtraction-feed og opdateres automatisk hver nat.

## Vigtigste ændringer
- **Lyca Mobile kører på TT-netværket (Norlys/Telenor)** ifølge Lycas egne data – IKKE TDC NET. Alle Lyca-abonnementer er **4G**. Fjern Mobilsiden/Telecompaper-diskussionen; skriv blot at Lyca kører på Norlys/Telenor (TT-netværket).
- **Lebara**: 40 GB/49 kr. og 200 GB/159 kr. findes ikke længere. Nu: 5 GB/5 t 19 kr., **Fri tale + 70 GB 59 kr. (billigste med fri tale i hele sammenligningen)**, 100 GB 99 kr. (49 kr./md. i 2 mdr.), 160 GB 119 kr. Alle 4G. EU-data 20 GB på 70/100/160 GB. Inkluderede timer til opkald til 60+ lande (5-10 timer). Lebara 40 GB må ikke nævnes som aktuelt tilbud.
- **Lyca**: 5 GB/5 t 19 kr., 30 GB/15 t 49 kr. (18 kr./md. i 3 mdr.), fri tale + 100 GB 99 kr. (69 kr. i 3 mdr.), fri tale + 200 GB 119 kr. (59 kr. i 6 mdr.), 500 GB 299 kr. 60 GB-pakken er udgået. Alle 4G.
- **Telmore**: 3 GB/3 t 79 kr.; **fri tale + 50 GB 149 kr. (69 kr./md. i 3 mdr.)** erstatter 45 GB-tilbuddet (26 kr. til 18.10 findes ikke længere); fri tale + 200 GB 159 kr. ("dobbelt data", erstatter 80 GB); fri data 249 kr.; Telmore Play med fri data + 3/4/5/9 streamingtjenester: 399/449/499/599 kr. (99 kr. første måned). 60 GB + Musik er udgået.
- **Oister**: 12 GB fri tale 69 kr.; 40 GB 89 kr. (59 kr. i 6 mdr.); 100 GB 109 kr. (79 kr. i 6 mdr.); **fri data 189 kr. (129 kr. i 6 mdr.), 50 GB EU**. Streamingabonnementet (169 kr.) er ikke i feedet – nævn det ikke som aktuelt tilbud.
- **Flexii**: Både 4G- og 5G-priser (første år/derefter): 20 GB 4G 52→59, 5G 59→69; 50 GB 4G 69→79, 5G 79→89; 150 GB 4G 84→99, 5G 94→109; fri data 4G 124→144, 5G 129→149. Byg-selv 10 GB (4G) 19 kr. i 3 mdr., derefter 39 kr. 5 GB-børneabonnement (17/35 kr.) findes ikke i data længere.
- **Greentel**: Basic 5 GB/1 time 29 kr. (ny, billig), 2 GB/2 t 48 kr., fri tale + 10 GB 69 kr. (4G), 30 GB 89 kr. (5G, 18 GB EU), 50 GB 99 kr. (5G, 15 GB EU). **100 GB og 1000 GB er ikke længere i data.** 5G kun på 30 og 50 GB.
- **Duka**: 6 GB/6 t 59 kr. (4G), fri tale + 30 GB 99 kr. (ingen kampagne længere), 50 GB 99 kr., 55 GB 119 kr. (55 GB EU), 120 GB 119 kr., 75 GB 149 kr. (75 GB EU), **200 GB 129 kr. – 79 kr./md. til 31.3.2027**, 1000 GB 179 kr., fri data 199 kr. "World"-abonnementet er ikke i feedet – nævn det ikke som aktuelt.
- **YouSee**: 3 GB/3 t 99 kr. (4G), 25 GB 179, 50 GB 219 (35 GB EU), 100 GB 249 (40 GB EU), fri data 299 (50 GB EU). YouSee har nu også affiliatelink.
- Alle 8 udbydere: ingen binding.

## Nye nøgletal
- Billigst overhovedet: 19 kr. (Lebara/Lyca 5 GB). Greentel Basic 29 kr.
- Billigste fri tale: **Lebara 70 GB 59 kr.** (Flexii 20 GB 4G 59 kr. normalpris, 52 kr. første år).
- Billigste fri data: Flexii 4G 144 kr. (124 første år), Flexii 5G 149 (129 første år), Oister 189 (129 i 6 mdr.), Duka 199, Telmore 249, YouSee 299.
- Mest data for pengene: Duka 1000 GB 179 kr.; Duka 200 GB 79 kr. til 31.3.2027; Lyca 200 GB 59 kr. i 6 mdr.
- Antal abonnementer: 49 (brug pladsholderen `{antal}`).

## Pladsholdere – BRUG DEM i stedet for hårdkodede priser
Builderen indsætter automatisk aktuelle værdier ved hver build:
- `{pris:ID}` normalpris (tal), `{intro:ID}` intropris (tal), `{introtekst:ID}` fx "69 kr./md. i 3 mdr.", `{gb:ID}` "70 GB"/"Fri data", `{eu:ID}`, `{navn:ID}` "Lebara Fri tale + 70 GB"
- `{fra:TAG}` laveste pris i kategori, `{antal}` antal abonnementer, `{maaned}`, `{tjekket}`
- ID'er findes i PLANS_OVERVIEW.txt (fx lb-70, tm-50, fx-fri, dk-200, oi-fri).
Eksempel: "Lebara giver fri tale og {gb:lb-70} for {pris:lb-70} kr./md." Brug pladsholdere i front matter (title/desc/answer) og brødtekst for alle konkrete abonnementspriser. Regneeksempler (årspriser) må gerne stå som tal, men skal passe med de nuværende priser.
