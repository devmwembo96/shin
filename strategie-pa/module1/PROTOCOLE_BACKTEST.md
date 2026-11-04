# Protocole de backtest — Module 1 (Structure : BOS / CHOCH)

Ce document explique, pas à pas, comment lancer les backtests du Module 1 dans MetaTrader 5,
où récupérer les fichiers CSV et quoi renvoyer. Vous n'avez pas besoin de savoir programmer.

**Principe absolu : aucun réglage universel.** Chaque couple actif × unité de temps (UT) est
testé séparément et reçoit ses propres réglages. Un réglage trouvé en H1 n'est jamais réutilisé
en M15 sans y avoir été testé.

---

## 1. Ce que fait l'EA `PA_M1_Structure_EA`

L'EA détecte les swings, la tendance, les BOS et les CHOCH (sans regarder le futur), puis
prend un trade à chaque événement pour **mesurer** sa valeur prédictive :

- entrée au marché à l'ouverture de la bougie suivant l'événement, dans le sens de l'événement ;
- stop au-delà du swing opposé (+ 0,1 × ATR), objectif à 3 R ;
- résultats exprimés en **R** (1 R = le risque du trade), spread réel inclus.

Ce n'est pas encore une stratégie à trader : c'est un instrument de mesure.

---

## 2. Installation des fichiers (une seule fois, puis à chaque nouvelle version)

1. Dans MT5 : menu **Fichier → Ouvrir le dossier des données** (*File → Open Data Folder*).
   Une fenêtre Windows s'ouvre ; entrez dans le dossier `MQL5`.
2. Copiez les fichiers du projet (dossier `mql5/` du dépôt) **en respectant les sous-dossiers** :

   | Fichier du projet | Destination dans le dossier de données |
   |---|---|
   | `mql5/Include/PA/PA_Structure.mqh` | `MQL5\Include\PA\PA_Structure.mqh` (créer le dossier `PA`) |
   | `mql5/Indicators/PA_Structure.mq5` | `MQL5\Indicators\PA_Structure.mq5` |
   | `mql5/Experts/PA_M1_Structure_EA.mq5` | `MQL5\Experts\PA_M1_Structure_EA.mq5` |

3. Ouvrez **MetaEditor** (touche **F4** dans MT5).
4. Dans le Navigateur de MetaEditor, ouvrez `Indicators\PA_Structure.mq5` puis appuyez sur
   **F7** (Compiler). Faites de même pour `Experts\PA_M1_Structure_EA.mq5`.
5. En bas, l'onglet **Erreurs** doit afficher `0 errors`. Les *warnings* ne bloquent pas.
   **S'il y a des erreurs** : copiez tout le texte de l'onglet Erreurs et renvoyez-le tel quel.
6. Dans MT5, faites clic droit sur « Expert Advisors » dans le Navigateur → **Actualiser**.
   `PA_M1_Structure_EA` doit apparaître.

> Après chaque mise à jour du code : recopier les fichiers **et recompiler les deux**.
> Le `.mqh` seul ne se compile pas ; il est inclus par l'indicateur et l'EA.

---

## 3. Où l'EA écrit ses CSV : le dossier `Common\Files`

L'EA écrit dans le dossier **commun** à tous les terminaux MT5 (pas dans le dossier du
terminal), ce qui permet de récupérer les fichiers même en optimisation.

- Chemin habituel : `C:\Users\<VotreNom>\AppData\Roaming\MetaQuotes\Terminal\Common\Files`
- Raccourci : touches **Windows + R**, tapez `%APPDATA%\MetaQuotes\Terminal\Common\Files`, Entrée.
- Autre accès : dans MetaEditor, Navigateur → clic droit sur un dossier → *Ouvrir le dossier* ;
  remontez jusqu'à `Terminal`, puis `Common\Files`.

Deux types de fichiers y apparaissent :

| Fichier | Produit par | Contenu |
|---|---|---|
| `PA_M1_opt_<SYMBOLE>_<UT>_<AAAAMMJJ_HHMM>.csv` | chaque optimisation (et chaque test simple) | une ligne par passe : réglages + statistiques en R |
| `PA_M1_trades_<SYMBOLE>_<UT>_L<l>_R<r>_B<b>_E<e>.csv` | test simple uniquement | une ligne par trade (entrée, sortie, résultat R, MFE, MAE…) |

