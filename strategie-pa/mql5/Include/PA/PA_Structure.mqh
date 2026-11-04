//+------------------------------------------------------------------+
//|                                                 PA_Structure.mqh |
//|  Module 1 - Structure : swings, HH/HL/LH/LL, tendance, BOS, CHOCH |
//+------------------------------------------------------------------+
//| Fichier commun (indicateur PA_Structure.mq5 + EA                  |
//| PA_M1_Structure_EA.mq5). Aucun input ici : les réglages sont      |
//| passés à CPAStructure::Init() par le programme appelant :         |
//|   left      (InpLeftBars)  : nb de barres à gauche du pivot (>=1) |
//|   right     (InpRightBars) : nb de barres à droite du pivot (>=1) |
//|              = délai de confirmation (zéro look-ahead)            |
//|   breakMode (InpBreakMode) : 0 = clôture au-delà du niveau,       |
//|                              1 = mèche au-delà du niveau          |
//|   maxStore  : 0 = historique illimité ; N>0 = ne garde que ~N     |
//|               swings/événements récents (économie mémoire EA)     |
//|                                                                   |
//| Utilisation : appeler Update() une fois par barre FERMÉE, dans    |
//| l'ordre chronologique. Les cassures sont évaluées à la clôture.   |
//|                                                                   |
//| Règles codées (SPEC_MODULE1.md) :                                 |
//|  - Swing high à i : High[i] > High des `left` barres avant ET des |
//|    `right` barres après (strict). Confirmé à la clôture de        |
//|    i+right. Idem (inverse) pour les swing lows.                   |
//|  - HH si high > swing high précédent, sinon LH (égalité => LH).   |
//|    LL si low < swing low précédent, sinon HL (égalité => HL).     |
//|  - Tendance NONE au départ. 1re cassure d'un swing = BOS initial  |
//|    (flag initial=true, non tradé) qui fixe UP ou DOWN.            |
//|  - UP : cassure du dernier swing high confirmé = BOS_UP ;         |
//|         cassure du swing low protégé = CHOCH_DN -> DOWN.          |
//|    DOWN : symétrique (BOS_DN / CHOCH_UP -> UP).                   |
//|  - Swing protégé : dernier swing low confirmé au moment de la     |
//|    dernière cassure haussière (BOS_UP/CHOCH_UP/initial). Si le    |
//|    creux qui a précédé la cassure n'est confirmé qu'après         |
//|    (délai `right`), il devient le protégé à sa confirmation.      |
//|  - Un swing n'est cassé qu'une fois (flag broken).                |
//|  - Ordre dans une barre : 1) cassures, 2) confirmation du pivot.  |
//|  - Mode mèche, barre qui franchit les deux niveaux : on retient   |
//|    le côté de la couleur de la bougie (close>=open => haussier).  |
//+------------------------------------------------------------------+
#ifndef PA_STRUCTURE_MQH
#define PA_STRUCTURE_MQH

#define PA_BREAK_CLOSE 0
#define PA_BREAK_WICK  1

//--- Tendance
enum ENUM_PA_TREND
  {
   PA_TREND_DOWN = -1,
   PA_TREND_NONE = 0,
   PA_TREND_UP   = 1
  };

//--- Type de swing
enum ENUM_PA_SWING_TYPE
  {
   PA_SWING_LOW  = -1,
   PA_SWING_HIGH = 1
  };

//--- Classement du swing
enum ENUM_PA_SWING_LABEL
  {
   PA_LBL_NONE = 0,   // premier swing de son type (pas de comparaison)
   PA_LBL_HH   = 1,
   PA_LBL_LH   = 2,
   PA_LBL_HL   = 3,
   PA_LBL_LL   = 4
  };

//--- Type d'événement
enum ENUM_PA_EVENT
  {
   PA_EVT_NONE     = 0,
   PA_EVT_BOS_UP   = 1,
   PA_EVT_BOS_DN   = 2,
   PA_EVT_CHOCH_UP = 3,
   PA_EVT_CHOCH_DN = 4
  };

