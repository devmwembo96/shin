//+------------------------------------------------------------------+
//|                                           PA_M1_Structure_EA.mq5 |
//|  Module 1 - EA de test : mesure de la valeur prédictive des       |
//|  BOS / CHOCH (cf. module1/SPEC_MODULE1.md).                       |
//+------------------------------------------------------------------+
//| INPUTS                                                            |
//|  Structure                                                        |
//|   InpLeftBars        : barres à gauche du pivot (>=1)             |
//|   InpRightBars       : barres à droite = délai de confirmation    |
//|   InpBreakMode       : 0 = clôture au-delà, 1 = mèche au-delà     |
//|  Trade                                                            |
//|   InpTradeEvents     : 0 = BOS seulement, 1 = CHOCH seulement,    |
//|                        2 = les deux (BOS initiaux jamais tradés)  |
//|   InpATRPeriod       : période de l'ATR (barre fermée)            |
//|   InpSLBufferATR     : marge du SL au-delà du swing, en ATR       |
//|   InpMinRiskATR      : risque minimum (ATR), sinon SKIP           |
//|   InpMaxRiskATR      : risque maximum (ATR), sinon SKIP           |
//|   InpRR              : TP = entrée +/- RR x risque                |
//|   InpMaxBarsInTrade  : sortie forcée après N barres (0 = off)     |
//|   InpOnePosition     : une seule position à la fois               |
//|   InpLots            : lot fixe (normalisé min/max/step)          |
//|  Session (heure serveur)                                          |
//|   InpUseSession      : active le filtre                           |
//|   InpSessionStart    : "HH:MM" début (inclus)                     |
//|   InpSessionEnd      : "HH:MM" fin (exclue) ; fin<début = nuit    |
//|  Contrôle aléatoire                                               |
//|   InpRandomMode      : direction tirée au hasard (même timing/SL) |
//|   InpRandomSeed      : graine MathSrand                           |
//|  Optimisation                                                     |
//|   InpMinTradesForScore : trades mini pour score != 0 (OnTester)   |
//|  Divers (hors spec, techniques)                                   |
//|   InpMagic           : magic number                               |
//|   InpDeviationPoints : slippage max accepté (points)              |
//|   InpWarmupBars      : barres d'historique pré-chargées dans le   |
//|                        moteur au 1er tick (événements non tradés) |
//|                                                                   |
//| SORTIES (Common\Files, séparateur ';', point décimal '.')         |
//|  - test simple : PA_M1_trades_<SYM>_<TF>_L<l>_R<r>_B<b>_E<e>.csv  |
//|    (+ suffixe _RND<seed> si InpRandomMode=true)                   |
//|  - PA_M1_opt_<SYM>_<TF>_<YYYYMMDD_HHMM>.csv : une ligne par passe |
//|    (optimisation, via frames) ; en test simple une ligne ajoutée  |
//|    en fin de fichier (horodatage = heure simulée de fin de test). |
//|  - OnTester : 0 si trades < InpMinTradesForScore, sinon           |
//|    avg_R * sqrt(trades)  -> « Custom max ».                       |
//+------------------------------------------------------------------+
#property copyright   "strategie-pa"
#property version     "1.00"
#property description "PA Module 1 : test BOS/CHOCH, stats en R, CSV trades + optimisation"

#include <Trade\Trade.mqh>
#include <PA\PA_Structure.mqh>

//--- inputs
input group "Structure"
input int    InpLeftBars          = 3;        // Barres à gauche du pivot
input int    InpRightBars         = 2;        // Barres à droite (confirmation)
input int    InpBreakMode         = 0;        // 0 = clôture, 1 = mèche
input group "Trade"
input int    InpTradeEvents       = 2;        // 0 = BOS, 1 = CHOCH, 2 = les deux
input int    InpATRPeriod         = 14;       // Période ATR
input double InpSLBufferATR       = 0.1;      // Marge SL (x ATR)
input double InpMinRiskATR        = 0.2;      // Risque mini (x ATR)
input double InpMaxRiskATR        = 5.0;      // Risque maxi (x ATR)
input double InpRR                = 3.0;      // Ratio TP / risque
input int    InpMaxBarsInTrade    = 0;        // Sortie forcée après N barres (0 = off)
input bool   InpOnePosition       = true;     // Une position à la fois
input double InpLots              = 0.01;     // Lot fixe
input group "Session (heure serveur)"
input bool   InpUseSession        = false;    // Filtre session
input string InpSessionStart      = "08:00";  // Début HH:MM
input string InpSessionEnd        = "17:30";  // Fin HH:MM
input group "Contrôle aléatoire"
input bool   InpRandomMode        = false;    // Direction aléatoire
input int    InpRandomSeed        = 1;        // Graine
input group "Optimisation"
input int    InpMinTradesForScore = 100;      // Trades mini pour le score
input group "Divers"
input long   InpMagic             = 20261104; // Magic number
input int    InpDeviationPoints   = 20;       // Slippage max (points)
input int    InpWarmupBars        = 500;      // Barres de pré-chauffage

