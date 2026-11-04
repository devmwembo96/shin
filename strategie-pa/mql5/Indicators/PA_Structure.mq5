//+------------------------------------------------------------------+
//|                                                 PA_Structure.mq5 |
//|  Module 1 - Affichage swings, HH/HL/LH/LL, BOS, CHOCH (sans       |
//|  repainting : tout est calculé sur barres fermées).               |
//+------------------------------------------------------------------+
//| INPUTS                                                            |
//|  InpLeftBars      : barres à gauche du pivot (>=1)                |
//|  InpRightBars     : barres à droite du pivot = délai de           |
//|                     confirmation (>=1)                            |
//|  InpBreakMode     : 0 = clôture au-delà du niveau, 1 = mèche      |
//|  InpMaxBars       : nb de barres d'historique calculées           |
//|                     (0 = tout l'historique du graphique)          |
//|  InpShowSwings    : points sur les swings                         |
//|  InpShowLabels    : textes HH/HL/LH/LL                            |
//|  InpShowBreaks    : lignes + textes BOS/CHOCH                     |
//|  InpShowInitial   : afficher aussi les BOS initiaux (tendance     |
//|                     NONE, non tradés), texte "BOS*"               |
//|  InpColSwingHigh / InpColSwingLow : couleurs des swings           |
//|  InpColBOSUp / InpColBOSDn        : couleurs des BOS              |
//|  InpColCHOCHUp / InpColCHOCHDn    : couleurs des CHOCH            |
//|  InpLineWidth     : épaisseur des lignes BOS/CHOCH                |
//|  InpFontSize      : taille des textes                             |
//|  InpExportCSV     : exporte les événements dans Common\Files :    |
//|     PA_M1_events_<SYMBOL>_<TF>_L<l>_R<r>_B<mode>.csv              |
//|     colonnes time;type;price;swing_time (test de parité avec l'EA)|
//|     type = BOS_UP|BOS_DN|CHOCH_UP|CHOCH_DN, suffixe _INIT pour    |
//|     les BOS initiaux.                                             |
//+------------------------------------------------------------------+
#property copyright   "strategie-pa"
#property version     "1.00"
#property description "Structure PA : swings, HH/HL/LH/LL, BOS, CHOCH (barres fermées, sans repainting)"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2

#property indicator_label1  "Swing High"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrTomato
#property indicator_width1  2

#property indicator_label2  "Swing Low"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrDodgerBlue
#property indicator_width2  2

#include <PA\PA_Structure.mqh>

//--- inputs
input group "Structure"
input int    InpLeftBars    = 3;      // Barres à gauche du pivot
input int    InpRightBars   = 2;      // Barres à droite (confirmation)
input int    InpBreakMode   = 0;      // 0 = clôture, 1 = mèche
input int    InpMaxBars     = 5000;   // Barres calculées (0 = tout)
input group "Affichage"
input bool   InpShowSwings  = true;   // Points sur les swings
input bool   InpShowLabels  = true;   // Textes HH/HL/LH/LL
input bool   InpShowBreaks  = true;   // Lignes BOS/CHOCH
input bool   InpShowInitial = true;   // Afficher les BOS initiaux
input color  InpColSwingHigh = clrTomato;
input color  InpColSwingLow  = clrDodgerBlue;
input color  InpColBOSUp     = clrLimeGreen;
input color  InpColBOSDn     = clrOrangeRed;
input color  InpColCHOCHUp   = clrAqua;
input color  InpColCHOCHDn   = clrMagenta;
input int    InpLineWidth    = 1;
input int    InpFontSize     = 8;
input group "Export"
input bool   InpExportCSV    = false; // Export CSV des événements (Common\Files)

//--- buffers
double g_bufHigh[];
double g_bufLow[];

