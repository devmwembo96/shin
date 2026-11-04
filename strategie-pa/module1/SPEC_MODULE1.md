# Spécification Module 1 — Structure (contrat commun à tous les agents)

## Arborescence
- `mql5/Include/PA/PA_Structure.mqh` : logique unique (swings, HH/HL/LH/LL, tendance, BOS, CHOCH). Utilisée par l'indicateur ET l'EA.
- `mql5/Indicators/PA_Structure.mq5` : affichage (flèches swings, labels HH/HL/LH/LL, lignes + texte BOS/CHOCH).
- `mql5/Experts/PA_M1_Structure_EA.mq5` : EA de test qui trade les événements et exporte les CSV.
- `module1/PROTOCOLE_BACKTEST.md`, `module1/prompts_mt5/*.md` : protocole et prompts pour l'assistant IA de MT5.
- `analyse/analyse_module1.py` : analyse des CSV.
- `resultats/module1/` : le trader y dépose les CSV.

## Règles (cf. PROMPT_MAITRE.md §4)
- Swing high à la barre i : High[i] > High des `InpLeftBars` barres avant ET des `InpRightBars` barres après. Confirmé seulement à la clôture de la barre i+RightBars. Pas de look-ahead.
- HH/LH : swing high comparé au swing high confirmé précédent ; HL/LL idem pour les lows.
- État de tendance : UP, DOWN, NONE. Départ NONE.
- Cassure évaluée à la clôture de bougie. `InpBreakMode` : 0 = clôture au-delà du niveau, 1 = mèche au-delà.
- En UP : cassure du dernier swing high confirmé = BOS_UP. Cassure du dernier swing low « protégé » (le swing low ayant précédé le dernier BOS_UP / dernier HL) = CHOCH_DN → tendance DOWN. Symétrique en DOWN.
- En NONE : la première cassure d'un swing (haut → UP, bas → DOWN) est un BOS initial, non tradé.
- Un même swing ne peut être cassé qu'une fois.

## Modèle de trade de l'EA (Module 1 = mesure de la valeur prédictive)
- `InpTradeEvents` : 0 = BOS seulement, 1 = CHOCH seulement, 2 = les deux.
- Entrée au marché à l'ouverture de la barre suivant l'événement, dans le sens de l'événement (BOS_UP/CHOCH_UP = achat).
- SL : au-delà du swing opposé de référence (achat : dernier swing low confirmé) ± `InpSLBufferATR` × ATR(`InpATRPeriod`). Si risque < `InpMinRiskATR` × ATR ou > `InpMaxRiskATR` × ATR → pas de trade (loggé SKIP).
- TP = entrée ± `InpRR` × risque (défaut 3.0). Sortie forcée après `InpMaxBarsInTrade` barres (0 = désactivé).
- Une position à la fois (`InpOnePosition`=true). Lot fixe `InpLots` (résultats évalués en R, pas en argent).
- Filtre session optionnel : `InpUseSession`, `InpSessionStart`, `InpSessionEnd` (heure serveur, "HH:MM").
- Mode **contrôle aléatoire** `InpRandomMode` (bool) + `InpRandomSeed` : remplace la direction par un tirage aléatoire, même timing/SL/TP → base de comparaison.
- Pour chaque trade on suit MFE/MAE (en R) jusqu'à la sortie.

## CSV 1 — journal des trades (test simple uniquement, pas en optimisation)
Fichier : `PA_M1_trades_<SYMBOL>_<TF>_L<left>_R<right>_B<mode>_E<events>.csv`, dossier Common\Files (`FILE_COMMON`), séparateur `;`, point décimal `.`, en-tête :
`open_time;close_time;symbol;tf;event;direction;entry;sl;tp;risk_points;atr_points;exit_price;exit_reason;result_R;mfe_R;mae_R;bars_held;spread_points;left_bars;right_bars;break_mode;trade_events;random_mode`
- event ∈ BOS_UP, BOS_DN, CHOCH_UP, CHOCH_DN ; direction ∈ BUY, SELL ; exit_reason ∈ TP, SL, TIME, END.
- result_R calculé sur prix réels de sortie (spread inclus).

## CSV 2 — synthèse des passes d'optimisation
Fichier : `PA_M1_opt_<SYMBOL>_<TF>_<YYYYMMDD_HHMM>.csv`, Common\Files. Produit via `OnTester()` (calcule stats, `FrameAdd`) + `OnTesterInit/OnTesterPass/OnTesterDeinit` (collecte et écrit). En test simple, écrire aussi une ligne.
En-tête :
`pass;symbol;tf;from;to;left_bars;right_bars;break_mode;trade_events;sl_buffer_atr;rr;random_mode;trades;wins;losses;timeouts;winrate;avg_R;sum_R;profit_factor_R;max_dd_R;avg_win_R;avg_loss_R;max_consec_losses;net_profit;balance_dd_pct`
- Stats R calculées par l'EA lui-même (liste des result_R des trades clos).

## Critère d'optimisation (OnTester return)
`trades < InpMinTradesForScore` (défaut 100) → 0. Sinon `avg_R * sqrt(trades)` (≈ t-stat de l'espérance), renvoyé tel quel (peut être négatif). À utiliser avec « Custom max ».

## Plages d'optimisation, itération 1
LeftBars 2..10 pas 1 ; RightBars 1..6 pas 1 ; BreakMode 0..1 ; TradeEvents 0..1 (séparés) ; RR fixe 3.0 ; SLBufferATR fixe 0.1.

## Périodes
In-sample : 2021-01-01 → 2024-06-30. Out-of-sample (forward) : 2024-07-01 → 2025-12-31 (ajuster à l'historique dispo du broker). Utiliser le « Forward » 1/3 du Testeur ou deux runs séparés.
UT : M1, M5, M15, M30, H1, H4, D1. Symboles : XAUUSD, GER40 (nom exact selon broker, ex. GOLD, DE40, GER40.cash).
