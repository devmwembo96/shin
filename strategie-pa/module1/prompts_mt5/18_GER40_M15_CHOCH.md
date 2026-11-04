# 18 — GER40 M15 — CHOCH (Module 1, itération 1)

| Élément | Valeur |
|---|---|
| EA | `PA_M1_Structure_EA` |
| Symbole | GER40 (nom broker : `GER40` — à adapter) |
| UT | M15 |
| Événements | InpTradeEvents = 1 (CHOCH seulement) |
| In-sample | 2021.01.01 → 2024.06.30 |
| Forward (OOS) | 2024.07.01 → 2025.12.31 (run séparé) |
| Modèle de ticks | « Every tick based on real ticks » (obligatoire) |
| Passes | 108 par run (algorithme complet) |
| Critère | Custom max (critère personnalisé maximum) |

## Plages optimisées
| Input | Start | Step | Stop | Nb valeurs |
|---|---|---|---|---|
| InpLeftBars | 2 | 1 | 10 | 9 |
| InpRightBars | 1 | 1 | 6 | 6 |
| InpBreakMode | 0 | 1 | 1 | 2 |

## Inputs fixes
- `InpTradeEvents` = 1 (CHOCH seulement)
- `InpRR` = 3.0
- `InpSLBufferATR` = 0.1
- `InpATRPeriod` = 14
- `InpMinRiskATR` = 0.2
- `InpMaxRiskATR` = 5.0
- `InpMaxBarsInTrade` = 0
- `InpOnePosition` = true
- `InpLots` = lot minimum du symbole (ex. 0.01 ; GER40 souvent 0.1 ou 1)
- `InpRandomMode` = false
- `InpRandomSeed` = 1
- `InpMinTradesForScore` = 100
- `InpUseSession` = true
- `InpSessionStart` = "09:00"
- `InpSessionEnd` = "18:30"

> **Session GER40** : 09:00–18:30 est exprimé en **heure serveur** (= 08:00–17:30 Francfort pour un serveur GMT+2/+3). Vérifiez l'écart chez votre broker (voir PROTOCOLE_BACKTEST.md §9) et corrigez si besoin.

---

## Étape A — prompt IN-SAMPLE (copier tout le bloc dans l'assistant IA de MT5)

```
Configure et lance une optimisation dans le Testeur de stratégie MT5 :
- Expert : PA_M1_Structure_EA
- Symbole : GER40
- Période (timeframe du graphique) : M15
- Dates : du 2021.01.01 au 2024.06.30 (période « Custom », IN-SAMPLE)
- Forward : No (désactivé)
- Modèle : « Every tick based on real ticks » (obligatoire)
- Dépôt initial : 10000 USD, levier 1:100
- Délai d'exécution : fixe 50 ms (pas « Random delay », pour des passes reproductibles)
- Optimisation : « Slow complete algorithm » (algorithme complet, 108 passes)
- Critère d'optimisation : Custom max (critère personnalisé maximum)
- Inputs à optimiser (cocher uniquement ceux-ci) :
- InpLeftBars : optimiser, Start=2, Step=1, Stop=10
- InpRightBars : optimiser, Start=1, Step=1, Stop=6
- InpBreakMode : optimiser, Start=0, Step=1, Stop=1
- Inputs fixes (décochés) :
- InpTradeEvents = 1 (CHOCH seulement) (NE PAS optimiser)
- InpRR = 3.0 (NE PAS optimiser)
- InpSLBufferATR = 0.1 (NE PAS optimiser)
- InpATRPeriod = 14 (NE PAS optimiser)
- InpMinRiskATR = 0.2 (NE PAS optimiser)
- InpMaxRiskATR = 5.0 (NE PAS optimiser)
- InpMaxBarsInTrade = 0 (NE PAS optimiser)
- InpOnePosition = true (NE PAS optimiser)
- InpLots = lot minimum du symbole (ex. 0.01 ; GER40 souvent 0.1 ou 1) (NE PAS optimiser)
- InpRandomMode = false (NE PAS optimiser)
- InpRandomSeed = 1 (NE PAS optimiser)
- InpMinTradesForScore = 100 (NE PAS optimiser)
- InpUseSession = true (NE PAS optimiser)
- InpSessionStart = "09:00" (NE PAS optimiser)
- InpSessionEnd = "18:30" (NE PAS optimiser)
Lance l'optimisation et préviens-moi quand elle est terminée. Ne modifie aucun autre réglage.
```

