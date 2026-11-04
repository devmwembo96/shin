#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur des prompts MT5 du Module 1 (Structure : BOS / CHOCH).

Usage :
    python3 module1/generer_prompts.py

Produit un fichier .md par backtest (symbole x UT x type d'événement) dans
module1/prompts_mt5/ (itération 1) ou module1/prompts_mt5/iteration_<N>/
(itérations suivantes), plus un 00_INDEX.md et deux modèles :
contrôle aléatoire et run simple « trades ».

Pour une nouvelle itération : modifier les PARAMÈTRES ci-dessous
(ITERATION, PLAGES_DEFAUT, PLAGES_SPECIFIQUES, COMBINAISONS...) puis relancer.
Le rapport d'analyse (analyse/analyse_module1.py) propose un bloc
PLAGES_SPECIFIQUES prêt à coller ici.

Aucune dépendance hors bibliothèque standard.
"""

import os

# =============================================================================
# PARAMÈTRES (à modifier aux itérations suivantes)
# =============================================================================

ITERATION = 1

EA_NOM = "PA_M1_Structure_EA"   # nom de l'Expert dans le Navigateur MT5

# Périodes (format MT5 AAAA.MM.JJ)
IS_DEBUT = "2021.01.01"
IS_FIN = "2024.06.30"
OOS_DEBUT = "2024.07.01"
OOS_FIN = "2025.12.31"

# Symboles : nom « logique » -> nom à utiliser chez le broker (à adapter).
SYMBOLES = {
    "XAUUSD": "XAUUSD",   # ex. GOLD, XAUUSD.a, XAUUSDm selon le broker
    "GER40": "GER40",     # ex. DE40, GER40.cash, DAX40 selon le broker
}

# Ordre de passage recommandé des UT (H1 et M15 d'abord pour valider la chaîne).
ORDRE_UT = ["H1", "M15", "H4", "M30", "D1", "M5", "M1"]
ORDRE_SYMBOLES = ["XAUUSD", "GER40"]

# Types d'événements : valeur de InpTradeEvents -> libellé
EVENEMENTS = {0: "BOS", 1: "CHOCH"}

# UT pour lesquelles le modèle « Every tick based on real ticks » est souvent
# trop lent sur une grille complète : on autorise « 1 minute OHLC » en le signalant.
UT_OHLC_AUTORISE = ["M1", "M5"]

# Plages optimisées par défaut : nom_input -> (start, step, stop)
PLAGES_DEFAUT = {
    "InpLeftBars": (2, 1, 10),
    "InpRightBars": (1, 1, 6),
    "InpBreakMode": (0, 1, 1),
}

# AUCUN réglage universel : chaque symbole x UT peut (et doit, dès l'itération 2)
# avoir ses propres plages. Priorité : PLAGES_SPECIFIQUES (symbole, UT, événement)
# > PLAGES_PAR_UT (symbole, UT) > PLAGES_DEFAUT.
# Seuls les inputs listés remplacent ceux du niveau inférieur.
# Exemple :
# PLAGES_PAR_UT = {
#     ("XAUUSD", "M5"): {"InpLeftBars": (3, 1, 12), "InpRightBars": (2, 1, 6)},
#     ("GER40", "H4"): {"InpLeftBars": (2, 1, 6)},
# }
PLAGES_PAR_UT = {}

# Surcharges par combinaison (symbole, UT, InpTradeEvents) -> dict de plages.
# Exemple (itération 2) :
# PLAGES_SPECIFIQUES = {
#     ("XAUUSD", "H1", 0): {"InpLeftBars": (4, 1, 8), "InpRightBars": (2, 1, 4),
#                           "InpBreakMode": (0, 1, 0)},
# }
PLAGES_SPECIFIQUES = {}

# Combinaisons à générer. None = toutes (symboles x UT x événements).
# Sinon liste de tuples (symbole, UT, InpTradeEvents).
COMBINAISONS = None

# Inputs fixes (non optimisés). Valeurs = hypothèses de l'itération 1.
# Les inputs non listés ici gardent la valeur par défaut de l'EA.
INPUTS_FIXES = {
    "InpRR": "3.0",
    "InpSLBufferATR": "0.1",
    "InpATRPeriod": "14",
    "InpMinRiskATR": "0.2",
    "InpMaxRiskATR": "5.0",
    "InpMaxBarsInTrade": "0",
    "InpOnePosition": "true",
    "InpLots": "lot minimum du symbole (ex. 0.01 ; GER40 souvent 0.1 ou 1)",
    "InpRandomMode": "false",
    "InpRandomSeed": "1",
    "InpMinTradesForScore": "100",
}

# Filtre de session GER40 (heure SERVEUR du broker !).
# 08:00-17:30 heure de Francfort = 09:00-18:30 pour un serveur en GMT+2/GMT+3
# (cas le plus courant). À ADAPTER à l'écart serveur/Francfort de votre broker.
SESSION_GER40 = {"start": "09:00", "end": "18:30"}
# UT sur lesquelles le filtre de session GER40 est activé (inutile en H4/D1).
UT_SESSION_GER40 = ["M1", "M5", "M15", "M30", "H1"]

# Réglages du Testeur
DEPOT = "10000 USD"
LEVIER = "1:100"
DELAI = "fixe 50 ms (pas « Random delay », pour des passes reproductibles)"
CRITERE = "Custom max (critère personnalisé maximum)"

# Contrôle aléatoire : graines testées
GRAINES = (1, 1, 30)

# =============================================================================
# FIN DES PARAMÈTRES
# =============================================================================

ICI = os.path.dirname(os.path.abspath(__file__))
if ITERATION == 1:
    DOSSIER_SORTIE = os.path.join(ICI, "prompts_mt5")
else:
    DOSSIER_SORTIE = os.path.join(ICI, "prompts_mt5", "iteration_%d" % ITERATION)


def nb_valeurs(start, step, stop):
    if step == 0:
        return 1
    return int(round((stop - start) / step)) + 1


def plages_pour(sym, ut, ev):
    p = dict(PLAGES_DEFAUT)
    p.update(PLAGES_PAR_UT.get((sym, ut), {}))
    p.update(PLAGES_SPECIFIQUES.get((sym, ut, ev), {}))
    return p


def nb_passes(plages):
    n = 1
    for (a, s, b) in plages.values():
        n *= nb_valeurs(a, s, b)
    return n


def inputs_fixes_pour(sym, ut, ev):
    fixes = {"InpTradeEvents": "%d (%s seulement)" % (ev, EVENEMENTS[ev])}
    fixes.update(INPUTS_FIXES)
    if sym == "GER40" and ut in UT_SESSION_GER40:
        fixes["InpUseSession"] = "true"
        fixes["InpSessionStart"] = '"%s"' % SESSION_GER40["start"]
        fixes["InpSessionEnd"] = '"%s"' % SESSION_GER40["end"]
    else:
        fixes["InpUseSession"] = "false"
    return fixes


def modele_ticks(ut):
    if ut in UT_OHLC_AUTORISE:
        return ("« Every tick based on real ticks » si la durée est acceptable ; "
                "sinon « 1 minute OHLC » (à SIGNALER : ajouter _OHLC au nom du "
                "fichier CSV avant de le déposer)")
    return "« Every tick based on real ticks » (obligatoire)"


def bloc_plages(plages):
    lignes = ["| Input | Start | Step | Stop | Nb valeurs |",
              "|---|---|---|---|---|"]
    for k, (a, s, b) in plages.items():
        lignes.append("| %s | %s | %s | %s | %d |" % (k, a, s, b, nb_valeurs(a, s, b)))
    return "\n".join(lignes)


def texte_plages_prompt(plages):
    return "\n".join("- %s : optimiser, Start=%s, Step=%s, Stop=%s"
                     % (k, a, s, b) for k, (a, s, b) in plages.items())


def texte_fixes_prompt(fixes):
    return "\n".join("- %s = %s (NE PAS optimiser)" % (k, v) for k, v in fixes.items())


def prompt_optimisation(sym, ut, ev, debut, fin, phase, plages, fixes):
    sym_b = SYMBOLES[sym]
    return """Configure et lance une optimisation dans le Testeur de stratégie MT5 :
- Expert : {ea}
- Symbole : {sym_b}
- Période (timeframe du graphique) : {ut}
- Dates : du {debut} au {fin} (période « Custom », {phase})
- Forward : No (désactivé)
- Modèle : {modele}
- Dépôt initial : {depot}, levier {levier}
- Délai d'exécution : {delai}
- Optimisation : « Slow complete algorithm » (algorithme complet, {np} passes)
- Critère d'optimisation : {critere}
- Inputs à optimiser (cocher uniquement ceux-ci) :
{plages}
- Inputs fixes (décochés) :
{fixes}
Lance l'optimisation et préviens-moi quand elle est terminée. Ne modifie aucun autre réglage.""".format(
        ea=EA_NOM, sym_b=sym_b, ut=ut, debut=debut, fin=fin, phase=phase,
        modele=modele_ticks(ut), depot=DEPOT, levier=LEVIER, delai=DELAI,
        np=nb_passes(plages), critere=CRITERE,
        plages=texte_plages_prompt(plages), fixes=texte_fixes_prompt(fixes))