#define PA_FRAME_ID   1001
#define PA_FRAME_SIZE 23

//--- trade suivi par l'EA
struct STradeRec
  {
   ulong             ticket;       // ticket de position
   ulong             posId;        // POSITION_IDENTIFIER
   datetime          openTime;
   int               evtType;      // ENUM_PA_EVENT
   int               dir;          // +1 achat, -1 vente
   double            entry;        // prix réel d'entrée
   double            sl;
   double            tp;
   double            risk;         // |entrée - SL| en prix
   double            riskMoney;    // perte au SL en devise du compte (pour les coûts)
   double            atr;
   double            volume;
   double            spreadPts;
   double            bestPx;       // meilleur prix de sortie atteint (MFE)
   double            worstPx;      // pire prix de sortie atteint (MAE)
   int               barsHeld;
   bool              timeClose;    // fermeture demandée par l'EA (TIME)
  };

//--- statistiques en R
struct SRStats
  {
   int               trades;
   int               wins;
   int               losses;
   int               timeouts;
   int               maxConsec;
   double            winrate;
   double            avgR;
   double            sumR;
   double            pf;
   double            maxDD;
   double            avgWin;
   double            avgLoss;
  };

//--- globaux
CTrade       g_trade;
CPAStructure g_ps;
int          g_atr=INVALID_HANDLE;
STradeRec    g_open[];
int          g_openCount=0;
double       g_R[];
int          g_nR=0;
int          g_timeouts=0;
int          g_skips=0;
int          g_tradeFile=INVALID_HANDLE;
int          g_optFile=INVALID_HANDLE;
string g_optFinalName="";   // nom définitif du CSV d'optimisation
string g_optTmpName="";     // nom provisoire (_EN_COURS) pendant l'optimisation
datetime     g_lastBarTime=0;
datetime     g_lastProcessed=0;
datetime     g_firstTime=0;
datetime     g_lastTime=0;
int          g_sessStart=0;
int          g_sessEnd=0;
bool         g_onePos=true;
bool         g_isOpt=false;
bool         g_finalized=false;
string       g_tf="";

//--- prototypes (fonctions définies plus bas)
void CheckClosedTrades(const bool atEnd);

//+------------------------------------------------------------------+
//| Utilitaires                                                      |
//+------------------------------------------------------------------+
bool ParseHHMM(const string s,int &mins)
  {
   string p[];
   if(StringSplit(s,':',p)!=2)
      return(false);
   int h=(int)StringToInteger(p[0]);
   int m=(int)StringToInteger(p[1]);
   if(h<0 || h>23 || m<0 || m>59)
      return(false);
   mins=h*60+m;
   return(true);
  }

//--- filtre session (heure serveur), fenêtre [début ; fin[
bool InSession(const datetime t)
  {
   if(g_sessStart==g_sessEnd)
      return(true);
   MqlDateTime dt;
   TimeToStruct(t,dt);
   int m=dt.hour*60+dt.min;
   if(g_sessStart<g_sessEnd)
      return(m>=g_sessStart && m<g_sessEnd);
   return(m>=g_sessStart || m<g_sessEnd);   // session qui passe minuit
  }