//--- état
CPAStructure g_ps;
string       g_prefix="";
datetime     g_lastTime=0;     // temps de la dernière barre fermée traitée
string       g_csvName="";

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpLeftBars<1 || InpRightBars<1 || (InpBreakMode!=0 && InpBreakMode!=1))
     {
      Print("PA_Structure : paramètres invalides (LeftBars>=1, RightBars>=1, BreakMode 0/1)");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!g_ps.Init(InpLeftBars,InpRightBars,InpBreakMode,0))
      return(INIT_PARAMETERS_INCORRECT);

   SetIndexBuffer(0,g_bufHigh,INDICATOR_DATA);
   SetIndexBuffer(1,g_bufLow,INDICATOR_DATA);
   ArraySetAsSeries(g_bufHigh,false);
   ArraySetAsSeries(g_bufLow,false);
   PlotIndexSetInteger(0,PLOT_ARROW,159);
   PlotIndexSetInteger(1,PLOT_ARROW,159);
   PlotIndexSetDouble(0,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetDouble(1,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,InpColSwingHigh);
   PlotIndexSetInteger(1,PLOT_LINE_COLOR,InpColSwingLow);
   PlotIndexSetInteger(0,PLOT_DRAW_TYPE,(InpShowSwings ? DRAW_ARROW : DRAW_NONE));
   PlotIndexSetInteger(1,PLOT_DRAW_TYPE,(InpShowSwings ? DRAW_ARROW : DRAW_NONE));

   g_prefix=StringFormat("PAS_%d_%d_%d_",InpLeftBars,InpRightBars,InpBreakMode);
   g_csvName=StringFormat("PA_M1_events_%s_%s_L%d_R%d_B%d.csv",
                          _Symbol,PA_TFToString(PERIOD_CURRENT),InpLeftBars,InpRightBars,InpBreakMode);
   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("PA_Structure(%d,%d,%s)",InpLeftBars,InpRightBars,(InpBreakMode==0 ? "close" : "wick")));
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
   g_lastTime=0;
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0,g_prefix);
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
//| Création d'un texte                                              |
//+------------------------------------------------------------------+
void PADrawText(const string name,const datetime t,const double price,const string txt,
              const color clr,const ENUM_ANCHOR_POINT anchor)
  {
   if(ObjectFind(0,name)<0)
     {
      if(!ObjectCreate(0,name,OBJ_TEXT,0,t,price))
         return;
     }
   else
      ObjectMove(0,name,0,t,price);
   ObjectSetString(0,name,OBJPROP_TEXT,txt);
   ObjectSetString(0,name,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,InpFontSize);
   ObjectSetInteger(0,name,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,anchor);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,name,OBJPROP_BACK,false);
  }

//+------------------------------------------------------------------+
//| Swing : point (buffer) + label                                   |
//+------------------------------------------------------------------+
void DrawSwing(const SPASwing &s,const int barIdx)
  {
   bool isHigh=(s.type==PA_SWING_HIGH);
   if(barIdx>=0)
     {
      if(isHigh)
         g_bufHigh[barIdx]=s.price;
      else
         g_bufLow[barIdx]=s.price;
     }
   if(!InpShowLabels)
      return;
   string txt=PA_LabelToString(s.label);
   if(txt=="")
      return;
   string name=g_prefix+"L"+IntegerToString((long)s.time)+(isHigh ? "H" : "L");
   PADrawText(name,s.time,s.price,txt,(isHigh ? InpColSwingHigh : InpColSwingLow),
            (isHigh ? ANCHOR_LOWER : ANCHOR_UPPER));
  }

//+------------------------------------------------------------------+
//| BOS/CHOCH : ligne horizontale swing -> barre de cassure + texte  |
//+------------------------------------------------------------------+
void DrawEvent(const SPAEvent &e)
  {
   if(!InpShowBreaks)
      return;
   if(e.initial && !InpShowInitial)
      return;
   bool  up=PA_EventIsBullish(e.type);
   bool  bos=PA_EventIsBOS(e.type);
   color clr=(bos ? (up ? InpColBOSUp : InpColBOSDn) : (up ? InpColCHOCHUp : InpColCHOCHDn));
   string base=g_prefix+"E"+IntegerToString((long)e.time)+"_"+IntegerToString(e.type);
   string ln=base+"_ln";
   if(ObjectFind(0,ln)<0)
      ObjectCreate(0,ln,OBJ_TREND,0,e.swing_time,e.level,e.time,e.level);
   ObjectSetInteger(0,ln,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,ln,OBJPROP_WIDTH,InpLineWidth);
   ObjectSetInteger(0,ln,OBJPROP_STYLE,(bos ? STYLE_SOLID : STYLE_DASH));
   ObjectSetInteger(0,ln,OBJPROP_RAY_RIGHT,false);
   ObjectSetInteger(0,ln,OBJPROP_RAY_LEFT,false);
   ObjectSetInteger(0,ln,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,ln,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,ln,OBJPROP_BACK,false);
   string txt=(bos ? "BOS" : "CHOCH");
   if(e.initial)
      txt=txt+"*";
   datetime mid=(datetime)(((long)e.swing_time+(long)e.time)/2);
   PADrawText(base+"_tx",mid,e.level,txt,clr,(up ? ANCHOR_LOWER : ANCHOR_UPPER));
  }

