# Index des backtests — Module 1, itération 1

Fichiers générés par `module1/generer_prompts.py` (ne pas éditer à la main : modifier le
script et relancer). Protocole complet : `module1/PROTOCOLE_BACKTEST.md`.

**Ordre recommandé** : suivre les numéros. Les lignes 01 à 04 (XAUUSD H1 puis M15) servent à
valider toute la chaîne (EA → CSV → analyse). Après le 04, renvoyez les 4 paires de CSV et
attendez le retour de l'analyse avant de continuer.

Chaque fichier = **2 runs** (A in-sample 2021.01.01→2024.06.30, B forward 2024.07.01→2025.12.31) → 2 CSV `PA_M1_opt_...`.

| Fait | N° | Fichier | Symbole | UT | Événement | Passes/run | Modèle de ticks |
|---|---|---|---|---|---|---|---|
| [ ] | 01 | [01_XAUUSD_H1_BOS.md](01_XAUUSD_H1_BOS.md) | XAUUSD | H1 | BOS (E=0) | 108 | real ticks |
| [ ] | 02 | [02_XAUUSD_H1_CHOCH.md](02_XAUUSD_H1_CHOCH.md) | XAUUSD | H1 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 03 | [03_XAUUSD_M15_BOS.md](03_XAUUSD_M15_BOS.md) | XAUUSD | M15 | BOS (E=0) | 108 | real ticks |
| [ ] | 04 | [04_XAUUSD_M15_CHOCH.md](04_XAUUSD_M15_CHOCH.md) | XAUUSD | M15 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 05 | [05_XAUUSD_H4_BOS.md](05_XAUUSD_H4_BOS.md) | XAUUSD | H4 | BOS (E=0) | 108 | real ticks |
| [ ] | 06 | [06_XAUUSD_H4_CHOCH.md](06_XAUUSD_H4_CHOCH.md) | XAUUSD | H4 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 07 | [07_XAUUSD_M30_BOS.md](07_XAUUSD_M30_BOS.md) | XAUUSD | M30 | BOS (E=0) | 108 | real ticks |
| [ ] | 08 | [08_XAUUSD_M30_CHOCH.md](08_XAUUSD_M30_CHOCH.md) | XAUUSD | M30 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 09 | [09_XAUUSD_D1_BOS.md](09_XAUUSD_D1_BOS.md) | XAUUSD | D1 | BOS (E=0) | 108 | real ticks |
| [ ] | 10 | [10_XAUUSD_D1_CHOCH.md](10_XAUUSD_D1_CHOCH.md) | XAUUSD | D1 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 11 | [11_XAUUSD_M5_BOS.md](11_XAUUSD_M5_BOS.md) | XAUUSD | M5 | BOS (E=0) | 108 | real ticks / 1m OHLC |
| [ ] | 12 | [12_XAUUSD_M5_CHOCH.md](12_XAUUSD_M5_CHOCH.md) | XAUUSD | M5 | CHOCH (E=1) | 108 | real ticks / 1m OHLC |
| [ ] | 13 | [13_XAUUSD_M1_BOS.md](13_XAUUSD_M1_BOS.md) | XAUUSD | M1 | BOS (E=0) | 108 | real ticks / 1m OHLC |
| [ ] | 14 | [14_XAUUSD_M1_CHOCH.md](14_XAUUSD_M1_CHOCH.md) | XAUUSD | M1 | CHOCH (E=1) | 108 | real ticks / 1m OHLC |
| [ ] | 15 | [15_GER40_H1_BOS.md](15_GER40_H1_BOS.md) | GER40 | H1 | BOS (E=0) | 108 | real ticks |
| [ ] | 16 | [16_GER40_H1_CHOCH.md](16_GER40_H1_CHOCH.md) | GER40 | H1 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 17 | [17_GER40_M15_BOS.md](17_GER40_M15_BOS.md) | GER40 | M15 | BOS (E=0) | 108 | real ticks |
| [ ] | 18 | [18_GER40_M15_CHOCH.md](18_GER40_M15_CHOCH.md) | GER40 | M15 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 19 | [19_GER40_H4_BOS.md](19_GER40_H4_BOS.md) | GER40 | H4 | BOS (E=0) | 108 | real ticks |
| [ ] | 20 | [20_GER40_H4_CHOCH.md](20_GER40_H4_CHOCH.md) | GER40 | H4 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 21 | [21_GER40_M30_BOS.md](21_GER40_M30_BOS.md) | GER40 | M30 | BOS (E=0) | 108 | real ticks |
| [ ] | 22 | [22_GER40_M30_CHOCH.md](22_GER40_M30_CHOCH.md) | GER40 | M30 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 23 | [23_GER40_D1_BOS.md](23_GER40_D1_BOS.md) | GER40 | D1 | BOS (E=0) | 108 | real ticks |
| [ ] | 24 | [24_GER40_D1_CHOCH.md](24_GER40_D1_CHOCH.md) | GER40 | D1 | CHOCH (E=1) | 108 | real ticks |
| [ ] | 25 | [25_GER40_M5_BOS.md](25_GER40_M5_BOS.md) | GER40 | M5 | BOS (E=0) | 108 | real ticks / 1m OHLC |
| [ ] | 26 | [26_GER40_M5_CHOCH.md](26_GER40_M5_CHOCH.md) | GER40 | M5 | CHOCH (E=1) | 108 | real ticks / 1m OHLC |
| [ ] | 27 | [27_GER40_M1_BOS.md](27_GER40_M1_BOS.md) | GER40 | M1 | BOS (E=0) | 108 | real ticks / 1m OHLC |
| [ ] | 28 | [28_GER40_M1_CHOCH.md](28_GER40_M1_CHOCH.md) | GER40 | M1 | CHOCH (E=1) | 108 | real ticks / 1m OHLC |

## Après la grille (sur les combinaisons retenues par le rapport)
| Fait | N° | Fichier | Rôle |
|---|---|---|---|
| [ ] | 29 | [29_MODELE_CONTROLE_ALEATOIRE.md](29_MODELE_CONTROLE_ALEATOIRE.md) | Contrôle aléatoire (InpRandomMode=true, graines 1–30) |
| [ ] | 30 | [30_MODELE_RUN_TRADES.md](30_MODELE_RUN_TRADES.md) | Run simple sur le meilleur réglage → CSV des trades |

## Rappel des dépôts
Tous les CSV vont dans `resultats/module1/` (sans les renommer, sauf ajout de `_OHLC`), puis :
`python3 analyse/analyse_module1.py`
