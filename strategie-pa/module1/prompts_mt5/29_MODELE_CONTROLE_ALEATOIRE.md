# 29 — MODÈLE : contrôle aléatoire (une fois par symbole × UT × événement retenu)

À lancer **après** la première analyse, uniquement pour les combinaisons classées
« EDGE PROBABLE » ou « À CONFIRMER » dans `resultats/module1/rapport/RAPPORT_MODULE1.md`.
Le rapport indique le réglage à utiliser (LeftBars, RightBars, BreakMode).

Remplacez les `<...>` puis collez le bloc dans l'assistant IA de MT5 :

```
Configure et lance une optimisation dans le Testeur de stratégie MT5 :
- Expert : PA_M1_Structure_EA
- Symbole : <SYMBOLE_BROKER>
- Période (timeframe) : <UT>
- Dates : du 2021.01.01 au 2024.06.30 (in-sample), Forward : No
- Modèle : « Every tick based on real ticks » (ou « 1 minute OHLC » si c'est celui utilisé pour la grille)
- Dépôt initial : 10000 USD, levier 1:100, délai : fixe 50 ms (pas « Random delay », pour des passes reproductibles)
- Optimisation : « Slow complete algorithm », critère : Custom max (critère personnalisé maximum)
- Inputs à optimiser : InpRandomSeed : Start=1, Step=1, Stop=30
- Inputs fixes : InpRandomMode = true ; InpLeftBars = <L> ; InpRightBars = <R> ;
  InpBreakMode = <B> ; InpTradeEvents = <E> ; tous les autres inputs identiques à la grille
  (InpRR=3.0, InpSLBufferATR=0.1, InpATRPeriod=14, InpMinRiskATR=0.2, InpMaxRiskATR=5.0,
  InpMaxBarsInTrade=0, InpOnePosition=true, InpMinTradesForScore=100, session identique)
Lance l'optimisation et préviens-moi quand elle est terminée.
```

Optionnel (recommandé si le temps le permet) : refaire le même contrôle sur la période
forward 2024.07.01 → 2025.12.31.

**Après** : copiez le `PA_M1_opt_<SYMBOLE>_<UT>_<AAAAMMJJ_HHMM>.csv` produit dans
`resultats/module1/`. Les lignes ont `random_mode=1` : l'analyse les reconnaît seule.
