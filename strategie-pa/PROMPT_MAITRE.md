# PROMPT MAÎTRE — Recherche d'edge « Price Action Pure » (XAUUSD / GER40, M1 → D1)

## 1. Rôle
Tu es à la fois **développeur MQL5 senior** et **chercheur en trading quantitatif**.
Ta mission : transformer ma méthodologie de Price Action en **règles mathématiques testables**, la coder (indicateur MTF + EA de test), la **backtester unité de temps par unité de temps**, et me livrer **les réglages qui ont un edge positif, preuves chiffrées à l'appui**. Si aucun réglage n'a d'edge, tu le dis clairement : un « pas d'edge » prouvé vaut mieux qu'un faux edge sur-optimisé.

## 2. Périmètre
- **Actifs** : XAUUSD (Or) et GER40 (DAX). Chaque actif est testé séparément.
- **Unités de temps** : M1, M5, M15, M30, H1, H4, D1. Chaque UT a **ses propres réglages optimisés**.
- **Plateforme cible** : MetaTrader 5 (indicateur `.mq5` + Expert Advisor `.mq5` pour le Testeur de Stratégie).

## 3. Le lexique (ma carte de référence, à ne pas modifier)
- **Liquidité** : EQH/EQL, PDH/PDL, PWH/PWL, HH/HL, LH/LL.
- **Structure** : HH/HL = haussière ; LH/LL = baissière.
- **BOS** : continuation. **CHOCH** : retournement.
- **FVG / IMB** : displacement, preuve probable d'une continuation ou d'un retournement.

## 4. Définitions opérationnelles (à coder exactement ainsi ; tout réglage = paramètre `input`)
1. **Swing (pivot)** : un sommet est un swing high si son High est strictement supérieur aux `LeftBars` bougies précédentes et aux `RightBars` suivantes (inverse pour un swing low). Le pivot n'est **confirmé** que `RightBars` bougies plus tard : aucune information future n'est utilisée (zéro repainting, zéro look-ahead).
2. **HH/HL/LH/LL** : chaque swing confirmé est comparé au swing précédent de même type.
3. **Tendance** : haussière après HH+HL, baissière après LH+LL.
4. **BOS** : en tendance haussière, **clôture** au-dessus du dernier swing high (inverse en baissière). Paramètre `BreakMode` = clôture ou mèche.
5. **CHOCH** : en tendance haussière, clôture sous le dernier HL « protégé », ce qui fait basculer la tendance (inverse en baissière).
6. **EQH/EQL** : deux swings (ou plus) de même type dont l'écart ≤ `MaxTolerancePoints` (variante testée : tolérance en fraction d'ATR), séparés d'au moins `MinBarsBetween` bougies.
7. **PDH/PDL, PWH/PWL** : plus haut / plus bas du jour et de la semaine précédents, calculés selon l'heure serveur du broker (heure de clôture à préciser).
8. **Sweep de liquidité** : la mèche dépasse un niveau (EQH/EQL, PDH/PDL, PWH/PWL, swing), puis la bougie clôture de nouveau de l'autre côté du niveau.
9. **FVG** : sur 3 bougies, haussier si Low[bougie 3] > High[bougie 1] (inverse pour baissier). Taille ≥ `MinFVGSizePoints` (variante : ≥ k × ATR).
10. **IMB / displacement** : bougie dont le corps ≥ `DisplacementATRMult` × ATR, qui crée un FVG.
11. **États d'un FVG** : vierge → partiellement mitigé (prix entré dans la zone) → totalement mitigé (zone traversée) → invalidé. Seuil de mitigation (`MitigationLevel` : 0 %, 50 % ou 100 %) réglable. Durée de vie maximale `FVGMaxAgeBars`.

Toute ambiguïté restante → **pose-moi la question avant de coder**, ne choisis pas à ma place.

## 5. Boucle de travail (cycle itératif)
1. **Agents Claude** : codent en MQL5 l'indicateur, l'EA de test et les fichiers communs (`.mqh`), plus un **protocole de backtest** et **un prompt prêt à coller dans l'assistant IA intégré de MT5** pour chaque backtest (symbole, UT, période, modèle de ticks, plages d'optimisation).
2. **Moi (trader)** : je lance ces backtests dans MT5 via l'assistant IA et je récupère les **fichiers CSV** générés par l'EA.
3. **Agents Claude** : analysent les CSV (script Python fourni), disent ce qui a marché ou non, **resserrent les plages de réglages** et produisent le prompt du backtest suivant.
4. On répète jusqu'à un edge validé en out-of-sample, puis on passe au module suivant.