> Utilisez de préférence les **agents locaux** du testeur. Les agents du réseau MQL5 Cloud
> ne posent pas de problème pour le CSV d'optimisation (il est écrit par votre terminal),
> mais ils coûtent de l'argent et sont inutiles ici (108 passes par run).

---

## 4. Réglages du Testeur de stratégie

Ouvrir le Testeur : **Affichage → Testeur de stratégie** (*Ctrl+R*). Onglet **Paramètres** (*Settings*) :

| Réglage | Valeur |
|---|---|
| Expert | `PA_M1_Structure_EA` |
| Symbole | XAUUSD ou GER40 (nom exact de votre broker, §9) |
| Période (*timeframe*) | l'UT du prompt (M1 … D1) |
| Dates | *Custom* : dates indiquées dans le prompt |
| Forward | *No* (on fait un run forward séparé, §6) |
| Délais (*Delays*) | délai **fixe** (ex. 50 ms). Évitez « Random delay » : les passes ne seraient pas reproductibles |
| Modèle (*Modelling*) | **Every tick based on real ticks** (ticks réels, spread réel) |
| Dépôt | 10 000 USD |
| Levier | 1:100 |
| Optimisation | *Slow complete algorithm* (algorithme complet) |
| Critère | **Custom max** |

**Modèle de ticks.** « Every tick based on real ticks » est obligatoire pour H1, H4, D1, M15,
M30 : c'est le seul qui utilise le spread réel. **Exception M1 / M5** : si un run dure trop
longtemps (plusieurs heures par passe), vous pouvez passer en **« 1 minute OHLC »**, à
condition de le **signaler** en ajoutant `_OHLC` à la fin du nom du CSV avant de le déposer
(ex. `PA_M1_opt_XAUUSD_M5_20260110_0930_OHLC.csv`). L'analyse marquera alors ces résultats
« à reconfirmer en real ticks » : ils ne pourront jamais obtenir directement le verdict EDGE PROBABLE.

**Coûts.** Le spread réel est inclus par les ticks réels. La commission est celle définie par
votre broker pour le symbole (si votre compte réel paie une commission séparée, vérifiez
qu'elle apparaît dans l'onglet *Backtest* / *Résultats*). Le délai fixe simule le glissement.

Onglet **Paramètres d'entrée** (*Inputs*) : cochez **uniquement** les inputs à optimiser et
renseignez Start / Step / Stop exactement comme dans le prompt ; décochez tous les autres et
saisissez leur valeur fixe.

---

## 5. Optimisation complète ou génétique ? Critère « Custom max »

- La grille de l'itération 1 fait **108 combinaisons** (9 LeftBars × 6 RightBars × 2 BreakMode).
  C'est petit : on utilise l'**algorithme complet** (*Slow complete algorithm*), qui teste
  **toutes** les combinaisons. Indispensable pour tracer des heatmaps sans trous et repérer
  des plateaux.
- L'**algorithme génétique** (*Fast genetic based algorithm*) ne teste qu'une partie de la
  grille et se concentre autour des meilleurs résultats : à réserver aux grilles de plus de
  ~5 000 combinaisons (itérations futures), et jamais pour tirer des heatmaps.
- **Critère « Custom max »** : l'EA calcule lui-même son score = `avg_R × √trades`
  (proche d'un t de Student de l'espérance), et 0 si moins de 100 trades. Ce score sert juste
  à trier l'onglet *Optimization results* ; **l'analyse ne prend pas le meilleur score** mais
  cherche un plateau stable (§2 du rapport).

---

## 6. In-sample / forward (out-of-sample)

On sépare chronologiquement :

| Période | Dates | Rôle |
|---|---|---|
| In-sample (IS) | 2021-01-01 → 2024-06-30 | trouver les plateaux de réglages |
| Forward (OOS) | 2024-07-01 → 2025-12-31 | vérifier que le plateau trouvé tient |

**Méthode recommandée : deux runs séparés** (étape A puis étape B de chaque prompt), avec la
même grille. Chaque run produit son CSV `PA_M1_opt_...` ; l'analyse reconnaît la période grâce
aux colonnes `from` / `to`. On ne choisit **jamais** un réglage en regardant le forward.