//--- mode de remplissage autorisé par le symbole
ENUM_ORDER_TYPE_FILLING GetFilling()
  {
   long fm=SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE);
   if((fm&SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
      return(ORDER_FILLING_FOK);
   if((fm&SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
      return(ORDER_FILLING_IOC);
   return(ORDER_FILLING_RETURN);
  }

//--- prix arrondi au tick
double NormPrice(const double p)
  {
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double v=p;
   if(ts>0.0)
      v=MathRound(p/ts)*ts;
   return(NormalizeDouble(v,_Digits));
  }

//--- volume aligné sur min/max/step
double NormVolume(const double lots)
  {
   double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(st<=0.0)
      st=(mn>0.0 ? mn : 0.01);
   double v=MathFloor(lots/st+1e-9)*st;
   if(v<mn)
      v=mn;
   if(mx>0.0 && v>mx)
      v=mx;
   int dg=0;
   while(dg<8 && MathAbs(st*MathPow(10,dg)-MathRound(st*MathPow(10,dg)))>1e-8)
      dg++;
   return(NormalizeDouble(v,dg));
  }

string D(const double v,const int digits)
  {
   return(DoubleToString(v,digits));
  }

string Stamp(const datetime t)
  {
   MqlDateTime dt;
   TimeToStruct(t,dt);
   return(StringFormat("%04d%02d%02d_%02d%02d",dt.year,dt.mon,dt.day,dt.hour,dt.min));
  }

string BoolStr(const string s)
  {
   string v=s;
   StringToLower(v);
   return((v=="true" || v=="1") ? "1" : "0");
  }

string TS(const datetime t)
  {
   return(TimeToString(t,TIME_DATE|TIME_SECONDS));
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   g_isOpt=(MQLInfoInteger(MQL_OPTIMIZATION)!=0);
   g_tf=PA_TFToString(PERIOD_CURRENT);

   if(InpLeftBars<1 || InpRightBars<1 || (InpBreakMode!=0 && InpBreakMode!=1) ||
      InpTradeEvents<0 || InpTradeEvents>2 || InpATRPeriod<1 || InpRR<=0.0 ||
      InpMinRiskATR<0.0 || InpMaxRiskATR<=InpMinRiskATR || InpLots<=0.0)
     {
      Print("PA_M1_Structure_EA : paramètres invalides");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!ParseHHMM(InpSessionStart,g_sessStart) || !ParseHHMM(InpSessionEnd,g_sessEnd))
     {
      Print("PA_M1_Structure_EA : session invalide (format HH:MM)");
      return(INIT_PARAMETERS_INCORRECT);
     }
//--- moteur : on ne garde que ~2000 swings/événements récents (mémoire)
   if(!g_ps.Init(InpLeftBars,InpRightBars,InpBreakMode,2000))
      return(INIT_PARAMETERS_INCORRECT);

   g_atr=iATR(_Symbol,_Period,InpATRPeriod);
   if(g_atr==INVALID_HANDLE)
     {
      PrintFormat("PA_M1_Structure_EA : iATR impossible (err %d)",GetLastError());
      return(INIT_FAILED);
     }

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints((ulong)MathMax(InpDeviationPoints,0));
   g_trade.SetTypeFilling(GetFilling());

//--- compte netting : plusieurs positions impossibles -> une seule
   g_onePos=InpOnePosition;
   if(!g_onePos && AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
     {
      Print("PA_M1_Structure_EA : compte non hedging -> InpOnePosition forcé à true");
      g_onePos=true;
     }

   MathSrand(InpRandomSeed);

//--- remise à zéro des états
   ArrayResize(g_open,0);
   g_openCount=0;
   ArrayResize(g_R,0,1024);
   g_nR=0;
   g_timeouts=0;
   g_skips=0;
   g_lastBarTime=0;
   g_lastProcessed=0;
   g_firstTime=0;
   g_lastTime=0;
   g_finalized=false;

//--- journal des trades : test simple uniquement (pas en optimisation)
   g_tradeFile=INVALID_HANDLE;
   if(!g_isOpt)
     {
      string fn=StringFormat("PA_M1_trades_%s_%s_L%d_R%d_B%d_E%d",
                             _Symbol,g_tf,InpLeftBars,InpRightBars,InpBreakMode,InpTradeEvents);
      if(InpRandomMode)
         fn=fn+"_RND"+IntegerToString(InpRandomSeed);
      fn=fn+".csv";
      g_tradeFile=FileOpen(fn,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,';');
      if(g_tradeFile==INVALID_HANDLE)
         PrintFormat("PA_M1_Structure_EA : impossible d'ouvrir %s (err %d)",fn,GetLastError());
      else
         FileWrite(g_tradeFile,"open_time","close_time","symbol","tf","event","direction",
                   "entry","sl","tp","risk_points","atr_points","exit_price","exit_reason",
                   "result_R","mfe_R","mae_R","bars_held","spread_points","left_bars",
                   "right_bars","break_mode","trade_events","random_mode");
     }
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
//--- test interrompu avant OnTester : on clôt quand même le journal
   if(!g_finalized && MQLInfoInteger(MQL_TESTER)!=0 && g_openCount>0)
      CheckClosedTrades(true);
   if(g_tradeFile!=INVALID_HANDLE)
     {
      FileClose(g_tradeFile);
      g_tradeFile=INVALID_HANDLE;
     }
   if(g_atr!=INVALID_HANDLE)
     {
      IndicatorRelease(g_atr);
      g_atr=INVALID_HANDLE;
     }
  }

//+------------------------------------------------------------------+
//| Pré-chauffage du moteur sur l'historique (événements non tradés) |
//+------------------------------------------------------------------+
bool Warmup()
  {
   int cnt=MathMax(InpWarmupBars,1);
   MqlRates r[];
   ArraySetAsSeries(r,false);
   int n=CopyRates(_Symbol,_Period,1,cnt,r);
   if(n<=0)
      return(false);
   for(int i=0;i<n;i++)
      g_ps.Update(r[i].time,r[i].open,r[i].high,r[i].low,r[i].close);
   g_lastProcessed=r[n-1].time;
   return(true);
  }

//+------------------------------------------------------------------+
//| MFE/MAE : suivi au tick sur le prix de sortie (Bid achat/Ask vente)|
//+------------------------------------------------------------------+
void UpdateExcursions(const MqlTick &tk)
  {
   for(int i=0;i<g_openCount;i++)
     {
      if(g_open[i].dir>0)
        {
         g_open[i].bestPx=MathMax(g_open[i].bestPx,tk.bid);
         g_open[i].worstPx=MathMin(g_open[i].worstPx,tk.bid);
        }
      else
        {
         g_open[i].bestPx=MathMin(g_open[i].bestPx,tk.ask);
         g_open[i].worstPx=MathMax(g_open[i].worstPx,tk.ask);
        }
     }
  }

//+------------------------------------------------------------------+
//| Infos de sortie depuis l'historique des deals de la position     |
//| Retourne true si un deal de sortie existe. costs = commissions + |
//| swaps + frais de tous les deals (entrée et sortie).              |
//+------------------------------------------------------------------+
bool GetExitInfo(const ulong posId,double &px,datetime &t,double &costs,long &dreason)
  {
   px=0.0;
   t=0;
   costs=0.0;
   dreason=-1;
   if(!HistorySelectByPosition(posId))
      return(false);
   int    n=HistoryDealsTotal();
   double vol=0.0,pv=0.0;
   bool   found=false;
   for(int k=0;k<n;k++)
     {
      ulong d=HistoryDealGetTicket(k);
      if(d==0)
         continue;
      costs+=HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_SWAP)+
             HistoryDealGetDouble(d,DEAL_FEE);
      long en=HistoryDealGetInteger(d,DEAL_ENTRY);
      if(en==DEAL_ENTRY_OUT || en==DEAL_ENTRY_OUT_BY)
        {
         double v=HistoryDealGetDouble(d,DEAL_VOLUME);
         pv+=v*HistoryDealGetDouble(d,DEAL_PRICE);
         vol+=v;
         datetime dt=(datetime)HistoryDealGetInteger(d,DEAL_TIME);
         if(dt>=t)
           {
            t=dt;
            dreason=HistoryDealGetInteger(d,DEAL_REASON);
           }
         found=true;
        }
     }
   if(found && vol>0.0)
      px=pv/vol;
   return(found);
  }

//+------------------------------------------------------------------+
//| Enregistre un trade clos (stats R + ligne CSV) et le retire      |
//+------------------------------------------------------------------+
void FinalizeTrade(const int i,const double exitPx,const datetime exitT,const double costs,const string reason)
  {
   STradeRec r=g_open[i];
//--- le prix de sortie fait partie de l'excursion
   if(r.dir>0)
     {
      r.bestPx=MathMax(r.bestPx,exitPx);
      r.worstPx=MathMin(r.worstPx,exitPx);
     }
   else
     {
      r.bestPx=MathMin(r.bestPx,exitPx);
      r.worstPx=MathMax(r.worstPx,exitPx);
     }
   double res=0.0,mfe=0.0,mae=0.0;
   if(r.risk>0.0)
     {
      //--- R sur prix réels (spread inclus) + coûts (commission/swap) convertis en R
      res=r.dir*(exitPx-r.entry)/r.risk;
      if(r.riskMoney>0.0)
         res+=costs/r.riskMoney;
      mfe=MathMax(0.0,r.dir*(r.bestPx-r.entry)/r.risk);
      mae=MathMax(0.0,r.dir*(r.entry-r.worstPx)/r.risk);
     }
   ArrayResize(g_R,g_nR+1,1024);
   g_R[g_nR]=res;
   g_nR++;
   if(reason=="TIME" || reason=="END")
      g_timeouts++;

   if(g_tradeFile!=INVALID_HANDLE)
     {
      FileWrite(g_tradeFile,TS(r.openTime),TS(exitT),_Symbol,g_tf,
                PA_EventToString(r.evtType),(r.dir>0 ? "BUY" : "SELL"),
                D(r.entry,_Digits),D(r.sl,_Digits),D(r.tp,_Digits),
                D(r.risk/_Point,1),D(r.atr/_Point,1),D(exitPx,_Digits),reason,
                D(res,4),D(mfe,4),D(mae,4),IntegerToString(r.barsHeld),D(r.spreadPts,1),
                IntegerToString(InpLeftBars),IntegerToString(InpRightBars),
                IntegerToString(InpBreakMode),IntegerToString(InpTradeEvents),
                (InpRandomMode ? "1" : "0"));
      FileFlush(g_tradeFile);
     }
//--- retrait du tableau
   for(int k=i;k<g_openCount-1;k++)
      g_open[k]=g_open[k+1];
   g_openCount--;
   ArrayResize(g_open,g_openCount);
  }

//+------------------------------------------------------------------+
//| Détecte les positions fermées (SL/TP/TIME). atEnd=true : fin de  |
//| test, les positions encore ouvertes sont valorisées (END).       |
//+------------------------------------------------------------------+
void CheckClosedTrades(const bool atEnd)
  {
   for(int i=g_openCount-1;i>=0;i--)
     {
      bool stillOpen=PositionSelectByTicket(g_open[i].ticket);
      if(stillOpen && !atEnd)
         continue;
      double   exitPx=0.0,costs=0.0;
      datetime exitT=0;
      long     dreason=-1;
      string   reason="END";
      if(!stillOpen && GetExitInfo(g_open[i].posId,exitPx,exitT,costs,dreason))
        {
         if(dreason==DEAL_REASON_SL)
            reason="SL";
         else
            if(dreason==DEAL_REASON_TP)
               reason="TP";
            else
               if(g_open[i].timeClose)
                  reason="TIME";
               else
                  reason="END";
        }
      else
        {
         if(!atEnd)
            continue;   // historique pas encore disponible : on réessaie au tick suivant
         //--- position encore ouverte en fin de test : sortie théorique au prix courant
         MqlTick tk;
         if(!SymbolInfoTick(_Symbol,tk))
            continue;
         exitPx=(g_open[i].dir>0 ? tk.bid : tk.ask);
         exitT=tk.time;
         double c2=0.0;
         datetime t2=0;
         double p2=0.0;
         long r2=-1;
         GetExitInfo(g_open[i].posId,p2,t2,c2,r2);   // commission d'entrée
         costs=c2;
         if(PositionSelectByTicket(g_open[i].ticket))
            costs+=PositionGetDouble(POSITION_SWAP);
         reason="END";
        }
      FinalizeTrade(i,exitPx,exitT,costs,reason);
     }
  }

//+------------------------------------------------------------------+
//| Sortie forcée après InpMaxBarsInTrade barres                     |
//+------------------------------------------------------------------+
void CloseByTime(const int i)
  {
   g_open[i].timeClose=true;
   if(!g_trade.PositionClose(g_open[i].ticket,(ulong)MathMax(InpDeviationPoints,0)))
      PrintFormat("PA_M1_Structure_EA : échec fermeture TIME #%I64u (ret %u)",
                  g_open[i].ticket,g_trade.ResultRetcode());
  }

//+------------------------------------------------------------------+
void LogSkip(const datetime t,const int evtType,const int dir,const string why)
  {
   g_skips++;
   if(g_isOpt)
      return;
   PrintFormat("SKIP %s %s %s : %s",TS(t),PA_EventToString(evtType),(dir>0 ? "BUY" : "SELL"),why);
  }

//+------------------------------------------------------------------+
//| Ticket de la position ouverte par l'EA, non encore suivie        |
//+------------------------------------------------------------------+
ulong FindNewPosition()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0)
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         continue;
      bool known=false;
      for(int k=0;k<g_openCount;k++)
         if(g_open[k].ticket==tk)
           {
            known=true;
            break;
           }
      if(!known)
         return(tk);
     }
   return(0);
  }