def nom_fichier(num, sym, ut, ev):
    return "%02d_%s_%s_%s.md" % (num, sym, ut, EVENEMENTS[ev])


def generer_fichier(num, sym, ut, ev):
    plages = plages_pour(sym, ut, ev)
    fixes = inputs_fixes_pour(sym, ut, ev)
    lib = EVENEMENTS[ev]
    pA = prompt_optimisation(sym, ut, ev, IS_DEBUT, IS_FIN, "IN-SAMPLE", plages, fixes)
    pB = prompt_optimisation(sym, ut, ev, OOS_DEBUT, OOS_FIN, "OUT-OF-SAMPLE / forward", plages, fixes)
    note_session = ""
    if "InpSessionStart" in fixes:
        note_session = ("\n> **Session GER40** : %s–%s est exprimé en **heure serveur** "
                        "(= 08:00–17:30 Francfort pour un serveur GMT+2/+3). Vérifiez l'écart "
                        "chez votre broker (voir PROTOCOLE_BACKTEST.md §9) et corrigez si besoin.\n"
                        % (SESSION_GER40["start"], SESSION_GER40["end"]))
    note_ohlc = ""
    if ut in UT_OHLC_AUTORISE:
        note_ohlc = ("\n> **%s** : si « real ticks » est trop long, utilisez « 1 minute OHLC » "
                     "et ajoutez `_OHLC` à la fin du nom des CSV (ex. `..._OHLC.csv`). "
                     "Les résultats seront alors marqués « à reconfirmer en real ticks ».\n" % ut)
    if ut == "D1":
        note_ohlc += ("\n> **D1** : ~900 bougies sur l'in-sample ; il est probable que peu de "
                      "réglages atteignent 100 trades. Un score de 0 = échantillon insuffisant, "
                      "pas un bug.\n")
    sym_b = SYMBOLES[sym]
    return """# {num:02d} — {sym} {ut} — {lib} (Module 1, itération {it})

| Élément | Valeur |
|---|---|
| EA | `{ea}` |
| Symbole | {sym} (nom broker : `{sym_b}` — à adapter) |
| UT | {ut} |
| Événements | InpTradeEvents = {ev} ({lib} seulement) |
| In-sample | {isd} → {isf} |
| Forward (OOS) | {ood} → {oof} (run séparé) |
| Modèle de ticks | {modele} |
| Passes | {np} par run (algorithme complet) |
| Critère | {critere} |

## Plages optimisées
{tab}

## Inputs fixes
{fixes_md}
{note_session}{note_ohlc}
---

## Étape A — prompt IN-SAMPLE (copier tout le bloc dans l'assistant IA de MT5)

```
{pA}
```

**Après l'étape A** : dans le dossier `Common\\Files` (voir protocole §3), récupérez le fichier
`PA_M1_opt_{sym_b}_{ut}_<AAAAMMJJ_HHMM>.csv` le plus récent. Ne le renommez pas
(sauf ajout éventuel de `_OHLC`). Copiez-le dans `resultats/module1/`.

---

## Étape B — prompt OUT-OF-SAMPLE (même grille, autres dates)

```
{pB}
```

**Après l'étape B** : récupérez le nouveau `PA_M1_opt_{sym_b}_{ut}_<AAAAMMJJ_HHMM>.csv`
(horodatage plus récent que celui de l'étape A) et copiez-le aussi dans `resultats/module1/`.
L'analyse distingue in-sample et forward grâce aux colonnes `from`/`to` du CSV.

> Important : on ne choisit **jamais** un réglage en regardant l'étape B. L'étape B sert
> uniquement à vérifier que le plateau trouvé en A reste positif.

## À renvoyer
- [ ] CSV de l'étape A (`PA_M1_opt_{sym_b}_{ut}_....csv`, période {isd}–{isf})
- [ ] CSV de l'étape B (`PA_M1_opt_{sym_b}_{ut}_....csv`, période {ood}–{oof})
- [ ] (optionnel) capture de l'onglet « Optimization results » ou export XML/HTML
- [ ] Toute erreur ou anomalie du Journal (onglet « Journal » du testeur)
""".format(num=num, sym=sym, ut=ut, lib=lib, it=ITERATION, ea=EA_NOM, sym_b=sym_b, ev=ev,
           isd=IS_DEBUT, isf=IS_FIN, ood=OOS_DEBUT, oof=OOS_FIN, modele=modele_ticks(ut),
           np=nb_passes(plages), critere=CRITERE, tab=bloc_plages(plages),
           fixes_md="\n".join("- `%s` = %s" % (k, v) for k, v in fixes.items()),
           note_session=note_session, note_ohlc=note_ohlc, pA=pA, pB=pB)