Alternative : un seul run 2021-01-01 → 2025-12-31 avec *Forward = 1/3* (ou date personnalisée
2024-07-01). Moins fiable pour nous : le CSV de l'EA mélangerait les deux phases ; à n'utiliser
que si vous ne pouvez pas faire deux runs, et dans ce cas renvoyez aussi l'export XML des
résultats Forward.

Si votre broker n'a pas d'historique de ticks depuis 2021 : décalez le début (ex. 2022-01-01)
en gardant ≈ 70 % IS / 30 % forward, et **indiquez-le** dans votre message.

---

## 7. Ordre de passage des runs

Suivez `prompts_mt5/00_INDEX.md` (cases à cocher). Résumé :

1. **Validation de la chaîne** : `01` et `02` (XAUUSD H1, BOS puis CHOCH), puis `03` et `04`
   (XAUUSD M15). Renvoyez ces CSV **avant** de continuer : on vérifie que l'EA, les fichiers
   et l'analyse fonctionnent (évite de perdre des heures de calcul en M1).
2. XAUUSD H4, M30, D1, puis M5 et M1 (les plus longs).
3. GER40 dans le même ordre : H1, M15, H4, M30, D1, M5, M1.
4. Après la première analyse : **contrôle aléatoire** et **run trades** (§8, §9) sur les
   combinaisons retenues seulement.

Chaque fichier de prompt = 2 runs (IS puis forward) = 2 CSV.

---

## 8. Run de contrôle aléatoire (pour chaque UT retenue)

But : vérifier qu'un BOS / CHOCH fait mieux qu'une entrée **au hasard** au même moment, avec
le même stop et le même objectif. L'EA garde le timing et le SL/TP mais tire la direction au
sort (`InpRandomMode = true`).

- Quand : pour chaque symbole × UT × événement classé « EDGE PROBABLE » ou « À CONFIRMER »
  par le rapport (section « Réglages retenus par UT »).
- Comment : prompt modèle `prompts_mt5/29_MODELE_CONTROLE_ALEATOIRE.md`, en remplaçant
  `<L>`, `<R>`, `<B>`, `<E>` par le réglage retenu **pour cette UT**. On optimise seulement
  `InpRandomSeed` de 1 à 30 → 30 tirages aléatoires.
- Résultat : un CSV `PA_M1_opt_...` dont les lignes ont `random_mode = 1`.

---

## 9. Run simple sur le meilleur réglage (CSV des trades)