//+------------------------------------------------------------------+
//| Entrée au marché à l'ouverture de la barre suivant l'événement   |
//+------------------------------------------------------------------+
void TryEnter(const SPAEvent &e,const datetime barTime)
  {
   if(e.initial)
      return;                                   // BOS initial : jamais tradé
   bool bos=PA_EventIsBOS(e.type);
   if(InpTradeEvents==0 && !bos)
      return;
   if(InpTradeEvents==1 && bos)
      return;
   int dir=(PA_EventIsBullish(e.type) ? 1 : -1);
   if(InpRandomMode)
      dir=(((MathRand()&1)==0) ? 1 : -1);        // contrôle aléatoire

   if(InpUseSession && !InSession(barTime))
     { LogSkip(barTime,e.type,dir,"SESSION"); return; }
   if(g_onePos && g_openCount>0)
     { LogSkip(barTime,e.type,dir,"POSITION_OPEN"); return; }
//--- compte netting : une position étrangère sur le symbole fusionnerait
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING && PositionSelect(_Symbol))
     { LogSkip(barTime,e.type,dir,"NETTING_POSITION"); return; }

//--- ATR de la barre fermée
   double ab[];
   if(CopyBuffer(g_atr,0,1,1,ab)!=1 || ab[0]<=0.0)
     { LogSkip(barTime,e.type,dir,"ATR_INDISPONIBLE"); return; }
   double atr=ab[0];