//--- Swing confirmé
struct SPASwing
  {
   long              id;            // identifiant unique croissant
   datetime          time;          // temps de la barre pivot
   datetime          confirm_time;  // temps de la barre de confirmation (pivot + right)
   long              bar;           // n° de barre interne (0 = 1re barre traitée)
   int               type;          // ENUM_PA_SWING_TYPE
   int               label;         // ENUM_PA_SWING_LABEL
   double            price;         // High (swing high) ou Low (swing low)
   bool              broken;        // déjà cassé ?
   datetime          broken_time;   // temps de la barre de cassure
  };

//--- Événement de structure
struct SPAEvent
  {
   datetime          time;          // temps de la barre de cassure (clôturée)
   long              bar;           // n° de barre interne de la cassure
   int               type;          // ENUM_PA_EVENT
   bool              initial;       // BOS initial (tendance NONE) : non tradé
   double            level;         // prix du swing cassé
   datetime          swing_time;    // temps du swing cassé
   long              swing_id;      // id du swing cassé
   double            close;         // clôture de la barre de cassure
   int               trend_before;  // ENUM_PA_TREND avant
   int               trend_after;   // ENUM_PA_TREND après
  };

//+------------------------------------------------------------------+
//| Moteur de structure incrémental                                  |
//+------------------------------------------------------------------+
class CPAStructure
  {
private:
   int               m_left;
   int               m_right;
   int               m_mode;
   int               m_win;         // taille fenêtre = left + right + 1
   int               m_maxStore;
   //--- fenêtre glissante des dernières barres
   datetime          m_wTime[];
   double            m_wHigh[];
   double            m_wLow[];
   int               m_wCount;
   long              m_bars;        // nb de barres traitées
   //--- stockage
   SPASwing          m_swings[];
   int               m_swCount;
   SPAEvent          m_events[];
   int               m_evCount;
   long              m_nextId;
   //--- état
   int               m_lastHigh;    // index du dernier swing high confirmé (-1 si aucun)
   int               m_lastLow;
   int               m_protHigh;    // swing high protégé (tendance DOWN)
   int               m_protLow;     // swing low protégé (tendance UP)
   ENUM_PA_TREND     m_trend;
   datetime          m_lastBreakTime; // temps de la dernière cassure qui a fixé la tendance
   //--- drapeaux de la dernière barre traitée
   int               m_newHigh;
   int               m_newLow;
   bool              m_newEvent;

   bool              BrokenUp(const int idx,const double h,const double c) const;
   bool              BrokenDn(const int idx,const double l,const double c) const;
   void              MarkBroken(const int idx,const datetime t);
   void              CheckBreaks(const datetime t,const double o,const double h,const double l,const double c);
   void              DetectPivot(void);
   int               AddSwing(const int type,const datetime t,const long bar,const double price,const datetime confirmTime);
   void              AddEvent(const datetime t,const int type,const bool initial,const int swIdx,const double c,const int before,const int after);
   void              Trim(void);

public:
                     CPAStructure(void);
                    ~CPAStructure(void) {}
   bool              Init(const int left,const int right,const int breakMode,const int maxStore=0);
   void              Reset(void);
   int               Update(const datetime t,const double o,const double h,const double l,const double c);

   //--- accès
   int               Left(void)  const { return m_left;  }
   int               Right(void) const { return m_right; }
   int               BreakMode(void) const { return m_mode; }
   ENUM_PA_TREND     Trend(void) const { return m_trend; }
   long              BarsProcessed(void) const { return m_bars; }
   int               SwingsTotal(void) const { return m_swCount; }
   int               EventsTotal(void) const { return m_evCount; }
   bool              GetSwing(const int i,SPASwing &s) const;
   bool              GetEvent(const int i,SPAEvent &e) const;
   bool              LastSwingHigh(SPASwing &s) const { return GetSwing(m_lastHigh,s); }
   bool              LastSwingLow(SPASwing &s)  const { return GetSwing(m_lastLow,s);  }
   bool              ProtectedHigh(SPASwing &s) const { return GetSwing(m_protHigh,s); }
   bool              ProtectedLow(SPASwing &s)  const { return GetSwing(m_protLow,s);  }
   //--- résultats de la dernière barre passée à Update()
   bool              NewSwingHigh(SPASwing &s) const { return GetSwing(m_newHigh,s); }
   bool              NewSwingLow(SPASwing &s)  const { return GetSwing(m_newLow,s);  }
   bool              NewEvent(SPAEvent &e) const;
   bool              LastEvent(SPAEvent &e) const { return GetEvent(m_evCount-1,e); }
  };