def generer_modele_controle(num):
    a, s, b = GRAINES
    return """# {num:02d} — MODÈLE : contrôle aléatoire (une fois par symbole × UT × événement retenu)

À lancer **après** la première analyse, uniquement pour les combinaisons classées
« EDGE PROBABLE » ou « À CONFIRMER » dans `resultats/module1/rapport/RAPPORT_MODULE1.md`.
Le rapport indique le réglage à utiliser (LeftBars, RightBars, BreakMode).

Remplacez les `<...>` puis collez le bloc dans l'assistant IA de MT5 :

```
Configure et lance une optimisation dans le Testeur de stratégie MT5 :
- Expert : {ea}
- Symbole : <SYMBOLE_BROKER>
- Période (timeframe) : <UT>
- Dates : du {isd} au {isf} (in-sample), Forward : No
- Modèle : « Every tick based on real ticks » (ou « 1 minute OHLC » si c'est celui utilisé pour la grille)
- Dépôt initial : {depot}, levier {levier}, délai : {delai}
- Optimisation : « Slow complete algorithm », critère : {critere}
- Inputs à optimiser : InpRandomSeed : Start={a}, Step={s}, Stop={b}
- Inputs fixes : InpRandomMode = true ; InpLeftBars = <L> ; InpRightBars = <R> ;
  InpBreakMode = <B> ; InpTradeEvents = <E> ; tous les autres inputs identiques à la grille
  (InpRR=3.0, InpSLBufferATR=0.1, InpATRPeriod=14, InpMinRiskATR=0.2, InpMaxRiskATR=5.0,
  InpMaxBarsInTrade=0, InpOnePosition=true, InpMinTradesForScore=100, session identique)
Lance l'optimisation et préviens-moi quand elle est terminée.
```

Optionnel (recommandé si le temps le permet) : refaire le même contrôle sur la période
forward {ood} → {oof}.

**Après** : copiez le `PA_M1_opt_<SYMBOLE>_<UT>_<AAAAMMJJ_HHMM>.csv` produit dans
`resultats/module1/`. Les lignes ont `random_mode=1` : l'analyse les reconnaît seule.
""".format(num=num, ea=EA_NOM, isd=IS_DEBUT, isf=IS_FIN, ood=OOS_DEBUT, oof=OOS_FIN,
           depot=DEPOT, levier=LEVIER, delai=DELAI, critere=CRITERE, a=a, s=s, b=b)