//--- swing opposé de référence : achat -> dernier swing low confirmé
   SPASwing refSw;
   bool okRef=(dir>0 ? g_ps.LastSwingLow(refSw) : g_ps.LastSwingHigh(refSw));
   if(!okRef)
     { LogSkip(barTime,e.type,dir,"PAS_DE_SWING"); return; }

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol,tk))
      return;
   double entry=(dir>0 ? tk.ask : tk.bid);
   double sl=(dir>0 ? refSw.price-InpSLBufferATR*atr : refSw.price+InpSLBufferATR*atr);
   sl=NormPrice(sl);
   double risk=dir*(entry-sl);
   if(risk<=0.0)
     { LogSkip(barTime,e.type,dir,"RISQUE_NEGATIF"); return; }
   if(risk<InpMinRiskATR*atr || risk>InpMaxRiskATR*atr)
     {
      LogSkip(barTime,e.type,dir,StringFormat("RISQUE_ATR %.2f",risk/atr));
      return;
     }
   double tp=NormPrice(entry+dir*InpRR*risk);

//--- distance minimale des stops imposée par le broker
   double stopsDist=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(stopsDist>0.0)
     {
      double refPx=(dir>0 ? tk.bid : tk.ask);
      if(MathAbs(refPx-sl)<stopsDist || MathAbs(tp-refPx)<stopsDist)
        { LogSkip(barTime,e.type,dir,"STOPS_LEVEL"); return; }
     }

   double vol=NormVolume(InpLots);
   string cmt=PA_EventToString(e.type);
   bool ok=(dir>0 ? g_trade.Buy(vol,_Symbol,0.0,sl,tp,cmt) : g_trade.Sell(vol,_Symbol,0.0,sl,tp,cmt));
   uint rc=g_trade.ResultRetcode();
   if(!ok || (rc!=TRADE_RETCODE_DONE && rc!=TRADE_RETCODE_DONE_PARTIAL && rc!=TRADE_RETCODE_PLACED))
     {
      PrintFormat("PA_M1_Structure_EA : ordre refusé %s ret=%u %s",cmt,rc,g_trade.ResultRetcodeDescription());
      return;
     }
   ulong ticket=FindNewPosition();
   if(ticket==0 || !PositionSelectByTicket(ticket))
     {
      Print("PA_M1_Structure_EA : position introuvable après l'ordre");
      return;
     }

   STradeRec r;
   r.ticket=ticket;
   r.posId=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   r.openTime=(datetime)PositionGetInteger(POSITION_TIME);
   r.evtType=e.type;
   r.dir=dir;
   r.entry=PositionGetDouble(POSITION_PRICE_OPEN);
   r.sl=PositionGetDouble(POSITION_SL);
   r.tp=PositionGetDouble(POSITION_TP);
   if(r.sl<=0.0)
      r.sl=sl;
   if(r.tp<=0.0)
      r.tp=tp;
   r.volume=PositionGetDouble(POSITION_VOLUME);
   r.risk=dir*(r.entry-r.sl);
   if(r.risk<=0.0)
      r.risk=risk;
   r.riskMoney=0.0;
   double pr=0.0;
   if(OrderCalcProfit((dir>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),_Symbol,r.volume,r.entry,r.sl,pr))
      r.riskMoney=MathAbs(pr);
   r.atr=atr;
   r.spreadPts=(tk.ask-tk.bid)/_Point;
   r.bestPx=(dir>0 ? tk.bid : tk.ask);
   r.worstPx=r.bestPx;
   r.barsHeld=0;
   r.timeClose=false;
   ArrayResize(g_open,g_openCount+1);
   g_open[g_openCount]=r;
   g_openCount++;
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   MqlTick tk;
   if(!SymbolInfoTick(_Symbol,tk))
      return;
   if(g_firstTime==0)
      g_firstTime=tk.time;
   g_lastTime=tk.time;

   UpdateExcursions(tk);
   CheckClosedTrades(false);

   datetime bar0=iTime(_Symbol,_Period,0);
   if(bar0==0 || bar0==g_lastBarTime)
      return;