//+------------------------------------------------------------------+
CPAStructure::CPAStructure(void)
  {
   m_left=3;
   m_right=2;
   m_mode=PA_BREAK_CLOSE;
   m_maxStore=0;
   m_win=m_left+m_right+1;
   Reset();
  }

//+------------------------------------------------------------------+
//| Initialisation des réglages (remet l'état à zéro)                |
//+------------------------------------------------------------------+
bool CPAStructure::Init(const int left,const int right,const int breakMode,const int maxStore)
  {
   if(left<1 || right<1 || (breakMode!=PA_BREAK_CLOSE && breakMode!=PA_BREAK_WICK))
      return(false);
   m_left=left;
   m_right=right;
   m_mode=breakMode;
   m_maxStore=(maxStore<0 ? 0 : maxStore);
   m_win=m_left+m_right+1;
   Reset();
   return(true);
  }

//+------------------------------------------------------------------+
//| Remise à zéro complète de l'état                                 |
//+------------------------------------------------------------------+
void CPAStructure::Reset(void)
  {
   ArrayResize(m_wTime,m_win);
   ArrayResize(m_wHigh,m_win);
   ArrayResize(m_wLow,m_win);
   m_wCount=0;
   m_bars=0;
   ArrayResize(m_swings,0,1024);
   ArrayResize(m_events,0,256);
   m_swCount=0;
   m_evCount=0;
   m_nextId=0;
   m_lastHigh=-1;
   m_lastLow=-1;
   m_protHigh=-1;
   m_protLow=-1;
   m_trend=PA_TREND_NONE;
   m_lastBreakTime=0;
   m_newHigh=-1;
   m_newLow=-1;
   m_newEvent=false;
  }

//+------------------------------------------------------------------+
//| Traite une barre fermée. Retourne 1 si un événement BOS/CHOCH     |
//| a été détecté sur cette barre, 0 sinon.                           |
//+------------------------------------------------------------------+
int CPAStructure::Update(const datetime t,const double o,const double h,const double l,const double c)
  {
   m_newHigh=-1;
   m_newLow=-1;
   m_newEvent=false;
//--- ajout dans la fenêtre glissante
   if(m_wCount<m_win)
     {
      m_wTime[m_wCount]=t;
      m_wHigh[m_wCount]=h;
      m_wLow[m_wCount]=l;
      m_wCount++;
     }
   else
     {
      for(int k=0;k<m_win-1;k++)
        {
         m_wTime[k]=m_wTime[k+1];
         m_wHigh[k]=m_wHigh[k+1];
         m_wLow[k]=m_wLow[k+1];
        }
      m_wTime[m_win-1]=t;
      m_wHigh[m_win-1]=h;
      m_wLow[m_win-1]=l;
     }
   m_bars++;
//--- 1) cassures des niveaux connus AVANT cette barre
   CheckBreaks(t,o,h,l,c);
//--- 2) confirmation du pivot situé `right` barres en arrière
   if(m_wCount==m_win)
      DetectPivot();
//--- 3) purge éventuelle de l'historique
   Trim();
   return(m_newEvent ? 1 : 0);
  }

//+------------------------------------------------------------------+
bool CPAStructure::BrokenUp(const int idx,const double h,const double c) const
  {
   if(idx<0 || idx>=m_swCount || m_swings[idx].broken)
      return(false);
   if(m_mode==PA_BREAK_CLOSE)
      return(c>m_swings[idx].price);
   return(h>m_swings[idx].price);
  }