def generer_modele_trades(num):
    return """# {num:02d} — MODÈLE : run simple « trades » sur le meilleur réglage

À lancer pour chaque combinaison retenue par le rapport (même réglage que le contrôle
aléatoire). Ce run produit le journal des trades, indispensable pour l'IC bootstrap, le
Monte-Carlo du drawdown et l'analyse des MFE (choix du RR).

```
Configure et lance un test simple (PAS d'optimisation) dans le Testeur de stratégie MT5 :
- Expert : {ea}
- Symbole : <SYMBOLE_BROKER>
- Période (timeframe) : <UT>
- Dates : du {isd} au {oof} (période complète in-sample + forward), Forward : No
- Modèle : « Every tick based on real ticks »
- Dépôt initial : {depot}, levier {levier}, délai : {delai}
- Visualisation : désactivée
- Inputs : InpLeftBars = <L> ; InpRightBars = <R> ; InpBreakMode = <B> ;
  InpTradeEvents = <E> ; InpRandomMode = false ; InpRR=3.0 ; InpSLBufferATR=0.1 ;
  InpATRPeriod=14 ; InpMinRiskATR=0.2 ; InpMaxRiskATR=5.0 ; InpMaxBarsInTrade=0 ;
  InpOnePosition=true ; InpMinTradesForScore=100 ; session identique à la grille
Lance le test et préviens-moi quand il est terminé.
```

**Après** : dans `Common\\Files`, récupérez
`PA_M1_trades_<SYMBOLE>_<UT>_L<L>_R<R>_B<B>_E<E>.csv` (et le `PA_M1_opt_...csv` d'une ligne
produit en même temps). Copiez les deux dans `resultats/module1/`. Optionnel : clic droit sur
l'onglet « Backtest » → « Report » → enregistrer le rapport HTML à côté.

L'analyse coupe elle-même les trades en in-sample / forward à la date {ood}.
""".format(num=num, ea=EA_NOM, isd=IS_DEBUT, oof=OOS_FIN, ood=OOS_DEBUT,
           depot=DEPOT, levier=LEVIER, delai=DELAI)