//--- premier passage : pré-chauffage, pas de trade
   if(g_lastProcessed==0)
     {
      if(Warmup())
         g_lastBarTime=bar0;
      return;
     }
   g_lastBarTime=bar0;

//--- nouvelle barre : compteur de barres et sortie TIME
   for(int i=0;i<g_openCount;i++)
     {
      g_open[i].barsHeld++;
      if(InpMaxBarsInTrade>0 && g_open[i].barsHeld>=InpMaxBarsInTrade)
         CloseByTime(i);
     }
   CheckClosedTrades(false);

//--- barre(s) fermée(s) non encore traitée(s), ordre chronologique
   MqlRates r[];
   ArraySetAsSeries(r,false);
   int n=CopyRates(_Symbol,_Period,1,10,r);
   if(n<=0)
      return;
   bool     hasEvt=false;
   SPAEvent evt;
   ZeroMemory(evt);   // initialisation explicite (supprime l'avertissement)
   for(int i=0;i<n;i++)
     {
      if(r[i].time<=g_lastProcessed)
         continue;
      int k=g_ps.Update(r[i].time,r[i].open,r[i].high,r[i].low,r[i].close);
      g_lastProcessed=r[i].time;
      if(k>0 && i==n-1)
         hasEvt=g_ps.LastEvent(evt);
     }
   if(hasEvt)
      TryEnter(evt,bar0);
  }