//+------------------------------------------------------------------+
bool CPAStructure::BrokenDn(const int idx,const double l,const double c) const
  {
   if(idx<0 || idx>=m_swCount || m_swings[idx].broken)
      return(false);
   if(m_mode==PA_BREAK_CLOSE)
      return(c<m_swings[idx].price);
   return(l<m_swings[idx].price);
  }

//+------------------------------------------------------------------+
void CPAStructure::MarkBroken(const int idx,const datetime t)
  {
   if(idx<0 || idx>=m_swCount || m_swings[idx].broken)
      return;
   m_swings[idx].broken=true;
   m_swings[idx].broken_time=t;
  }

//+------------------------------------------------------------------+
//| Évaluation des cassures à la clôture de la barre                 |
//+------------------------------------------------------------------+
void CPAStructure::CheckBreaks(const datetime t,const double o,const double h,const double l,const double c)
  {
   bool upLast=BrokenUp(m_lastHigh,h,c);
   bool dnLast=BrokenDn(m_lastLow,l,c);
   bool upProt=BrokenUp(m_protHigh,h,c);
   bool dnProt=BrokenDn(m_protLow,l,c);
   bool bull=(c>=o);
   int  evt=PA_EVT_NONE;
   int  idx=-1;
   bool initial=false;
   int  before=(int)m_trend;

   if(m_trend==PA_TREND_NONE)
     {
      if(upLast && (!dnLast || bull))
        { evt=PA_EVT_BOS_UP; idx=m_lastHigh; initial=true; }
      else
         if(dnLast)
           { evt=PA_EVT_BOS_DN; idx=m_lastLow; initial=true; }
     }
   else
      if(m_trend==PA_TREND_UP)
        {
         if(upLast && (!dnProt || bull))
           { evt=PA_EVT_BOS_UP; idx=m_lastHigh; }
         else
            if(dnProt)
              { evt=PA_EVT_CHOCH_DN; idx=m_protLow; }
         //--- cassure interne d'un swing low non protégé : marqué, pas d'événement
         if(dnLast && m_lastLow!=m_protLow)
            MarkBroken(m_lastLow,t);
        }
      else // PA_TREND_DOWN
        {
         if(dnLast && (!upProt || !bull))
           { evt=PA_EVT_BOS_DN; idx=m_lastLow; }
         else
            if(upProt)
              { evt=PA_EVT_CHOCH_UP; idx=m_protHigh; }
         //--- cassure interne d'un swing high non protégé
         if(upLast && m_lastHigh!=m_protHigh)
            MarkBroken(m_lastHigh,t);
        }

   if(evt==PA_EVT_NONE)
      return;

   MarkBroken(idx,t);
   if(evt==PA_EVT_BOS_UP || evt==PA_EVT_CHOCH_UP)
     {
      //--- nouveau swing low protégé = dernier swing low confirmé non cassé
      if(m_lastLow>=0 && !m_swings[m_lastLow].broken)
         m_protLow=m_lastLow;
      else
         if(!(evt==PA_EVT_BOS_UP && m_trend==PA_TREND_UP))
            m_protLow=-1;              // sera fixé par mise à jour tardive
      //--- sinon (BOS_UP en UP) on garde le protégé courant
      m_protHigh=-1;
      m_trend=PA_TREND_UP;
     }
   else
     {
      if(m_lastHigh>=0 && !m_swings[m_lastHigh].broken)
         m_protHigh=m_lastHigh;
      else
         if(!(evt==PA_EVT_BOS_DN && m_trend==PA_TREND_DOWN))
            m_protHigh=-1;
      m_protLow=-1;
      m_trend=PA_TREND_DOWN;
     }
   m_lastBreakTime=t;
   AddEvent(t,evt,initial,idx,c,before,(int)m_trend);
  }

