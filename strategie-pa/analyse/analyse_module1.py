#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse des résultats du Module 1 (Structure : BOS / CHOCH).

Lit tous les CSV produits par l'EA PA_M1_Structure_EA et déposés dans
resultats/module1/ (sous-dossiers compris, sauf rapport/) :
  - PA_M1_opt_*.csv    : une ligne par passe d'optimisation
  - PA_M1_trades_*.csv : journal des trades d'un test simple

Produit dans resultats/module1/rapport/ :
  - RAPPORT_MODULE1.md           : rapport + verdicts + suggestions itération 2
  - synthese_verdicts.csv        : verdict par symbole x UT x événement
  - classement_<...>.csv         : classement des passes par groupe
  - heatmap_*.png, is_vs_oos_*.png, trades_*.png : graphiques

Usage :
    python3 analyse/analyse_module1.py
    python3 analyse/analyse_module1.py --dossier resultats/module1 --split 2024-07-01

Dépendances : pandas, numpy, matplotlib (optionnel : sans matplotlib, pas de PNG).
Aucun chiffre n'est inventé : tout provient des CSV lus.
"""

import argparse
import io
import math
import os
import re
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    HAS_MPL = True
except Exception:  # pragma: no cover
    HAS_MPL = False

# =============================================================================
# PARAMÈTRES D'ANALYSE (règles de verdict : voir aussi texte_regles())
# =============================================================================
SPLIT_DEFAUT = "2024-07-01"       # début de l'out-of-sample
MIN_TRADES = 100                  # trades mini pour qu'une passe in-sample compte
MIN_TRADES_OOS = 40               # trades mini en forward pour juger l'OOS
T_MIN = 2.0                       # t-stat approx. mini en in-sample
PART_VOISINS_POSITIFS = 0.70      # part mini de voisins à avg_R > 0 (plateau)
COUVERTURE_VOISINAGE = 0.75       # part mini de cellules valides dans le voisinage
P_ALEA_EDGE = 0.05                # p empirique max vs contrôle aléatoire
P_ALEA_REJET = 0.20               # au-delà : pas d'edge
NB_BOOT = 5000
NB_MC = 2000
GRAINE = 12345
TOP_N = 10

ALIAS_SYMBOLES = [
    (r"^(XAUUSD|GOLD|XAU)", "XAUUSD"),
    (r"^(GER40|DE40|GER30|DE30|DAX|GERMANY40|GER|DEU40)", "GER40"),
]
TF_ORDRE = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
TF_ENUM = {"1": "M1", "5": "M5", "15": "M15", "30": "M30", "16385": "H1", "60": "H1",
           "16388": "H4", "240": "H4", "16408": "D1", "1440": "D1", "32769": "W1",
           "49153": "MN1"}
EV_NOM = {0: "BOS", 1: "CHOCH", 2: "BOS+CHOCH"}

COLS_OPT_NUM = ["pass", "left_bars", "right_bars", "break_mode", "trade_events",
                "sl_buffer_atr", "rr", "random_mode", "trades", "wins", "losses",
                "timeouts", "winrate", "avg_r", "sum_r", "profit_factor_r", "max_dd_r",
                "avg_win_r", "avg_loss_r", "max_consec_losses", "net_profit",
                "balance_dd_pct"]
COLS_TR_NUM = ["entry", "sl", "tp", "risk_points", "atr_points", "exit_price", "result_r",
               "mfe_r", "mae_r", "bars_held", "spread_points", "left_bars", "right_bars",
               "break_mode", "trade_events", "random_mode"]

AVERTISSEMENTS = []


def avert(msg):
    AVERTISSEMENTS.append(msg)
    print("ATTENTION : " + msg, file=sys.stderr)


# =============================================================================
# LECTURE ROBUSTE
# =============================================================================
def decoder(octets):
    if octets.startswith(b"\xff\xfe") or octets.startswith(b"\xfe\xff"):
        return octets.decode("utf-16")
    if octets.startswith(b"\xef\xbb\xbf"):
        return octets[3:].decode("utf-8", errors="replace")
    if len(octets) > 1 and octets[1:2] == b"\x00":
        return octets.decode("utf-16-le", errors="replace")
    try:
        return octets.decode("utf-8")
    except UnicodeDecodeError:
        return octets.decode("cp1252", errors="replace")


def lire_csv(chemin):
    try:
        with open(chemin, "rb") as f:
            texte = decoder(f.read())
    except OSError as e:
        avert("lecture impossible %s (%s)" % (chemin, e))
        return None
    texte = texte.replace("\x00", "").strip()
    if not texte:
        avert("fichier vide : %s" % chemin)
        return None
    df = None
    for sep in [";", "\t", ","]:
        try:
            d = pd.read_csv(io.StringIO(texte), sep=sep, dtype=str, skipinitialspace=True,
                            on_bad_lines="skip", engine="python")
        except Exception:
            continue
        if d.shape[1] >= 5:
            df = d
            break
    if df is None:
        avert("format non reconnu (séparateur ?) : %s" % chemin)
        return None
    df.columns = [re.sub(r"[^0-9a-z_]", "", str(c).strip().lower().replace("﻿", ""))
                  for c in df.columns]
    # ligne d'en-tête répétée éventuelle (fichier concaténé)
    premiere = df.columns[0]
    df = df[df[premiere].astype(str).str.strip().str.lower() != premiere]
    return df.reset_index(drop=True)


def en_nombre(s):
    s = s.astype(str).str.strip().str.replace(" ", "", regex=False)
    s = s.str.replace(" ", "", regex=False)
    # virgule décimale : "1,23" -> "1.23" ; "1.234,5" -> "1234.5"
    s = s.where(~s.str.contains(r"\d\.\d{3},", regex=True),
                s.str.replace(".", "", regex=False))
    s = s.str.replace(",", ".", regex=False)
    s = s.replace({"true": "1", "false": "0", "True": "1", "False": "0", "": np.nan,
                   "nan": np.nan, "inf": "inf", "-inf": "-inf"})
    return pd.to_numeric(s, errors="coerce")


def en_date(s):
    s = s.astype(str).str.strip()
    if s.str.fullmatch(r"\d{9,11}").mean() > 0.8:
        return pd.to_datetime(pd.to_numeric(s, errors="coerce"), unit="s", errors="coerce")
    s = s.str.replace(r"^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", r"\1-\2-\3", regex=True)
    try:
        return pd.to_datetime(s, errors="coerce", format="mixed")
    except (TypeError, ValueError):
        return pd.to_datetime(s, errors="coerce")


def norm_symbole(x):
    x = str(x).strip().upper()
    for motif, nom in ALIAS_SYMBOLES:
        if re.match(motif, x):
            return nom
    return x


def norm_tf(x):
    x = str(x).strip().upper().replace("PERIOD_", "")
    if x.endswith(".0"):
        x = x[:-2]
    if x in TF_ENUM:
        return TF_ENUM[x]
    return x


def info_nom_fichier(nom):
    """Extrait symbole/UT/params du nom de fichier en secours."""
    m = re.match(r"PA_M1_(opt|trades)_(.+?)_(M1|M5|M15|M30|H1|H4|D1|W1|MN1)_", nom + "_",
                 re.IGNORECASE)
    d = {}
    if m:
        d["symbol"] = m.group(2)
        d["tf"] = m.group(3).upper()
    for cle, motif in [("left_bars", r"_L(\d+)"), ("right_bars", r"_R(\d+)"),
                       ("break_mode", r"_B(\d+)"), ("trade_events", r"_E(\d+)")]:
        mm = re.search(motif, nom)
        if mm:
            d[cle] = float(mm.group(1))
    return d


def preparer(df, chemin, cols_num):
    nom = os.path.basename(chemin)
    secours = info_nom_fichier(nom)
    for c in cols_num:
        if c in df.columns:
            df[c] = en_nombre(df[c])
        elif c in secours:
            df[c] = secours[c]
        else:
            df[c] = np.nan
    for c in ["symbol", "tf"]:
        if c not in df.columns or df[c].isna().all():
            df[c] = secours.get(c, "INCONNU")
    df["symbol"] = df["symbol"].map(norm_symbole)
    df["tf"] = df["tf"].map(norm_tf)
    df["random_mode"] = df["random_mode"].fillna(0).astype(int)
    df["ohlc"] = bool(re.search(r"OHLC", nom, re.IGNORECASE))
    df["fichier"] = nom
    df["mtime"] = os.path.getmtime(chemin)
    return df


def charger(dossier, rapport_dir):
    opts, trades = [], []
    fichiers = []
    for racine, _, noms in os.walk(dossier):
        if os.path.abspath(racine).startswith(os.path.abspath(rapport_dir)):
            continue
        for n in noms:
            if n.lower().endswith(".csv"):
                fichiers.append(os.path.join(racine, n))
    fichiers.sort()
    lus = []
    for ch in fichiers:
        df = lire_csv(ch)
        if df is None or df.empty:
            continue
        cols = set(df.columns)
        if "result_r" in cols:
            df = preparer(df, ch, COLS_TR_NUM)
            for c in ["open_time", "close_time"]:
                df[c] = en_date(df[c]) if c in df.columns else pd.NaT
            for c in ["exit_reason", "event", "direction"]:
                df[c] = df[c].astype(str).str.strip().str.upper() if c in df.columns else ""
            df = df[df["result_r"].notna()]
            trades.append(df)
            lus.append((os.path.basename(ch), "trades", len(df)))
        elif "avg_r" in cols or ("sum_r" in cols and "trades" in cols):
            df = preparer(df, ch, COLS_OPT_NUM)
            if df["avg_r"].isna().all() and df["sum_r"].notna().any():
                df["avg_r"] = df["sum_r"] / df["trades"].replace(0, np.nan)
            for c in ["from", "to"]:
                df[c + "_dt"] = en_date(df[c]) if c in df.columns else pd.NaT
            manquantes = [c for c in ["left_bars", "right_bars", "break_mode", "trades"]
                          if df[c].isna().all()]
            if manquantes:
                avert("%s : colonnes manquantes %s -> fichier ignoré" % (ch, manquantes))
                continue
            if df["trade_events"].isna().all():
                avert("%s : trade_events absent, supposé 2 (BOS+CHOCH)" % ch)
                df["trade_events"] = 2
            trades_vides = df["trades"].isna()
            df.loc[trades_vides, "trades"] = 0
            opts.append(df)
            lus.append((os.path.basename(ch), "optimisation", len(df)))
        else:
            avert("%s : type de CSV non reconnu (colonnes : %s)" % (ch, ", ".join(df.columns[:8])))
    opt = pd.concat(opts, ignore_index=True) if opts else pd.DataFrame()
    tr = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
    return opt, tr, lus


def phase_ligne(row, split):
    d, f = row.get("from_dt"), row.get("to_dt")
    tol = pd.Timedelta(days=5)
    if pd.notna(f) and f <= split + tol and (pd.isna(d) or d < split):
        return "IS"
    if pd.notna(d) and d >= split - tol:
        return "OOS"
    if pd.notna(d) and pd.notna(f):
        return "COMPLET"
    return "INCONNU"


# =============================================================================
# STATISTIQUES
# =============================================================================
def sigma_approx(r):
    """Écart-type approx. du R par trade à partir des colonnes de synthèse."""
    n = r["trades"]
    if not n or n <= 0:
        return np.nan
    w = r["wins"] / n if pd.notna(r["wins"]) else np.nan
    if pd.isna(w) and pd.notna(r["winrate"]):
        w = r["winrate"] / 100.0 if r["winrate"] > 1 else r["winrate"]
    aw, al = r["avg_win_r"], r["avg_loss_r"]
    if pd.notna(w) and pd.notna(aw) and pd.notna(al):
        m2 = w * aw ** 2 + (1 - w) * al ** 2
        var = m2 - r["avg_r"] ** 2
        if var > 1e-6:
            return math.sqrt(var)
    rr = r["rr"] if pd.notna(r["rr"]) else 3.0
    p = min(max((r["avg_r"] + 1) / (rr + 1), 0.01), 0.99)
    return math.sqrt(p * (1 - p)) * (rr + 1)


def t_approx(r):
    s = sigma_approx(r)
    if pd.isna(s) or s <= 0 or r["trades"] <= 0:
        return np.nan
    return r["avg_r"] * math.sqrt(r["trades"]) / s


def max_dd(r):
    if len(r) == 0:
        return 0.0
    eq = np.concatenate([[0.0], np.cumsum(r)])
    return float(np.max(np.maximum.accumulate(eq) - eq))


def stats_r(r):
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n == 0:
        return dict(n=0, moy=np.nan, wr=np.nan, pf=np.nan, somme=0.0, dd=0.0)
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=n, moy=r.mean(), wr=(r > 0).mean(), pf=(pos / neg) if neg > 0 else np.inf,
                somme=r.sum(), dd=max_dd(r))


def bootstrap(r, rng):
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return np.nan, np.nan, np.nan
    idx = rng.integers(0, len(r), size=(NB_BOOT, len(r)))
    moy = r[idx].mean(axis=1)
    return (float(np.percentile(moy, 2.5)), float(np.percentile(moy, 97.5)),
            float((moy <= 0).mean()))


def mc_dd(r, rng):
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return np.nan, np.nan, np.nan
    dds = np.empty(NB_MC)
    for i in range(NB_MC):
        dds[i] = max_dd(rng.permutation(r))
    return float(np.median(dds)), float(np.percentile(dds, 95)), float(np.percentile(dds, 99))


def esperance_rr(df, k):
    """Espérance estimée si TP = k R (k <= RR testé), à partir des MFE."""
    mfe = df["mfe_r"].values
    res = df["result_r"].values
    out = np.where(mfe >= k, k, np.minimum(res, k))
    return float(np.nanmean(out))


# =============================================================================
# PLATEAUX / HEATMAPS
# =============================================================================
def grille(g, col="avg_r", min_trades=MIN_TRADES):
    """dict break_mode -> DataFrame (index=left, colonnes=right) ; NaN si trades < min."""
    res = {}
    for b, gb in g.groupby("break_mode"):
        gb = gb.copy()
        gb.loc[gb["trades"] < min_trades, col] = np.nan
        piv = gb.pivot_table(index="left_bars", columns="right_bars", values=col, aggfunc="mean")
        res[int(b)] = piv.sort_index().sort_index(axis=1)
    return res


def plateaux(piv):
    """Moyenne de avg_R sur le voisinage ±1 (L, R) de chaque cellule valide."""
    v = piv.values
    nl, nr = v.shape
    moy = np.full(v.shape, np.nan)
    part_pos = np.full(v.shape, np.nan)
    couv = np.full(v.shape, np.nan)
    for i in range(nl):
        for j in range(nr):
            if np.isnan(v[i, j]):
                continue
            bloc = v[max(0, i - 1):i + 2, max(0, j - 1):j + 2]
            valides = bloc[~np.isnan(bloc)]
            moy[i, j] = valides.mean()
            part_pos[i, j] = (valides > 0).mean()
            couv[i, j] = len(valides) / bloc.size
    mk = lambda a: pd.DataFrame(a, index=piv.index, columns=piv.columns)
    return mk(moy), mk(part_pos), mk(couv)


def tracer_heatmaps(grilles, plats, titre, chemin, choix=None):
    if not HAS_MPL or not grilles:
        return None
    modes = sorted(grilles)
    fig, axes = plt.subplots(2, len(modes), figsize=(5.2 * len(modes), 8.4), squeeze=False)
    toutes = np.concatenate([np.ravel(grilles[m].values) for m in modes])
    toutes = toutes[np.isfinite(toutes)]
    lim = max(0.05, float(np.nanmax(np.abs(toutes)))) if len(toutes) else 0.5
    for c, m in enumerate(modes):
        for r, (data, nom) in enumerate([(grilles[m], "avg_R"), (plats[m], "plateau (moy. ±1)")]):
            ax = axes[r][c]
            arr = np.ma.masked_invalid(data.values.astype(float))
            cmap = plt.get_cmap("RdBu").copy()
            cmap.set_bad("#d9d9d9")
            im = ax.imshow(arr, cmap=cmap, vmin=-lim, vmax=lim, origin="lower", aspect="auto")
            ax.set_xticks(range(data.shape[1]))
            ax.set_xticklabels([int(x) for x in data.columns])
            ax.set_yticks(range(data.shape[0]))
            ax.set_yticklabels([int(x) for x in data.index])
            ax.set_xlabel("RightBars")
            ax.set_ylabel("LeftBars")
            ax.set_title("BreakMode=%d (%s) — %s" % (m, "clôture" if m == 0 else "mèche", nom),
                         fontsize=9)
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    val = data.values[i, j]
                    if np.isfinite(val):
                        ax.text(j, i, "%.2f" % val, ha="center", va="center", fontsize=7,
                                color="white" if abs(val) > 0.6 * lim else "black")
            if choix and choix["break_mode"] == m:
                try:
                    i = list(data.index).index(choix["left_bars"])
                    j = list(data.columns).index(choix["right_bars"])
                    ax.add_patch(Rectangle((j - 1.5, i - 1.5), 3, 3, fill=False, lw=2,
                                           ec="#1b9e3a"))
                    ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, lw=2, ec="k"))
                except ValueError:
                    pass
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(titre + "\n(gris = moins de %d trades ; cadre = plateau retenu)" % MIN_TRADES,
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(chemin, dpi=110)
    plt.close(fig)
    return os.path.basename(chemin)


# =============================================================================
# MARKDOWN
# =============================================================================
def fmt(x, nd=3):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—" if (x is None or np.isnan(x)) else ("∞" if x > 0 else "-∞")
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        if float(x).is_integer() and abs(x) < 1e6 and nd == 0:
            return str(int(x))
        return ("%." + str(nd) + "f") % x
    return str(x)


def table_md(df, nd=3):
    if df is None or df.empty:
        return "_(aucune ligne)_\n"
    cols = list(df.columns)
    lignes = ["| " + " | ".join(str(c) for c in cols) + " |",
              "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cel = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cel.append(fmt(float(v), 0 if c in ("L", "R", "B", "trades", "n") else nd))
            else:
                cel.append(str(v))
        lignes.append("| " + " | ".join(cel) + " |")
    return "\n".join(lignes) + "\n"


def texte_regles():
    return """Les verdicts sont calculés pour chaque symbole × UT × type d'événement, sur le