- Quand : pour chaque combinaison retenue, avec le **réglage de cette UT** donné par le rapport.
- Comment : prompt modèle `prompts_mt5/30_MODELE_RUN_TRADES.md` — un **test simple**
  (pas d'optimisation) sur toute la période 2021-01-01 → 2025-12-31.
- Résultat : `PA_M1_trades_<SYMBOLE>_<UT>_L.._R.._B.._E...csv` (+ un petit `PA_M1_opt_...`).
  L'analyse en tire l'espérance avec intervalle de confiance, le drawdown Monte-Carlo et la
  distribution des MFE (pour proposer un meilleur ratio risque / rendement).
- Optionnel : onglet *Backtest* → clic droit → *Report* → enregistrer le rapport HTML.

---

## 10. Noms de symboles et session GER40

**Noms de symboles.** Ils varient selon le broker : l'or peut s'appeler `XAUUSD`, `GOLD`,
`XAUUSD.a`, `XAUUSDm`… ; le DAX `GER40`, `DE40`, `GER40.cash`, `DAX40`… Utilisez le nom exact
visible dans votre *Market Watch* (clic droit → *Symboles* pour l'afficher). Les prompts
utilisent `XAUUSD` et `GER40` : remplacez-les si besoin (ou modifiez `SYMBOLES` en haut de
`module1/generer_prompts.py` et relancez-le). L'analyse reconnaît automatiquement les
variantes courantes (GOLD, DE40, GER40.cash…).

**Historique de ticks.** Avant le premier run sur un symbole, ouvrez *Affichage → Symboles →
Ticks* pour forcer le téléchargement, ou acceptez le téléchargement demandé par le testeur
(cela peut prendre du temps la première fois).

**Session GER40.** Pour GER40 en M1 → H1, le filtre de session est activé
(`InpUseSession = true`). Les heures de l'EA sont en **heure du serveur du broker**, pas en
heure de Francfort :

- la plupart des brokers MT5 sont en GMT+2 l'hiver / GMT+3 l'été (« heure de New York + 7 ») ;
  Francfort est en GMT+1 / GMT+2 → **écart d'1 heure** → 08:00–17:30 Francfort = **09:00–18:30
  serveur** (valeurs mises dans les prompts) ;
- vérifiez chez votre broker : comparez l'heure affichée dans *Market Watch* à l'heure de
  Paris/Francfort. Si l'écart n'est pas d'1 heure, corrigez `InpSessionStart` / `InpSessionEnd`
  (ou `SESSION_GER40` dans le générateur) ;
- quelques semaines par an (mars et fin octobre / novembre), les changements d'heure
  américain et européen ne tombent pas le même jour : l'écart change d'1 heure pendant ces
  périodes. L'EA de l'itération 1 utilise des heures serveur fixes : c'est une approximation
  connue, à signaler mais sans impact majeur sur des mesures par événement ;
- en H4 et D1, le filtre de session est désactivé (une bougie couvre la session entière).

---

## 11. Nommage et dépôt des fichiers

- **Ne renommez pas** les CSV produits par l'EA. Seule exception : ajouter `_OHLC` avant
  `.csv` si le run a été fait en « 1 minute OHLC ».
- Copiez-les (pas besoin de supprimer les originaux) dans le dossier du projet
  **`resultats/module1/`**. Vous pouvez créer des sous-dossiers (ex. `resultats/module1/XAUUSD_H1/`) :
  l'analyse les parcourt tous.
- Si vous relancez un run identique, gardez les deux : l'analyse conserve automatiquement le
  plus récent pour un même réglage et une même période.
- Le rapport est écrit dans `resultats/module1/rapport/` : n'y déposez rien.

---

## 12. Check-list de ce qu'il faut renvoyer

Pour chaque prompt `NN_<SYMBOLE>_<UT>_<EVENEMENT>.md` :

- [ ] CSV d'optimisation **in-sample** (étape A)
- [ ] CSV d'optimisation **forward** (étape B)
- [ ] le modèle de ticks utilisé (real ticks ou `_OHLC` dans le nom)
- [ ] (optionnel) capture de l'onglet *Optimization results* ou export XML
- [ ] toute erreur du Journal du testeur, et les erreurs de compilation éventuelles

Après la première analyse, pour chaque combinaison retenue :

- [ ] CSV du contrôle aléatoire (30 graines)
- [ ] CSV des trades du run simple
- [ ] (optionnel) rapport HTML du run simple

Précisez aussi dans votre message : nom du broker, noms exacts des symboles, décalage
horaire serveur, début réel de l'historique de ticks si différent de 2021-01-01.

---

## 13. Lancer l'analyse (agent Claude ou vous-même)

```
python3 analyse/analyse_module1.py
```

Options : `--dossier <chemin des CSV>` (défaut `resultats/module1`), `--split 2024-07-01`
(début du forward). Dépendances : `pandas`, `numpy`, `matplotlib`.
Résultat : `resultats/module1/rapport/RAPPORT_MODULE1.md` (verdicts, heatmaps, tableau
« Réglages retenus par UT », plages proposées pour l'itération 2).

Itération suivante : coller le bloc `PLAGES_SPECIFIQUES` / `COMBINAISONS` du rapport dans
`module1/generer_prompts.py`, passer `ITERATION = 2`, puis `python3 module1/generer_prompts.py`.

---

## 14. Problèmes fréquents

| Symptôme | Cause probable / solution |
|---|---|
| Aucun CSV dans `Common\Files` | Mauvais dossier (vérifier `Common`, pas `Terminal\<ID>\MQL5\Files`) ; ou l'EA n'a pas été recompilé |
| Score 0 sur toutes les passes | Moins de 100 trades par passe (fréquent en D1) : ce n'est pas un bug |
| « No history » / test très court | Historique de ticks absent : forcer le téléchargement (§10) ou décaler la date de début |
| Passe très lente en M1 | Passer en « 1 minute OHLC » et ajouter `_OHLC` au nom du CSV |
| Le symbole n'est pas proposé | Afficher le symbole dans *Market Watch* (clic droit → Symboles) |