//+------------------------------------------------------------------+
//| Détection du pivot au centre-gauche de la fenêtre (index left)   |
//+------------------------------------------------------------------+
void CPAStructure::DetectPivot(void)
  {
   int    p=m_left;
   double ph=m_wHigh[p];
   double pl=m_wLow[p];
   bool   isHigh=true;
   bool   isLow=true;
   for(int k=0;k<m_win;k++)
     {
      if(k==p)
         continue;
      if(m_wHigh[k]>=ph)
         isHigh=false;
      if(m_wLow[k]<=pl)
         isLow=false;
      if(!isHigh && !isLow)
         break;
     }
   long     pivotBar=m_bars-1-m_right;
   datetime confirmT=m_wTime[m_win-1];
   if(isHigh)
      m_newHigh=AddSwing(PA_SWING_HIGH,m_wTime[p],pivotBar,ph,confirmT);
   if(isLow)
      m_newLow=AddSwing(PA_SWING_LOW,m_wTime[p],pivotBar,pl,confirmT);
  }

//+------------------------------------------------------------------+
//| Ajoute un swing confirmé, le classe, met à jour l'état           |
//+------------------------------------------------------------------+
int CPAStructure::AddSwing(const int type,const datetime t,const long bar,const double price,const datetime confirmTime)
  {
   SPASwing s;
   s.id=m_nextId++;
   s.time=t;
   s.confirm_time=confirmTime;
   s.bar=bar;
   s.type=type;
   s.price=price;
   s.broken=false;
   s.broken_time=0;
   s.label=PA_LBL_NONE;
   if(type==PA_SWING_HIGH)
     {
      if(m_lastHigh>=0)
         s.label=(price>m_swings[m_lastHigh].price ? PA_LBL_HH : PA_LBL_LH);
     }
   else
     {
      if(m_lastLow>=0)
         s.label=(price<m_swings[m_lastLow].price ? PA_LBL_LL : PA_LBL_HL);
     }
   ArrayResize(m_swings,m_swCount+1,1024);
   m_swings[m_swCount]=s;
   int idx=m_swCount;
   m_swCount++;

   if(type==PA_SWING_HIGH)
     {
      m_lastHigh=idx;
      //--- mise à jour tardive du protégé en tendance DOWN : sommet antérieur à la
      //--- dernière cassure baissière, plus récent que le protégé actuel
      if(m_trend==PA_TREND_DOWN && m_lastBreakTime>0 && t<m_lastBreakTime &&
         (m_protHigh<0 || t>m_swings[m_protHigh].time))
         m_protHigh=idx;
     }
   else
     {
      m_lastLow=idx;
      if(m_trend==PA_TREND_UP && m_lastBreakTime>0 && t<m_lastBreakTime &&
         (m_protLow<0 || t>m_swings[m_protLow].time))
         m_protLow=idx;
     }
   return(idx);
  }

//+------------------------------------------------------------------+
void CPAStructure::AddEvent(const datetime t,const int type,const bool initial,const int swIdx,const double c,const int before,const int after)
  {
   SPAEvent e;
   e.time=t;
   e.bar=m_bars-1;
   e.type=type;
   e.initial=initial;
   e.level=m_swings[swIdx].price;
   e.swing_time=m_swings[swIdx].time;
   e.swing_id=m_swings[swIdx].id;
   e.close=c;
   e.trend_before=before;
   e.trend_after=after;
   ArrayResize(m_events,m_evCount+1,256);
   m_events[m_evCount]=e;
   m_evCount++;
   m_newEvent=true;
  }