**plateau retenu** en in-sample (IS). Une cellule de grille n'est valide que si elle a
**≥ {mt} trades**. Le « plateau » d'une cellule = moyenne de avg_R sur la cellule et ses
voisines LeftBars ±1 / RightBars ±1 (même BreakMode). On retient la cellule dont le plateau
est le plus élevé (parmi celles dont ≥ {cv:.0%} du voisinage est valide), **jamais le pic isolé**.

Conditions :
- **C0 Échantillon** : au moins une cellule IS avec ≥ {mt} trades.
- **C1 Plateau positif** : plateau > 0, avg_R de la cellule centrale > 0, et ≥ {pp:.0%} des
  cellules voisines valides ont avg_R > 0.
- **C2 Significativité IS** : t-stat approx. ≥ {t:.1f} (avg_R × √trades / σ estimé), **ou**
  borne basse de l'IC 95 % bootstrap > 0 si le CSV des trades de ce réglage est fourni.
- **C3 Forward (OOS)** : même réglage sur la période forward avec ≥ {mo} trades et avg_R > 0
  (lu dans le CSV d'optimisation forward, à défaut dans la partie OOS du CSV de trades).
- **C4 Contrôle aléatoire** : avg_R réel supérieur à au moins 95 % des runs aléatoires
  (p empirique ≤ {pa}) ; si moins de 5 runs aléatoires : z ≥ 1,96.

Verdict :
- **EDGE PROBABLE** : C0, C1, C2, C3 et C4 tous vrais (et grille testée en real ticks).
- **PAS D'EDGE** : C0 faux (échantillon insuffisant), ou C1 faux, ou C3 évalué et faux
  (OOS ≥ {mo} trades avec avg_R ≤ 0), ou C4 évalué avec p > {pr}.
- **À CONFIRMER** : tous les autres cas (C1 vrai mais C2, C3 ou C4 manquant ou non atteint
  sans être réfuté ; ou grille en « 1 minute OHLC » à reconfirmer en real ticks).

Le verdict symbole × UT = meilleur verdict entre BOS et CHOCH (détail affiché).
""".format(mt=MIN_TRADES, cv=COUVERTURE_VOISINAGE, pp=PART_VOISINS_POSITIFS, t=T_MIN,
           mo=MIN_TRADES_OOS, pa=P_ALEA_EDGE, pr=P_ALEA_REJET)


# =============================================================================
# ANALYSE D'UN GROUPE (symbole x UT x événement x config)
# =============================================================================
def cle_params(r):
    return (int(r["left_bars"]), int(r["right_bars"]), int(r["break_mode"]))


def analyser_groupe(cle, g_is, g_oos, g_rand, trades_df, out_dir, rng):
    sym, tf, ev, rr, slb = cle
    tag = "%s_%s_%s" % (sym, tf, EV_NOM.get(ev, "E%d" % ev))
    if (pd.notna(rr) and abs(rr - 3.0) > 1e-9) or (pd.notna(slb) and abs(slb - 0.1) > 1e-9):
        tag += "_RR%s_SL%s" % (fmt(rr, 2), fmt(slb, 2))
    res = dict(symbole=sym, ut=tf, evenement=EV_NOM.get(ev, str(ev)), rr=rr, sl_buffer=slb,
               tag=tag, n_passes_is=len(g_is), n_passes_oos=len(g_oos),
               ohlc=bool(g_is["ohlc"].any()), md=[], suggestion=None)
    md = res["md"]
    md.append("### %s %s — %s (RR=%s, SLBuffer=%s ATR)\n" % (sym, tf, res["evenement"],
                                                             fmt(rr, 2), fmt(slb, 2)))
    if res["ohlc"]:
        md.append("> Grille testée en **1 minute OHLC** : résultats à reconfirmer en real ticks.\n")

    g = g_is.copy()
    g["t_approx"] = g.apply(t_approx, axis=1)
    g["score"] = g["avg_r"] * np.sqrt(g["trades"].clip(lower=0))
    valides = g[g["trades"] >= MIN_TRADES].sort_values("score", ascending=False)
    md.append("Passes in-sample : %d, dont %d avec ≥ %d trades.\n"
              % (len(g), len(valides), MIN_TRADES))

    # classement
    cl = valides.rename(columns={"left_bars": "L", "right_bars": "R", "break_mode": "B",
                                 "avg_r": "avg_R", "profit_factor_r": "PF_R",
                                 "max_dd_r": "DD_R"})
    cols_cl = ["L", "R", "B", "trades", "winrate", "avg_R", "score", "t_approx", "PF_R", "DD_R"]
    cl = cl[[c for c in cols_cl if c in cl.columns]]
    cl.to_csv(os.path.join(out_dir, "classement_%s.csv" % tag), sep=";", index=False)

    c0 = len(valides) > 0
    res.update(C0=c0, C1=False, C2=None, C3=None, C4=None)
    if not c0:
        md.append("**Aucune passe avec ≥ %d trades : échantillon insuffisant.** "
                  "Max trades observé : %s.\n" % (MIN_TRADES, fmt(g["trades"].max(), 0)))
        res["verdict"] = "PAS D'EDGE"
        res["raisons"] = "C0 faux : échantillon insuffisant (< %d trades)" % MIN_TRADES
        return res

    md.append("**Top %d (classement par score = avg_R × √trades)**\n" % TOP_N)
    md.append(table_md(cl.head(TOP_N)))

    # plateaux
    grilles = grille(g)
    plats, parts, couvs = {}, {}, {}
    meilleurs = []
    for b, piv in grilles.items():
        m, p, cv = plateaux(piv)
        plats[b], parts[b], couvs[b] = m, p, cv
        for L in m.index:
            for R in m.columns:
                val = m.loc[L, R]
                if np.isfinite(val) and cv.loc[L, R] >= COUVERTURE_VOISINAGE:
                    meilleurs.append((val, piv.loc[L, R], int(L), int(R), b, p.loc[L, R]))
    if not meilleurs:  # aucun voisinage assez couvert : on prend la meilleure moyenne
        for b, m in plats.items():
            for L in m.index:
                for R in m.columns:
                    if np.isfinite(m.loc[L, R]):
                        meilleurs.append((m.loc[L, R], grilles[b].loc[L, R], int(L), int(R), b,
                                          parts[b].loc[L, R]))
        avert("%s : aucun voisinage couvert à %.0f %% ; plateau choisi sur couverture partielle"
              % (tag, COUVERTURE_VOISINAGE * 100))
    meilleurs.sort(key=lambda x: (x[0], x[1]), reverse=True)
    pm, centre_avg, L0, R0, B0, ppos = meilleurs[0]
    choix = dict(left_bars=L0, right_bars=R0, break_mode=B0)
    ligne_c = g[(g["left_bars"] == L0) & (g["right_bars"] == R0) & (g["break_mode"] == B0)].iloc[0]
    pic = valides.iloc[0]
    res.update(L=L0, R=R0, B=B0, plateau=pm, avg_is=centre_avg, trades_is=ligne_c["trades"],
               t_is=ligne_c["t_approx"], part_pos=ppos)

    autre_mode = {b: np.nanmax(plats[b].values) if np.isfinite(plats[b].values).any() else np.nan
                  for b in plats}
    md.append("**Plateau retenu** : LeftBars=%d, RightBars=%d, BreakMode=%d → plateau %s R, "
              "cellule %s R, %s trades, t≈%s, voisins positifs %s.\n"
              % (L0, R0, B0, fmt(pm), fmt(centre_avg), fmt(ligne_c["trades"], 0),
                 fmt(ligne_c["t_approx"], 2), "%.0f %%" % (100 * ppos)))
    if cle_params(pic) != (L0, R0, B0):
        pl_pic = plats[int(pic["break_mode"])].loc[pic["left_bars"], pic["right_bars"]]
        md.append("Pic brut (meilleur score) : L=%d R=%d B=%d, avg_R %s, plateau autour %s "
                  "→ %s.\n" % (pic["left_bars"], pic["right_bars"], pic["break_mode"],
                               fmt(pic["avg_r"]), fmt(pl_pic),
                               "pic isolé, écarté" if pic["avg_r"] - pl_pic > 0.1
                               else "proche du plateau"))
    md.append("Meilleur plateau par BreakMode : " + ", ".join(
        "B%d = %s R" % (b, fmt(v)) for b, v in sorted(autre_mode.items())) + "\n")

    img = tracer_heatmaps(grilles, plats, "%s %s %s — in-sample avg_R" % (sym, tf,
                                                                          res["evenement"]),
                          os.path.join(out_dir, "heatmap_IS_%s.png" % tag), choix)
    if img:
        md.append("![heatmap IS](%s)\n" % img)

    c1 = bool(pm > 0 and centre_avg > 0 and ppos >= PART_VOISINS_POSITIFS)
    res["C1"] = c1

    # C2 : significativité
    c2 = bool(np.isfinite(ligne_c["t_approx"]) and ligne_c["t_approx"] >= T_MIN)
    tr_sel = pd.DataFrame()
    if trades_df is not None and not trades_df.empty:
        tr_sel = trades_df[(trades_df["symbol"] == sym) & (trades_df["tf"] == tf) &
                           (trades_df["trade_events"] == ev) & (trades_df["random_mode"] == 0) &
                           (trades_df["left_bars"] == L0) & (trades_df["right_bars"] == R0) &
                           (trades_df["break_mode"] == B0)]
    boot_txt = ""
    if not tr_sel.empty:
        r_is = tr_sel[tr_sel["phase"] == "IS"]["result_r"].values
        lo, hi, _ = bootstrap(r_is, rng)
        res["boot_is"] = (lo, hi)
        boot_txt = " ; IC95 bootstrap IS (CSV trades) [%s ; %s]" % (fmt(lo), fmt(hi))
        if np.isfinite(lo) and lo > 0:
            c2 = True
    res["C2"] = c2

    # C3 : OOS
    md.append("**Forward / out-of-sample**\n")
    c3 = None
    oos_avg, oos_n = np.nan, np.nan
    if not g_oos.empty:
        o = g_oos[(g_oos["left_bars"] == L0) & (g_oos["right_bars"] == R0) &
                  (g_oos["break_mode"] == B0)]
        if not o.empty:
            oos_avg, oos_n = o.iloc[0]["avg_r"], o.iloc[0]["trades"]
        fus = g[["left_bars", "right_bars", "break_mode", "avg_r", "trades"]].merge(
            g_oos[["left_bars", "right_bars", "break_mode", "avg_r", "trades"]],
            on=["left_bars", "right_bars", "break_mode"], suffixes=("_is", "_oos"))
        fus_v = fus[(fus["trades_is"] >= MIN_TRADES) & (fus["trades_oos"] >= MIN_TRADES_OOS)]
        corr = fus_v["avg_r_is"].rank().corr(fus_v["avg_r_oos"].rank()) \
            if len(fus_v) >= 5 else np.nan
        top5 = valides.head(5)[["left_bars", "right_bars", "break_mode", "avg_r", "trades"]].merge(
            g_oos[["left_bars", "right_bars", "break_mode", "avg_r", "trades"]],
            on=["left_bars", "right_bars", "break_mode"], how="left", suffixes=("_IS", "_OOS"))
        top5.columns = ["L", "R", "B", "avg_R IS", "trades IS", "avg_R OOS", "trades OOS"]
        md.append("Top 5 IS revus en OOS :\n")
        md.append(table_md(top5))
        n_pos = (fus_v["avg_r_oos"] > 0).mean() if len(fus_v) else np.nan
        md.append("Corrélation de rang IS↔OOS sur la grille : %s ; part des cellules positives "
                  "en OOS : %s.\n" % (fmt(corr, 2),
                                      "—" if not np.isfinite(n_pos) else "%.0f %%" % (100 * n_pos)))
        if HAS_MPL and len(fus) >= 3:
            fig, ax = plt.subplots(figsize=(5, 4.2))
            ax.axhline(0, color="#888", lw=0.8)
            ax.axvline(0, color="#888", lw=0.8)
            ax.scatter(fus["avg_r_is"], fus["avg_r_oos"], s=14, alpha=0.7, color="#3a6ea5")
            ax.scatter([centre_avg], [oos_avg], s=60, color="#d95f02", label="plateau retenu")
            ax.set_xlabel("avg_R in-sample")
            ax.set_ylabel("avg_R forward")
            ax.set_title("%s %s %s — IS vs OOS" % (sym, tf, res["evenement"]), fontsize=9)
            ax.legend(fontsize=8)
            fig.tight_layout()
            f = "is_vs_oos_%s.png" % tag
            fig.savefig(os.path.join(out_dir, f), dpi=110)
            plt.close(fig)
            md.append("![IS vs OOS](%s)\n" % f)
        img = tracer_heatmaps(grille(g_oos, min_trades=MIN_TRADES_OOS),
                              {b: plateaux(p)[0] for b, p in
                               grille(g_oos, min_trades=MIN_TRADES_OOS).items()},
                              "%s %s %s — forward avg_R (≥%d trades)" % (sym, tf, res["evenement"],
                                                                         MIN_TRADES_OOS),
                              os.path.join(out_dir, "heatmap_OOS_%s.png" % tag), choix)
        if img:
            md.append("![heatmap OOS](%s)\n" % img)
    elif not tr_sel.empty and (tr_sel["phase"] == "OOS").any():
        r_o = tr_sel[tr_sel["phase"] == "OOS"]["result_r"].values
        oos_avg, oos_n = float(np.mean(r_o)), len(r_o)
        md.append("(OOS tiré du CSV de trades, pas de grille forward.)\n")
    if np.isfinite(oos_n):
        md.append("Réglage retenu en OOS : avg_R %s sur %s trades.\n" % (fmt(oos_avg), fmt(oos_n, 0)))
        if oos_n >= MIN_TRADES_OOS:
            c3 = bool(oos_avg > 0)
        else:
            md.append("OOS < %d trades : non concluant.\n" % MIN_TRADES_OOS)
    else:
        md.append("_Pas de données forward pour ce réglage._\n")
    res.update(C3=c3, avg_oos=oos_avg, trades_oos=oos_n)

    # C4 : contrôle aléatoire
    md.append("**Contrôle aléatoire**\n")
    c4, p_alea = None, np.nan
    if g_rand is not None and not g_rand.empty:
        gr = g_rand[g_rand["phase"] == "IS"]
        if gr.empty:
            gr = g_rand
        meme = gr[(gr["left_bars"] == L0) & (gr["right_bars"] == R0) & (gr["break_mode"] == B0)]
        base = meme if len(meme) >= 1 else gr
        vals = base["avg_r"].dropna().values
        if len(vals) >= 5:
            p_alea = (np.sum(vals >= centre_avg) + 1) / (len(vals) + 1)
            c4 = bool(p_alea <= P_ALEA_EDGE)
            md.append("%d runs aléatoires (%s) : avg_R moyen %s, P95 %s ; réel %s → p empirique "
                      "%s.\n" % (len(vals), "même réglage" if len(meme) else "réglages mélangés",
                                 fmt(vals.mean()), fmt(np.percentile(vals, 95)),
                                 fmt(centre_avg), fmt(p_alea, 3)))
        elif len(vals) >= 1:
            rows = base.dropna(subset=["avg_r"])
            se_r = np.sqrt(np.mean([sigma_approx(x) ** 2 / max(x["trades"], 1)
                                    for _, x in rows.iterrows()]) / len(rows))
            se_c = sigma_approx(ligne_c) / math.sqrt(ligne_c["trades"])
            z = (centre_avg - vals.mean()) / math.sqrt(se_r ** 2 + se_c ** 2)
            p_alea = 0.5 * math.erfc(z / math.sqrt(2))
            c4 = bool(z >= 1.96)
            md.append("%d run(s) aléatoire(s) : avg_R %s ; réel %s → z = %s (p≈%s). "
                      "Peu de graines : lancer 30 graines pour conclure.\n"
                      % (len(vals), fmt(vals.mean()), fmt(centre_avg), fmt(z, 2), fmt(p_alea, 3)))
    else:
        md.append("_Pas de contrôle aléatoire fourni (prompt modèle CONTROLE_ALEATOIRE)._\n")
    res.update(C4=c4, p_alea=p_alea)

    # verdict
    raisons = []
    if not c1:
        raisons.append("C1 faux (plateau %s, cellule %s, voisins + %.0f %%)"
                       % (fmt(pm), fmt(centre_avg), 100 * ppos))
    if not c2:
        raisons.append("C2 non atteint (t≈%s%s)" % (fmt(ligne_c["t_approx"], 2), boot_txt))
    if c3 is None:
        raisons.append("C3 manquant (forward)")
    elif not c3:
        raisons.append("C3 faux (OOS avg_R %s sur %s trades)" % (fmt(oos_avg), fmt(oos_n, 0)))
    if c4 is None:
        raisons.append("C4 manquant (contrôle aléatoire)")
    elif not c4:
        raisons.append("C4 non atteint (p=%s)" % fmt(p_alea, 3))
    if not c1 or c3 is False or (c4 is False and np.isfinite(p_alea) and p_alea > P_ALEA_REJET):
        verdict = "PAS D'EDGE"
    elif c1 and c2 and c3 and c4 and not res["ohlc"]:
        verdict = "EDGE PROBABLE"
    else:
        verdict = "À CONFIRMER"
        if c1 and c2 and c3 and c4 and res["ohlc"]:
            raisons.append("grille en 1 minute OHLC")
    res["verdict"] = verdict
    res["raisons"] = "; ".join(raisons) if raisons else "toutes conditions remplies"
    md.append("**Verdict : %s** — %s\n" % (verdict, res["raisons"]))

    # suggestion itération 2
    if c1:
        Ls = sorted(set(g["left_bars"].dropna().astype(int)))
        Rs = sorted(set(g["right_bars"].dropna().astype(int)))
        def plage(c, vals):
            lo, hi = c - 2, c + 2
            if c == min(vals):
                lo = c - 3
            if c == max(vals):
                hi = c + 3
            return (max(1, lo), 1, max(max(1, lo), hi))
        autres = {b: v for b, v in autre_mode.items() if b != B0}
        fixer_b = all((not np.isfinite(v)) or v < pm - 0.05 for v in autres.values())
        res["suggestion"] = dict(InpLeftBars=plage(L0, Ls), InpRightBars=plage(R0, Rs),
                                 InpBreakMode=(B0, 1, B0) if fixer_b else (0, 1, 1))
    return res


# =============================================================================
# ANALYSE DES CSV DE TRADES
# =============================================================================
def analyser_trades(tr, out_dir, rng, split):
    md = []
    rr_info = {}
    if tr.empty:
        md.append("_Aucun CSV de trades fourni (prompt modèle RUN_TRADES)._\n")
        return md, rr_info
    cle = ["symbol", "tf", "left_bars", "right_bars", "break_mode", "trade_events", "random_mode"]
    tr = tr.sort_values("mtime")
    for k, g in tr.groupby(cle, dropna=False):
        # garder uniquement le fichier le plus récent pour une même clé
        dernier = g["fichier"].iloc[-1]
        g = g[g["fichier"] == dernier].sort_values("open_time")
        sym, tf, L, R, B, E, rnd = k
        rr_teste = np.nanmax(np.abs((g["tp"] - g["entry"]) / (g["entry"] - g["sl"])
                                    .replace(0, np.nan))) if g["tp"].notna().any() else np.nan
        if not np.isfinite(rr_teste) or rr_teste > 20:
            rr_teste = np.nanmax(g["mfe_r"].clip(upper=20)) if g["mfe_r"].notna().any() else 3.0
        rr_teste = round(float(rr_teste) * 4) / 4
        tag = "%s_%s_L%s_R%s_B%s_E%s%s" % (sym, tf, fmt(L, 0), fmt(R, 0), fmt(B, 0), fmt(E, 0),
                                          "_ALEA" if rnd else "")
        md.append("### Trades %s %s L=%s R=%s B=%s %s%s (fichier `%s`)\n"
                  % (sym, tf, fmt(L, 0), fmt(R, 0), fmt(B, 0),
                     EV_NOM.get(int(E), "?") if np.isfinite(E) else "?",
                     " — CONTRÔLE ALÉATOIRE" if rnd else "", dernier))
        lignes = []
        for ph, sub in [("IS", g[g["phase"] == "IS"]), ("OOS", g[g["phase"] == "OOS"]), ("TOTAL", g)]:
            r = sub["result_r"].values
            s = stats_r(r)
            lo, hi, pneg = bootstrap(r, rng)
            dmed, d95, d99 = mc_dd(r, rng)
            lignes.append({"phase": ph, "n": s["n"], "espérance R": s["moy"], "IC95 bas": lo,
                           "IC95 haut": hi, "P(moy≤0)": pneg, "winrate": s["wr"], "PF": s["pf"],
                           "somme R": s["somme"], "DD hist R": s["dd"], "DD MC méd": dmed,
                           "DD MC P95": d95, "DD MC P99": d99})
        md.append(table_md(pd.DataFrame(lignes), nd=2))
        if g["exit_reason"].astype(bool).any():
            rep = g["exit_reason"].value_counts(normalize=True)
            md.append("Sorties : " + ", ".join("%s %.0f %%" % (i, 100 * v) for i, v in rep.items())
                      + "\n")
        if g["mfe_r"].notna().any():
            gi = g[g["phase"] == "IS"] if (g["phase"] == "IS").sum() >= 30 else g
            seuils = [1, 2, 3] + ([rr_teste] if rr_teste not in (1, 2, 3) else [])
            md.append("MFE (part des trades atteignant x R, base %s) : " %
                      ("IS" if gi is not g else "totale") +
                      ", ".join("%gR %.0f %%" % (x, 100 * (gi["mfe_r"] >= x).mean())
                                for x in seuils) + "\n")
            ks = [k for k in np.arange(0.5, rr_teste + 1e-9, 0.25)]
            esp = [esperance_rr(gi, k) for k in ks]
            if ks:
                ib = int(np.nanargmax(esp))
                rr_info[(sym, tf, L, R, B, E, rnd)] = (ks[ib], esp[ib], rr_teste)
                md.append("Espérance estimée selon le TP (calculée sur les MFE ; valable seulement "
                          "pour TP ≤ RR testé = %g) :\n" % rr_teste)
                md.append(table_md(pd.DataFrame({"TP (R)": ks, "espérance R": esp}).iloc[::2]
                                   if len(ks) > 8 else pd.DataFrame({"TP (R)": ks,
                                                                     "espérance R": esp}), nd=3))
                note = (" (= RR testé : la vraie optimale peut être plus haute, tester un RR "
                        "supérieur)" if abs(ks[ib] - rr_teste) < 1e-9 else "")
                md.append("→ TP estimé optimal : **%g R** (espérance %s R)%s.\n"
                          % (ks[ib], fmt(esp[ib]), note))
            if HAS_MPL:
                fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
                eq = np.cumsum(g["result_r"].values)
                axes[0].plot(range(1, len(eq) + 1), eq, color="#3a6ea5", lw=1.2)
                n_is = int((g["phase"] == "IS").sum())
                if 0 < n_is < len(eq):
                    axes[0].axvline(n_is + 0.5, color="#d95f02", ls="--", lw=1,
                                    label="début forward")
                    axes[0].legend(fontsize=8)
                axes[0].set_title("Courbe en R cumulés", fontsize=9)
                axes[0].set_xlabel("trade n°")
                axes[1].hist(g["mfe_r"].clip(upper=max(rr_teste, 3) + 0.5).dropna(), bins=30,
                             color="#7a9cc6", edgecolor="white")
                for x in [1, 2, 3]:
                    axes[1].axvline(x, color="#555", ls=":", lw=0.8)
                axes[1].set_title("Distribution des MFE (R)", fontsize=9)
                axes[2].plot(ks, esp, marker="o", color="#1b9e3a", ms=3)
                axes[2].axhline(0, color="#888", lw=0.8)
                axes[2].set_title("Espérance estimée vs TP (R)", fontsize=9)
                axes[2].set_xlabel("TP (R)")
                fig.suptitle(tag, fontsize=10)
                fig.tight_layout()
                f = "trades_%s.png" % tag
                fig.savefig(os.path.join(out_dir, f), dpi=110)
                plt.close(fig)
                md.append("![trades](%s)\n" % f)
    return md, rr_info


# =============================================================================
# PROGRAMME PRINCIPAL
# =============================================================================
def main():
    ici = os.path.dirname(os.path.abspath(__file__))
    racine = os.path.dirname(ici)
    ap = argparse.ArgumentParser(description="Analyse des CSV du Module 1")
    ap.add_argument("--dossier", default=os.path.join(racine, "resultats", "module1"))
    ap.add_argument("--sortie", default=None, help="défaut : <dossier>/rapport")
    ap.add_argument("--split", default=SPLIT_DEFAUT, help="début de l'OOS (AAAA-MM-JJ)")
    args = ap.parse_args()
    dossier = os.path.abspath(args.dossier)
    out_dir = os.path.abspath(args.sortie or os.path.join(dossier, "rapport"))
    split = pd.Timestamp(args.split)
    rng = np.random.default_rng(GRAINE)

    if not os.path.isdir(dossier):
        print("Dossier introuvable : %s" % dossier)
        sys.exit(1)
    os.makedirs(out_dir, exist_ok=True)
    if not HAS_MPL:
        avert("matplotlib absent : pas de graphiques (pip install matplotlib)")

    opt, tr, lus = charger(dossier, out_dir)
    print("%d fichier(s) CSV lu(s)" % len(lus))

    if not opt.empty:
        opt["phase"] = opt.apply(lambda r: phase_ligne(r, split), axis=1)
        if (opt["phase"] == "INCONNU").any():
            avert("%d ligne(s) d'optimisation sans dates from/to : traitées comme in-sample"
                  % (opt["phase"] == "INCONNU").sum())
            opt.loc[opt["phase"] == "INCONNU", "phase"] = "IS"
        if (opt["phase"] == "COMPLET").any():
            avert("%d ligne(s) couvrent IS+OOS (période complète) : non utilisées pour la grille"
                  % (opt["phase"] == "COMPLET").sum())
        opt = opt.dropna(subset=["avg_r"])
        opt = opt.sort_values(["mtime", "fichier"])
        reel = opt[opt["random_mode"] == 0]
        cle_d = ["symbol", "tf", "phase", "left_bars", "right_bars", "break_mode",
                 "trade_events", "sl_buffer_atr", "rr", "ohlc"]
        n0 = len(reel)
        reel = reel.drop_duplicates(subset=cle_d, keep="last")
        if len(reel) < n0:
            print("%d doublon(s) de passes écartés (fichier le plus récent conservé)" % (n0 - len(reel)))
        alea = opt[opt["random_mode"] == 1].drop_duplicates(subset=["fichier", "pass"] + cle_d)
    else:
        reel = alea = pd.DataFrame()

    if not tr.empty:
        tr["phase"] = np.where(tr["open_time"] >= split, "OOS", "IS")

    resultats = []
    sections = []
    if not reel.empty:
        reel_ = reel[reel["phase"].isin(["IS", "OOS"])].copy()
        reel_["rr_k"] = reel_["rr"].round(4).fillna(-1)
        reel_["sl_k"] = reel_["sl_buffer_atr"].round(4).fillna(-1)
        alea = alea.copy()
        if not alea.empty:
            alea["rr_k"] = alea["rr"].round(4).fillna(-1)
            alea["sl_k"] = alea["sl_buffer_atr"].round(4).fillna(-1)
        groupes = reel_.groupby(["symbol", "tf", "trade_events", "rr_k", "sl_k"])
        ordre = sorted(groupes.groups.keys(),
                       key=lambda k: (k[0], TF_ORDRE.index(k[1]) if k[1] in TF_ORDRE else 99,
                                      k[2], k[3], k[4]))
        for k in ordre:
            g = groupes.get_group(k)
            g_is, g_oos = g[g["phase"] == "IS"], g[g["phase"] == "OOS"]
            if g_is.empty:
                avert("%s %s E=%d : forward sans in-sample, ignoré" % (k[0], k[1], k[2]))
                continue
            g_rand = pd.DataFrame()
            if not alea.empty:
                g_rand = alea[(alea["symbol"] == k[0]) & (alea["tf"] == k[1]) &
                              (alea["trade_events"] == k[2]) & (alea["rr_k"] == k[3]) &
                              (alea["sl_k"] == k[4])]
            cle = (k[0], k[1], int(k[2]), k[3] if k[3] != -1 else np.nan,
                   k[4] if k[4] != -1 else np.nan)
            r = analyser_groupe(cle, g_is, g_oos, g_rand, tr, out_dir, rng)
            resultats.append(r)
            sections.extend(r["md"])

    md_trades, rr_info = analyser_trades(tr, out_dir, rng, split) if not tr.empty else \
        (["_Aucun CSV de trades fourni (prompt modèle RUN_TRADES)._\n"], {})

    # ------------------------------------------------------------------ synthèse
    rang = {"EDGE PROBABLE": 0, "À CONFIRMER": 1, "PAS D'EDGE": 2}
    synth = pd.DataFrame([{k: v for k, v in r.items() if k not in ("md", "suggestion")}
                          for r in resultats])
    if not synth.empty:
        synth.drop(columns=["tag"], errors="ignore").to_csv(
            os.path.join(out_dir, "synthese_verdicts.csv"), sep=";", index=False)

    L = []
    L.append("# Rapport Module 1 — Structure (BOS / CHOCH)\n")
    L.append("Généré le %s par `analyse/analyse_module1.py` à partir de **%d fichier(s) CSV** "
             "dans `%s`. Début du forward : %s. Tous les chiffres proviennent des CSV de l'EA "
             "(coûts du testeur inclus) ; rien n'est extrapolé.\n"
             % (datetime.now().strftime("%Y-%m-%d %H:%M"), len(lus),
                os.path.relpath(dossier, racine) if dossier.startswith(racine) else dossier,
                split.date()))
    L.append("## 1. Verdict par symbole × UT\n")
    if synth.empty:
        L.append("_Aucun CSV d'optimisation exploitable : pas de verdict possible._\n")
    else:
        lignes = []
        for (s, u), gg in synth.groupby(["symbole", "ut"], sort=False):
            gg = gg.assign(_r=gg["verdict"].map(rang)).sort_values("_r")
            best = gg.iloc[0]
            det = " / ".join("%s : %s%s" % (x["evenement"], x["verdict"],
                                            "" if pd.isna(x.get("L", np.nan)) else
                                            " (L%d R%d B%d)" % (x["L"], x["R"], x["B"]))
                             for _, x in gg.iterrows())
            lignes.append({"Symbole": s, "UT": u, "Verdict": "**%s**" % best["verdict"],
                           "Détail": det,
                           "avg_R IS": best.get("avg_is", np.nan),
                           "trades IS": best.get("trades_is", np.nan),
                           "avg_R OOS": best.get("avg_oos", np.nan),
                           "p aléa": best.get("p_alea", np.nan)})
        tab = pd.DataFrame(lignes)
        tab["_o"] = tab["UT"].map(lambda u: TF_ORDRE.index(u) if u in TF_ORDRE else 99)
        tab = tab.sort_values(["Symbole", "_o"]).drop(columns="_o")
        L.append(table_md(tab.rename(columns={"trades IS": "trades"})))
        L.append("\nDétail des conditions : `synthese_verdicts.csv`.\n")
    L.append("## 2. Règles de verdict (appliquées automatiquement)\n")
    L.append(texte_regles())
    L.append("## 3. Fichiers lus et avertissements\n")
    L.append(table_md(pd.DataFrame(lus, columns=["fichier", "type", "lignes"])) if lus
             else "_Aucun fichier CSV trouvé._\n")
    if AVERTISSEMENTS:
        L.append("\n" + "\n".join("- " + a for a in AVERTISSEMENTS) + "\n")
    L.append("## 4. Détail par symbole × UT × événement\n")
    L.extend(sections if sections else ["_Rien à analyser._\n"])
    L.append("## 5. Analyse des journaux de trades\n")
    L.extend(md_trades)

    # ------------------------------------------------------------------ itération 2
    L.append("## 6. Suggestions pour l'itération 2\n")
    sugg = [r for r in resultats if r.get("suggestion")]
    if not sugg:
        L.append("Aucune combinaison avec un plateau positif : rien à resserrer. "
                 "Si C0 était faux (échantillon insuffisant), envisager une période plus longue "
                 "ou InpTradeEvents=2.\n")
    else:
        lignes, bloc, combis = [], [], []
        for r in sugg:
            s = r["suggestion"]
            ev = [k for k, v in EV_NOM.items() if v == r["evenement"]][0]
            rrk = None
            for (sym, tf, Lb, Rb, Bb, Eb, rnd), (kopt, esp, rrt) in rr_info.items():
                if (sym, tf, Lb, Rb, Bb, Eb, rnd) == (r["symbole"], r["ut"], r["L"], r["R"], r["B"],
                                                     ev, 0):
                    rrk = (kopt, rrt)
            rr_txt = "garder 3.0"
            if rrk:
                rr_txt = ("tester 3.0→5.0 (optimum au bord)" if abs(rrk[0] - rrk[1]) < 1e-9
                          else "tester %g (estimé sur MFE)" % rrk[0])
            lignes.append({"Symbole": r["symbole"], "UT": r["ut"], "Événement": r["evenement"],
                           "Verdict": r["verdict"],
                           "LeftBars": "%d..%d" % (s["InpLeftBars"][0], s["InpLeftBars"][2]),
                           "RightBars": "%d..%d" % (s["InpRightBars"][0], s["InpRightBars"][2]),
                           "BreakMode": "%d..%d" % (s["InpBreakMode"][0], s["InpBreakMode"][2]),
                           "RR": rr_txt})
            bloc.append('    ("%s", "%s", %d): {"InpLeftBars": %s, "InpRightBars": %s, '
                        '"InpBreakMode": %s},' % (r["symbole"], r["ut"], ev, s["InpLeftBars"],
                                                   s["InpRightBars"], s["InpBreakMode"]))
            combis.append('    ("%s", "%s", %d),' % (r["symbole"], r["ut"], ev))
        L.append(table_md(pd.DataFrame(lignes)))
        L.append("\nRègle : plateau retenu ±2 sur LeftBars et RightBars (±3 côté bord de grille "
                 "si le plateau touche le bord) ; BreakMode fixé si l'autre mode a un plateau "
                 "inférieur d'au moins 0,05 R. Les combinaisons « PAS D'EDGE » sont abandonnées. "
                 "Ne pas re-tester sur la période forward pour choisir : elle reste réservée "
                 "à la validation.\n")
        L.append("Bloc à coller dans `module1/generer_prompts.py` (avec `ITERATION = 2`) :\n")
        L.append("```python\nPLAGES_SPECIFIQUES = {\n" + "\n".join(bloc) + "\n}\n"
                 "COMBINAISONS = [\n" + "\n".join(combis) + "\n]\n```\n")
    L.append("## 7. Prochaines étapes\n")
    a_faire = []
    for r in resultats:
        if r["verdict"] != "PAS D'EDGE" and r.get("C1"):
            manq = []
            if r.get("C3") is None:
                manq.append("run forward")
            if r.get("C4") is None:
                manq.append("contrôle aléatoire (L%d R%d B%d)" % (r["L"], r["R"], r["B"]))
            if not r.get("boot_is"):
                manq.append("run simple trades (L%d R%d B%d)" % (r["L"], r["R"], r["B"]))
            if manq:
                a_faire.append("- %s %s %s : %s" % (r["symbole"], r["ut"], r["evenement"],
                                                    ", ".join(manq)))
    L.append("\n".join(a_faire) + "\n" if a_faire else "Rien de manquant pour les combinaisons "
             "retenues.\n")
    L.append("## 8. Réglages retenus par UT\n")
    L.append("Aucun réglage universel : chaque ligne est choisie **uniquement** à partir des "
             "passes in-sample de ce symbole × UT × événement (plateau retenu, §2). Aucun "
             "« meilleur réglage global » toutes UT confondues n'est calculé.\n")
    if synth.empty:
        L.append("_Aucun réglage : pas de CSV d'optimisation exploitable._\n")
    else:
        rows = []
        for r in resultats:
            a_reg = r.get("L") is not None and not pd.isna(r.get("L", np.nan))
            rows.append({"Symbole": r["symbole"], "UT": r["ut"], "Événement": r["evenement"],
                         "LeftBars": int(r["L"]) if a_reg else "—",
                         "RightBars": int(r["R"]) if a_reg else "—",
                         "BreakMode": int(r["B"]) if a_reg else "—",
                         "trades": r.get("trades_is", np.nan),
                         "avg_R IS": r.get("avg_is", np.nan),
                         "avg_R forward": r.get("avg_oos", np.nan),
                         "Verdict": r["verdict"],
                         "_o": TF_ORDRE.index(r["ut"]) if r["ut"] in TF_ORDRE else 99})
        t8 = pd.DataFrame(rows).sort_values(["Symbole", "_o", "Événement"]).drop(columns="_o")
        L.append(table_md(t8))
        t8.to_csv(os.path.join(out_dir, "reglages_retenus_par_ut.csv"), sep=";", index=False)
        L.append("\n(« — » = pas de réglage retenu : échantillon insuffisant. Un réglage "
                 "« PAS D'EDGE » est listé pour mémoire, il n'est pas recommandé.)\n")
    L.append("\n_STOP : validation du trader requise avant l'itération suivante._\n")

    chemin = os.path.join(out_dir, "RAPPORT_MODULE1.md")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("Rapport écrit : %s" % chemin)


if __name__ == "__main__":
    main()
