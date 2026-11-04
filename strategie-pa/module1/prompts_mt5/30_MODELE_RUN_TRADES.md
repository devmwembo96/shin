# 30 — MODÈLE : run simple « trades » sur le meilleur réglage

À lancer pour chaque combinaison retenue par le rapport (même réglage que le contrôle
aléatoire). Ce run produit le journal des trades, indispensable pour l'IC bootstrap, le
Monte-Carlo du drawdown et l'analyse des MFE (choix du RR).

```
Configure et lance un test simple (PAS d'optimisation) dans le Testeur de stratégie MT5 :
- Expert : PA_M1_Structure_EA
- Symbole : <SYMBOLE_BROKER>
- Période (timeframe) : <UT>
- Dates : du 2021.01.01 au 2025.12.31 (période complète in-sample + forward), Forward : No
- Modèle : « Every tick based on real ticks »
- Dépôt initial : 10000 USD, levier 1:100, délai : fixe 50 ms (pas « Random delay », pour des passes reproductibles)
- Visualisation : désactivée
- Inputs : InpLeftBars = <L> ; InpRightBars = <R> ; InpBreakMode = <B> ;
  InpTradeEvents = <E> ; InpRandomMode = false ; InpRR=3.0 ; InpSLBufferATR=0.1 ;
  InpATRPeriod=14 ; InpMinRiskATR=0.2 ; InpMaxRiskATR=5.0 ; InpMaxBarsInTrade=0 ;
  InpOnePosition=true ; InpMinTradesForScore=100 ; session identique à la grille
Lance le test et préviens-moi quand il est terminé.
```

**Après** : dans `Common\Files`, récupérez
`PA_M1_trades_<SYMBOLE>_<UT>_L<L>_R<R>_B<B>_E<E>.csv` (et le `PA_M1_opt_...csv` d'une ligne
produit en même temps). Copiez les deux dans `resultats/module1/`. Optionnel : clic droit sur
l'onglet « Backtest » → « Report » → enregistrer le rapport HTML à côté.

L'analyse coupe elle-même les trades en in-sample / forward à la date 2024.07.01.