//+------------------------------------------------------------------+
//| Purge de l'historique (maxStore>0) sans toucher aux swings actifs|
//+------------------------------------------------------------------+
void CPAStructure::Trim(void)
  {
   if(m_maxStore<=0)
      return;
//--- swings
   if(m_swCount>2*m_maxStore)
     {
      int minActive=m_swCount;
      if(m_lastHigh>=0 && m_lastHigh<minActive)
         minActive=m_lastHigh;
      if(m_lastLow>=0 && m_lastLow<minActive)
         minActive=m_lastLow;
      if(m_protHigh>=0 && m_protHigh<minActive)
         minActive=m_protHigh;
      if(m_protLow>=0 && m_protLow<minActive)
         minActive=m_protLow;
      int rem=MathMin(m_swCount-m_maxStore,minActive);
      if(rem>0)
        {
         for(int k=rem;k<m_swCount;k++)
            m_swings[k-rem]=m_swings[k];
         m_swCount-=rem;
         ArrayResize(m_swings,m_swCount,1024);
         if(m_lastHigh>=0)
            m_lastHigh-=rem;
         if(m_lastLow>=0)
            m_lastLow-=rem;
         if(m_protHigh>=0)
            m_protHigh-=rem;
         if(m_protLow>=0)
            m_protLow-=rem;
         if(m_newHigh>=0)
            m_newHigh-=rem;
         if(m_newLow>=0)
            m_newLow-=rem;
        }
     }
//--- événements
   if(m_evCount>2*m_maxStore)
     {
      int rem=m_evCount-m_maxStore;
      for(int k=rem;k<m_evCount;k++)
         m_events[k-rem]=m_events[k];
      m_evCount-=rem;
      ArrayResize(m_events,m_evCount,256);
     }
  }

//+------------------------------------------------------------------+
bool CPAStructure::GetSwing(const int i,SPASwing &s) const
  {
   if(i<0 || i>=m_swCount)
      return(false);
   s=m_swings[i];
   return(true);
  }

//+------------------------------------------------------------------+
bool CPAStructure::GetEvent(const int i,SPAEvent &e) const
  {
   if(i<0 || i>=m_evCount)
      return(false);
   e=m_events[i];
   return(true);
  }

//+------------------------------------------------------------------+
bool CPAStructure::NewEvent(SPAEvent &e) const
  {
   if(!m_newEvent)
      return(false);
   return(GetEvent(m_evCount-1,e));
  }

//+------------------------------------------------------------------+
//| Utilitaires texte                                                |
//+------------------------------------------------------------------+
string PA_EventToString(const int type)
  {
   switch(type)
     {
      case PA_EVT_BOS_UP:
         return("BOS_UP");
      case PA_EVT_BOS_DN:
         return("BOS_DN");
      case PA_EVT_CHOCH_UP:
         return("CHOCH_UP");
      case PA_EVT_CHOCH_DN:
         return("CHOCH_DN");
     }
   return("NONE");
  }

//+------------------------------------------------------------------+
string PA_LabelToString(const int label)
  {
   switch(label)
     {
      case PA_LBL_HH:
         return("HH");
      case PA_LBL_LH:
         return("LH");
      case PA_LBL_HL:
         return("HL");
      case PA_LBL_LL:
         return("LL");
     }
   return("");
  }

//+------------------------------------------------------------------+
string PA_TrendToString(const int trend)
  {
   if(trend==PA_TREND_UP)
      return("UP");
   if(trend==PA_TREND_DOWN)
      return("DOWN");
   return("NONE");
  }

//+------------------------------------------------------------------+
//| "PERIOD_M15" -> "M15"                                            |
//+------------------------------------------------------------------+
string PA_TFToString(const ENUM_TIMEFRAMES tf)
  {
   ENUM_TIMEFRAMES p=(tf==PERIOD_CURRENT ? (ENUM_TIMEFRAMES)Period() : tf);
   return(StringSubstr(EnumToString(p),7));
  }

//+------------------------------------------------------------------+
//| true si l'événement va dans le sens haussier                     |
//+------------------------------------------------------------------+
bool PA_EventIsBullish(const int type)
  {
   return(type==PA_EVT_BOS_UP || type==PA_EVT_CHOCH_UP);
  }

//+------------------------------------------------------------------+
bool PA_EventIsBOS(const int type)
  {
   return(type==PA_EVT_BOS_UP || type==PA_EVT_BOS_DN);
  }

#endif // PA_STRUCTURE_MQH
//+------------------------------------------------------------------+