//+------------------------------------------------------------------+
//| Export CSV                                                       |
//+------------------------------------------------------------------+
string EventCSVType(const SPAEvent &e)
  {
   string s=PA_EventToString(e.type);
   if(e.initial)
      s=s+"_INIT";
   return(s);
  }

//--- réécrit le fichier complet (après recalcul total)
void WriteAllEventsCSV()
  {
   int h=FileOpen(g_csvName,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,';');
   if(h==INVALID_HANDLE)
     {
      PrintFormat("PA_Structure : impossible d'ouvrir %s (err %d)",g_csvName,GetLastError());
      return;
     }
   FileWrite(h,"time","type","price","swing_time");
   int n=g_ps.EventsTotal();
   SPAEvent e;
   for(int i=0;i<n;i++)
     {
      if(!g_ps.GetEvent(i,e))
         continue;
      FileWrite(h,TimeToString(e.time,TIME_DATE|TIME_SECONDS),EventCSVType(e),
                DoubleToString(e.level,_Digits),TimeToString(e.swing_time,TIME_DATE|TIME_SECONDS));
     }
   FileClose(h);
  }

//--- ajoute une ligne en fin de fichier (temps réel)
void AppendEventCSV(const SPAEvent &e)
  {
   int h=FileOpen(g_csvName,FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,';');
   if(h==INVALID_HANDLE)
      return;
   if(FileSize(h)==0)
      FileWrite(h,"time","type","price","swing_time");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,TimeToString(e.time,TIME_DATE|TIME_SECONDS),EventCSVType(e),
             DoubleToString(e.level,_Digits),TimeToString(e.swing_time,TIME_DATE|TIME_SECONDS));
   FileClose(h);
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   ArraySetAsSeries(time,false);
   ArraySetAsSeries(open,false);
   ArraySetAsSeries(high,false);
   ArraySetAsSeries(low,false);
   ArraySetAsSeries(close,false);

   if(rates_total<InpLeftBars+InpRightBars+2)
      return(0);

   bool full=(prev_calculated<=0 || g_lastTime==0);
   int  first=0;
   if(full)
     {
      //--- recalcul complet : remise à zéro du moteur, des objets et des buffers
      ObjectsDeleteAll(0,g_prefix);
      g_ps.Reset();
      g_lastTime=0;
      ArrayInitialize(g_bufHigh,EMPTY_VALUE);
      ArrayInitialize(g_bufLow,EMPTY_VALUE);
      first=(InpMaxBars>0 ? MathMax(0,rates_total-1-InpMaxBars) : 0);
     }
   else
     {
      //--- nouvelles cases de buffer
      for(int k=MathMax(prev_calculated,0);k<rates_total;k++)
        {
         g_bufHigh[k]=EMPTY_VALUE;
         g_bufLow[k]=EMPTY_VALUE;
        }
      //--- reprise après la dernière barre fermée traitée (repérée par son temps)
      int i=rates_total-2;
      while(i>=0 && time[i]>g_lastTime)
         i--;
      first=i+1;
     }

//--- traitement des barres FERMÉES uniquement (la barre rates_total-1 est en cours)
   for(int i=first;i<=rates_total-2;i++)
     {
      int n=g_ps.Update(time[i],open[i],high[i],low[i],close[i]);
      g_lastTime=time[i];
      SPASwing s;
      if(g_ps.NewSwingHigh(s))
         DrawSwing(s,i-InpRightBars);
      if(g_ps.NewSwingLow(s))
         DrawSwing(s,i-InpRightBars);
      if(n>0)
        {
         SPAEvent e;
         if(g_ps.LastEvent(e))
           {
            DrawEvent(e);
            if(InpExportCSV && !full)
               AppendEventCSV(e);
           }
        }
     }

   if(full && InpExportCSV)
      WriteAllEventsCSV();

   return(rates_total);
  }
//+------------------------------------------------------------------+