//+------------------------------------------------------------------+
//| Statistiques en R (liste des result_R des trades clos)           |
//+------------------------------------------------------------------+
void ComputeStats(SRStats &s)
  {
   ZeroMemory(s);
   s.trades=g_nR;
   s.timeouts=g_timeouts;
   double gp=0.0,gl=0.0,cum=0.0,peak=0.0,dd=0.0;
   int streak=0;
   for(int i=0;i<g_nR;i++)
     {
      double x=g_R[i];
      s.sumR+=x;
      if(x>0.0)
        {
         s.wins++;
         gp+=x;
         streak=0;
        }
      else
        {
         s.losses++;
         gl+=x;
         streak++;
         if(streak>s.maxConsec)
            s.maxConsec=streak;
        }
      cum+=x;
      if(cum>peak)
         peak=cum;
      if(peak-cum>dd)
         dd=peak-cum;
     }
   if(s.trades>0)
     {
      s.winrate=(double)s.wins/s.trades;
      s.avgR=s.sumR/s.trades;
     }
   s.avgWin=(s.wins>0 ? gp/s.wins : 0.0);
   s.avgLoss=(s.losses>0 ? gl/s.losses : 0.0);
   s.pf=(gl<0.0 ? gp/(-gl) : (gp>0.0 ? 999.0 : 0.0));
   s.maxDD=dd;
  }

//--- stats + paramètres dans un tableau (frame et ligne test simple)
void PackData(const SRStats &s,const double net,const double ddp,double &d[])
  {
   ArrayResize(d,PA_FRAME_SIZE);
   d[0]=s.trades;
   d[1]=s.wins;
   d[2]=s.losses;
   d[3]=s.timeouts;
   d[4]=s.winrate;
   d[5]=s.avgR;
   d[6]=s.sumR;
   d[7]=s.pf;
   d[8]=s.maxDD;
   d[9]=s.avgWin;
   d[10]=s.avgLoss;
   d[11]=s.maxConsec;
   d[12]=net;
   d[13]=ddp;
   d[14]=(double)(long)g_firstTime;
   d[15]=(double)(long)g_lastTime;
   d[16]=InpLeftBars;
   d[17]=InpRightBars;
   d[18]=InpBreakMode;
   d[19]=InpTradeEvents;
   d[20]=InpSLBufferATR;
   d[21]=InpRR;
   d[22]=(InpRandomMode ? 1.0 : 0.0);
  }

void WriteOptHeader(const int h)
  {
   FileWrite(h,"pass","symbol","tf","from","to","left_bars","right_bars","break_mode",
             "trade_events","sl_buffer_atr","rr","random_mode","trades","wins","losses",
             "timeouts","winrate","avg_R","sum_R","profit_factor_R","max_dd_R","avg_win_R",
             "avg_loss_R","max_consec_losses","net_profit","balance_dd_pct");
  }

void WriteOptRow(const int h,const string pass,const string sym,const string tf,
                 const string left,const string right,const string mode,const string events,
                 const string slbuf,const string rr,const string rnd,const double &d[])
  {
   FileWrite(h,pass,sym,tf,
             TimeToString((datetime)(long)d[14],TIME_DATE),
             TimeToString((datetime)(long)d[15],TIME_DATE),
             left,right,mode,events,slbuf,rr,rnd,
             IntegerToString((long)d[0]),IntegerToString((long)d[1]),
             IntegerToString((long)d[2]),IntegerToString((long)d[3]),
             D(d[4],4),D(d[5],4),D(d[6],4),D(d[7],4),D(d[8],4),D(d[9],4),D(d[10],4),
             IntegerToString((long)d[11]),D(d[12],2),D(d[13],2));
  }

//+------------------------------------------------------------------+
//| Clôture des enregistrements avant calcul des stats               |
//+------------------------------------------------------------------+
void FinalizeAll()
  {
   if(g_finalized)
      return;
   CheckClosedTrades(true);
   g_finalized=true;
  }

//+------------------------------------------------------------------+
double OnTester()
  {
   FinalizeAll();
   SRStats st;
   ComputeStats(st);
   double score=0.0;
   if(st.trades>=InpMinTradesForScore && st.trades>0)
      score=st.avgR*MathSqrt((double)st.trades);
   double net=TesterStatistics(STAT_PROFIT);
   double ddp=TesterStatistics(STAT_BALANCE_DDREL_PERCENT);
   double data[];
   PackData(st,net,ddp,data);

   if(MQLInfoInteger(MQL_OPTIMIZATION)!=0)
     {
      //--- envoi au terminal (OnTesterPass) ; nom = "SYMBOLE|TF"
      if(!FrameAdd(_Symbol+"|"+g_tf,PA_FRAME_ID,score,data))
         PrintFormat("FrameAdd échec (err %d)",GetLastError());
     }
   else
     {
      //--- test simple : une ligne ajoutée au CSV d'optimisation
      string fn=StringFormat("PA_M1_opt_%s_%s_%s.csv",_Symbol,g_tf,Stamp(TimeLocal()));
      int h=FileOpen(fn,FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,';');
      if(h!=INVALID_HANDLE)
        {
         if(FileSize(h)==0)
            WriteOptHeader(h);
         FileSeek(h,0,SEEK_END);
         WriteOptRow(h,"0",_Symbol,g_tf,IntegerToString(InpLeftBars),IntegerToString(InpRightBars),
                     IntegerToString(InpBreakMode),IntegerToString(InpTradeEvents),
                     D(InpSLBufferATR,4),D(InpRR,4),(InpRandomMode ? "1" : "0"),data);
         FileClose(h);
        }
      else
         PrintFormat("PA_M1_Structure_EA : impossible d'ouvrir %s (err %d)",fn,GetLastError());
      PrintFormat("PA_M1 stats : trades=%d avgR=%.4f sumR=%.2f PF=%.2f maxDD=%.2fR skips=%d score=%.4f",
                  st.trades,st.avgR,st.sumR,st.pf,st.maxDD,g_skips,score);
     }
   return(score);
  }

