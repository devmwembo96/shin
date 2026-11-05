# Rapport Module 1 — Structure (BOS / CHOCH)

Généré le 2026-11-05 10:12 par `analyse/analyse_module1.py` à partir de **2 fichier(s) CSV** dans `resultats/module1`. Début du forward : 2024-07-01. Tous les chiffres proviennent des CSV de l'EA (coûts du testeur inclus) ; rien n'est extrapolé.

## 1. Verdict par symbole × UT

| Symbole | UT | Verdict | Détail | avg_R IS | trades | avg_R OOS | p aléa |
|---|---|---|---|---|---|---|---|
| XAUUSD | H1 | **PAS D'EDGE** | BOS : PAS D'EDGE | — | — | — | — |


Détail des conditions : `synthese_verdicts.csv`.

## 2. Règles de verdict (appliquées automatiquement)

Les verdicts sont calculés pour chaque symbole × UT × type d'événement, sur le
**plateau retenu** en in-sample (IS). Une cellule de grille n'est valide que si elle a
**≥ 100 trades**. Le « plateau » d'une cellule = moyenne de avg_R sur la cellule et ses
voisines LeftBars ±1 / RightBars ±1 (même BreakMode). On retient la cellule dont le plateau
est le plus élevé (parmi celles dont ≥ 75% du voisinage est valide), **jamais le pic isolé** :
le tri se fait d'abord sur « ≥ 70% de voisins positifs », puis sur la moyenne du voisinage
**sans sa meilleure valeur** (un pic isolé ne peut donc pas tirer ses voisins), puis sur la moyenne.

Conditions :
- **C0 Échantillon** : au moins une cellule IS avec ≥ 100 trades.
- **C1 Plateau positif** : plateau > 0, avg_R de la cellule centrale > 0, et ≥ 70% des
  cellules voisines valides ont avg_R > 0.
- **C2 Significativité IS** : t-stat approx. ≥ 2.0 (avg_R × √trades / σ estimé), **ou**
  borne basse de l'IC 95 % bootstrap > 0 si le CSV des trades de ce réglage est fourni.
- **C3 Forward (OOS)** : même réglage sur la période forward avec ≥ 40 trades et avg_R > 0
  (lu dans le CSV d'optimisation forward, à défaut dans la partie OOS du CSV de trades).
- **C4 Contrôle aléatoire** : avg_R réel supérieur à au moins 95 % des runs aléatoires
  (p empirique ≤ 0.05) ; si moins de 5 runs aléatoires : z ≥ 1,96.

Verdict :
- **EDGE PROBABLE** : C0, C1, C2, C3 et C4 tous vrais (et grille testée en real ticks).
- **PAS D'EDGE** : C0 faux (échantillon insuffisant), ou C1 faux, ou C3 évalué et faux
  (OOS ≥ 40 trades avec avg_R ≤ 0), ou C4 évalué avec p > 0.2.
- **À CONFIRMER** : tous les autres cas (C1 vrai mais C2, C3 ou C4 manquant ou non atteint
  sans être réfuté ; ou grille en « 1 minute OHLC » à reconfirmer en real ticks).

Le verdict symbole × UT = meilleur verdict entre BOS et CHOCH (détail affiché).

## 3. Fichiers lus et avertissements

| fichier | type | lignes |
|---|---|---|
| PA_M1_opt_XAUUSD_H1_20261105_1029.csv | optimisation | 108 |
| PA_M1_opt_XAUUSD_H1_20261105_1037.csv | optimisation | 108 |

## 4. Détail par symbole × UT × événement

### XAUUSD H1 — BOS (RR=3, SLBuffer=0.10 ATR)

Passes in-sample : 108, dont 0 avec ≥ 100 trades.

**Aucune passe avec ≥ 100 trades : échantillon insuffisant.** Max trades observé : 44.

## 5. Analyse des journaux de trades

_Aucun CSV de trades fourni (prompt modèle RUN_TRADES)._

## 6. Suggestions pour l'itération 2

Aucune combinaison avec un plateau positif : rien à resserrer. Si C0 était faux (échantillon insuffisant), envisager une période plus longue ou InpTradeEvents=2.

## 7. Prochaines étapes

Rien de manquant pour les combinaisons retenues.

## 8. Réglages retenus par UT

Aucun réglage universel : chaque ligne est choisie **uniquement** à partir des passes in-sample de ce symbole × UT × événement (plateau retenu, §2). Aucun « meilleur réglage global » toutes UT confondues n'est calculé.

| Symbole | UT | Événement | LeftBars | RightBars | BreakMode | trades | avg_R IS | avg_R forward | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD | H1 | BOS | — | — | — | — | — | — | PAS D'EDGE |


(« — » = pas de réglage retenu : échantillon insuffisant. Un réglage « PAS D'EDGE » est listé pour mémoire, il n'est pas recommandé.)


_STOP : validation du trader requise avant l'itération suivante._