def main():
    os.makedirs(DOSSIER_SORTIE, exist_ok=True)
    if COMBINAISONS is None:
        combis = [(s, u, e) for s in ORDRE_SYMBOLES for u in ORDRE_UT for e in EVENEMENTS]
    else:
        combis = list(COMBINAISONS)

    lignes_index = []
    num = 0
    for (sym, ut, ev) in combis:
        num += 1
        nom = nom_fichier(num, sym, ut, ev)
        with open(os.path.join(DOSSIER_SORTIE, nom), "w", encoding="utf-8") as f:
            f.write(generer_fichier(num, sym, ut, ev))
        modele = "real ticks / 1m OHLC" if ut in UT_OHLC_AUTORISE else "real ticks"
        lignes_index.append("| [ ] | %02d | [%s](%s) | %s | %s | %s (E=%d) | %d | %s |"
                            % (num, nom, nom, sym, ut, EVENEMENTS[ev], ev,
                               nb_passes(plages_pour(sym, ut, ev)), modele))

    n_ctrl = num + 1
    n_tr = num + 2
    f_ctrl = "%02d_MODELE_CONTROLE_ALEATOIRE.md" % n_ctrl
    f_tr = "%02d_MODELE_RUN_TRADES.md" % n_tr
    with open(os.path.join(DOSSIER_SORTIE, f_ctrl), "w", encoding="utf-8") as f:
        f.write(generer_modele_controle(n_ctrl))
    with open(os.path.join(DOSSIER_SORTIE, f_tr), "w", encoding="utf-8") as f:
        f.write(generer_modele_trades(n_tr))

    index = """# Index des backtests — Module 1, itération {it}

Fichiers générés par `module1/generer_prompts.py` (ne pas éditer à la main : modifier le
script et relancer). Protocole complet : `module1/PROTOCOLE_BACKTEST.md`.

**Ordre recommandé** : suivre les numéros. Les lignes 01 à 04 (XAUUSD H1 puis M15) servent à
valider toute la chaîne (EA → CSV → analyse). Après le 04, renvoyez les 4 paires de CSV et
attendez le retour de l'analyse avant de continuer.

Chaque fichier = **2 runs** (A in-sample {isd}→{isf}, B forward {ood}→{oof}) → 2 CSV `PA_M1_opt_...`.

| Fait | N° | Fichier | Symbole | UT | Événement | Passes/run | Modèle de ticks |
|---|---|---|---|---|---|---|---|
{lignes}

## Après la grille (sur les combinaisons retenues par le rapport)
| Fait | N° | Fichier | Rôle |
|---|---|---|---|
| [ ] | {nc:02d} | [{fc}]({fc}) | Contrôle aléatoire (InpRandomMode=true, graines 1–30) |
| [ ] | {nt:02d} | [{ft}]({ft}) | Run simple sur le meilleur réglage → CSV des trades |

## Rappel des dépôts
Tous les CSV vont dans `resultats/module1/` (sans les renommer, sauf ajout de `_OHLC`), puis :
`python3 analyse/analyse_module1.py`
""".format(it=ITERATION, isd=IS_DEBUT, isf=IS_FIN, ood=OOS_DEBUT, oof=OOS_FIN,
           lignes="\n".join(lignes_index), nc=n_ctrl, fc=f_ctrl, nt=n_tr, ft=f_tr)
    with open(os.path.join(DOSSIER_SORTIE, "00_INDEX.md"), "w", encoding="utf-8") as f:
        f.write(index)
    print("%d prompts + 2 modèles + index écrits dans %s" % (num, DOSSIER_SORTIE))


if __name__ == "__main__":
    main()