//+------------------------------------------------------------------+
//| Optimisation : collecte des frames côté terminal                 |
//+------------------------------------------------------------------+
void OnTesterInit()
  {
   //--- pendant l'optimisation le fichier porte le suffixe _EN_COURS ;
   //--- il n'est renommé avec son nom définitif qu'à la toute fin (OnTesterDeinit)
   string stamp=Stamp(TimeLocal());
   g_optFinalName=StringFormat("PA_M1_opt_%s_%s_%s.csv",_Symbol,PA_TFToString(PERIOD_CURRENT),stamp);
   g_optTmpName=StringFormat("PA_M1_opt_%s_%s_%s_EN_COURS.csv",_Symbol,PA_TFToString(PERIOD_CURRENT),stamp);
   string fn=g_optTmpName;
   g_optFile=FileOpen(fn,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,';');
   if(g_optFile==INVALID_HANDLE)
     {
      PrintFormat("OnTesterInit : impossible d'ouvrir %s (err %d)",fn,GetLastError());
      return;
     }
   WriteOptHeader(g_optFile);
   PrintFormat("OnTesterInit : écriture des passes dans Common\\Files\\%s",fn);
  }

//--- lit toutes les frames disponibles et écrit une ligne par passe
void CollectFrames()
  {
   if(g_optFile==INVALID_HANDLE)
      return;
   ulong  pass=0;
   string name="";
   long   id=0;
   double value=0.0;
   double data[];
   while(FrameNext(pass,name,id,value,data))
     {
      if(id!=PA_FRAME_ID || ArraySize(data)<PA_FRAME_SIZE)
         continue;
      string sym=_Symbol;
      string tf=PA_TFToString(PERIOD_CURRENT);
      string parts[];
      if(StringSplit(name,'|',parts)==2)
        {
         sym=parts[0];
         tf=parts[1];
        }
      //--- valeurs par défaut issues de la frame, remplacées par FrameInputs
      string left=IntegerToString((long)data[16]);
      string right=IntegerToString((long)data[17]);
      string mode=IntegerToString((long)data[18]);
      string events=IntegerToString((long)data[19]);
      string slbuf=D(data[20],4);
      string rr=D(data[21],4);
      string rnd=(data[22]>0.5 ? "1" : "0");
      string params[];
      uint   pc=0;
      if(FrameInputs(pass,params,pc))
        {
         for(uint k=0;k<pc;k++)
           {
            string kv[];
            if(StringSplit(params[k],'=',kv)!=2)
               continue;
            StringTrimLeft(kv[0]);
            StringTrimRight(kv[0]);
            StringTrimLeft(kv[1]);
            StringTrimRight(kv[1]);
            if(kv[0]=="InpLeftBars")
               left=kv[1];
            else
               if(kv[0]=="InpRightBars")
                  right=kv[1];
               else
                  if(kv[0]=="InpBreakMode")
                     mode=kv[1];
                  else
                     if(kv[0]=="InpTradeEvents")
                        events=kv[1];
                     else
                        if(kv[0]=="InpSLBufferATR")
                           slbuf=kv[1];
                        else
                           if(kv[0]=="InpRR")
                              rr=kv[1];
                           else
                              if(kv[0]=="InpRandomMode")
                                 rnd=BoolStr(kv[1]);
           }
        }
      WriteOptRow(g_optFile,IntegerToString((long)pass),sym,tf,left,right,mode,events,slbuf,rr,rnd,data);
     }
   FileFlush(g_optFile);
  }

void OnTesterPass()
  {
   CollectFrames();
  }

void OnTesterDeinit()
  {
   CollectFrames();
   if(g_optFile!=INVALID_HANDLE)
     {
      FileClose(g_optFile);
      g_optFile=INVALID_HANDLE;
      //--- renommage final : le fichier sans _EN_COURS est complet
      if(FileMove(g_optTmpName,FILE_COMMON,g_optFinalName,FILE_COMMON|FILE_REWRITE))
         PrintFormat("OnTesterDeinit : CSV d'optimisation terminé -> Common\\Files\\%s",g_optFinalName);
      else
         PrintFormat("OnTesterDeinit : renommage impossible (err %d), fichier laissé sous %s",GetLastError(),g_optTmpName);
     }
  }
//+------------------------------------------------------------------+