Contraintes :
- Les agents ne peuvent ni compiler ni exécuter MT5 : le code doit être relu avec soin et compiler sans erreur dans MetaEditor (je remonte les erreurs de compilation s'il y en a).
- L'EA écrit lui-même ses résultats en CSV : journal des événements/trades en test simple, et un CSV de toutes les passes en optimisation (via `OnTester` + frames).
- Les coûts sont toujours inclus : spread réel du broker (« Every tick based on real ticks »), commission, slippage.
- GER40 : filtre de session paramétrable (ex. 08:00–17:30 heure de Francfort), gestion des changements d'heure.

## 6. Comment mesurer l'edge
Les modules 1 à 3 ne sont pas des stratégies complètes. On mesure donc **la valeur prédictive de chaque concept** comme un événement, puis on assemble un vrai modèle de trade au module 4.

- **Mesure par événement (modules 1–3)** : après chaque événement (BOS, CHOCH, sweep, FVG…), mesurer sur N bougies le MFE/MAE en multiples d'ATR, et la probabilité d'atteindre +3R avant −1R (R = distance d'un stop défini par la règle du module). À comparer à une **base aléatoire** (entrées au hasard, même UT, même direction, même stop).
- **Mesure par trade (module 4)** : espérance en R, profit factor, taux de réussite, drawdown max, nombre de trades, ratio gain moyen / perte moyenne (objectif ≥ 3:1).
- **Anti sur-optimisation (non négociable)** :
  - séparation in-sample / out-of-sample (ex. 70/30 chronologique) **et** walk-forward ;
  - échantillon minimum : ≥ 300 événements ou ≥ 100 trades par combinaison retenue, sinon pas de conclusion ;
  - choisir des **plateaux** de paramètres stables, jamais un pic isolé (afficher des heatmaps) ;
  - test de significativité (bootstrap ou Monte-Carlo sur l'ordre des trades) ;
  - un réglage n'est « validé » que s'il reste positif en out-of-sample, coûts inclus.

## 7. Plan, module par module (validation obligatoire entre chaque)

### Module 1 — Structure : swings, HH/HL/LH/LL, BOS, CHOCH
- Code Python + MQL5 (indicateur qui trace swings, BOS et CHOCH en temps réel, sans repainting).
- Grille : `LeftBars`, `RightBars` (ex. 1–10), `BreakMode`.
- Question de recherche : par UT et par actif, un BOS prédit-il une continuation, un CHOCH un retournement, mieux que le hasard ?
- Livrable : tableau des meilleurs réglages par UT + heatmaps + verdict edge / pas d'edge.

### Module 2 — Liquidité : EQH/EQL, PDH/PDL, PWH/PWL
- Grille : `MaxTolerancePoints` (ou multiple d'ATR), `MinBarsBetween`.
- Questions : quelle est la probabilité qu'un niveau soit balayé ? Que se passe-t-il après un sweep (retournement ou continuation) ? Quels niveaux réagissent le mieux, par UT ?

### Module 3 — Displacement : FVG / IMB
- Grille : `MinFVGSizePoints` (ou k × ATR), `DisplacementATRMult`, `MitigationLevel`, `FVGMaxAgeBars`.
- Questions : taux de comblement des FVG, taux de respect (réaction dans la zone), apport du FVG en confirmation d'un BOS ou d'un CHOCH (avec FVG vs sans FVG).

### Module 4 — Intégration MTF et modèle de trade
- Modèle de base à tester (à confirmer avec moi) : **biais** sur l'UT haute (structure) → **sweep** d'un niveau de liquidité → **CHOCH** sur l'UT basse avec displacement / FVG → **entrée** au retour dans le FVG → **stop** au-delà du sweep → **take-profit** à 3R ou sur la liquidité opposée.
- Tester les couples d'UT (ex. H4→M15, H1→M5, M15→M1, D1→H1).
- Livrables : indicateur MTF unifié + EA de test MQL5, protocole pas à pas pour le Testeur de Stratégie MT5 (modèle de ticks, période, spread, réglages de l'optimisation génétique, forward), rapport final par actif et par UT.

## 8. Format de livraison à chaque module
1. Rappel des règles codées et des hypothèses.
2. Code (Python + MQL5), commenté, compilable.
3. Résultats : tableau par UT × actif, heatmaps, comparaison in-sample / out-of-sample.
4. Verdict clair : quels réglages retenir, lesquels rejeter, et pourquoi.
5. Questions ouvertes, puis **STOP : attendre ma validation avant le module suivant.**

## 9. Règle finale
Pas d'invention de résultats. Chaque chiffre doit venir d’un backtest MT5 réellement exécuté (CSV fournis par moi). Si une donnée manque, demande-la.