**Après l'étape A** : dans le dossier `Common\Files` (voir protocole §3), récupérez le fichier
`PA_M1_opt_GER40_M15_<AAAAMMJJ_HHMM>.csv` le plus récent. Ne le renommez pas
(sauf ajout éventuel de `_OHLC`). Copiez-le dans `resultats/module1/`.

---

## Étape B — prompt OUT-OF-SAMPLE (même grille, autres dates)

```
Configure et lance une optimisation dans le Testeur de stratégie MT5 :
- Expert : PA_M1_Structure_EA
- Symbole : GER40
- Période (timeframe du graphique) : M15
- Dates : du 2024.07.01 au 2025.12.31 (période « Custom », OUT-OF-SAMPLE / forward)
- Forward : No (désactivé)
- Modèle : « Every tick based on real ticks » (obligatoire)
- Dépôt initial : 10000 USD, levier 1:100
- Délai d'exécution : fixe 50 ms (pas « Random delay », pour des passes reproductibles)
- Optimisation : « Slow complete algorithm » (algorithme complet, 108 passes)
- Critère d'optimisation : Custom max (critère personnalisé maximum)
- Inputs à optimiser (cocher uniquement ceux-ci) :
- InpLeftBars : optimiser, Start=2, Step=1, Stop=10
- InpRightBars : optimiser, Start=1, Step=1, Stop=6
- InpBreakMode : optimiser, Start=0, Step=1, Stop=1
- Inputs fixes (décochés) :
- InpTradeEvents = 1 (CHOCH seulement) (NE PAS optimiser)
- InpRR = 3.0 (NE PAS optimiser)
- InpSLBufferATR = 0.1 (NE PAS optimiser)
- InpATRPeriod = 14 (NE PAS optimiser)
- InpMinRiskATR = 0.2 (NE PAS optimiser)
- InpMaxRiskATR = 5.0 (NE PAS optimiser)
- InpMaxBarsInTrade = 0 (NE PAS optimiser)
- InpOnePosition = true (NE PAS optimiser)
- InpLots = lot minimum du symbole (ex. 0.01 ; GER40 souvent 0.1 ou 1) (NE PAS optimiser)
- InpRandomMode = false (NE PAS optimiser)
- InpRandomSeed = 1 (NE PAS optimiser)
- InpMinTradesForScore = 100 (NE PAS optimiser)
- InpUseSession = true (NE PAS optimiser)
- InpSessionStart = "09:00" (NE PAS optimiser)
- InpSessionEnd = "18:30" (NE PAS optimiser)
Lance l'optimisation et préviens-moi quand elle est terminée. Ne modifie aucun autre réglage.
```

**Après l'étape B** : récupérez le nouveau `PA_M1_opt_GER40_M15_<AAAAMMJJ_HHMM>.csv`
(horodatage plus récent que celui de l'étape A) et copiez-le aussi dans `resultats/module1/`.
L'analyse distingue in-sample et forward grâce aux colonnes `from`/`to` du CSV.

> Important : on ne choisit **jamais** un réglage en regardant l'étape B. L'étape B sert
> uniquement à vérifier que le plateau trouvé en A reste positif.

## À renvoyer
- [ ] CSV de l'étape A (`PA_M1_opt_GER40_M15_....csv`, période 2021.01.01–2024.06.30)
- [ ] CSV de l'étape B (`PA_M1_opt_GER40_M15_....csv`, période 2024.07.01–2025.12.31)
- [ ] (optionnel) capture de l'onglet « Optimization results » ou export XML/HTML
- [ ] Toute erreur ou anomalie du Journal (onglet « Journal » du testeur)
