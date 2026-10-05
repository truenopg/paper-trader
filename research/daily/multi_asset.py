"""Daily multi-asset walk-forward lab (free Yahoo data, 2005-2026).
Signals at close t, traded at close t (next-bar return applied via shift), cost per side in bps.
Families: Donchian breakout, SMA trend, time-series momentum, RSI2 reversion w/ SMA200 filter, Bollinger reversion.
Walk-forward: every year, per asset pick the best config by Sharpe over the prior 5y, trade it the next year.
Also: fixed classic params, no selection. Portfolio = equal-vol sleeves."""
import numpy as np, pandas as pd, yfinance as yf, itertools, sys, os, warnings
warnings.filterwarnings("ignore")
A = {"EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X","USDJPY":"USDJPY=X","AUDUSD":"AUDUSD=X","USDCAD":"USDCAD=X",
     "USDCHF":"USDCHF=X","NZDUSD":"NZDUSD=X","SPX":"^GSPC","NDX":"^NDX","DJI":"^DJI","DAX":"^GDAXI",
     "FTSE":"^FTSE","N225":"^N225","GOLD":"GC=F","SILVER":"SI=F","OIL":"CL=F","BTC":"BTC-USD","ETH":"ETH-USD"}
COST = {k:(1 if "USD" in k and k not in("BTC","ETH") else 3) for k in A}
def load():
    f="/tmp/daily.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    d={k:yf.download(v,start="2005-01-01",progress=False,auto_adjust=True)["Close"].squeeze() for k,v in A.items()}
    d=pd.DataFrame(d); d.to_pickle(f); return d
def rsi(c,n):
    r=c.diff(); u=r.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-r.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+u/dn)
def sig(c,fam,p):
    if fam=="don":
        n=p; hi=c.rolling(n).max().shift(1); lo=c.rolling(n).min().shift(1)
        s=pd.Series(np.nan,c.index); s[c>hi]=1; s[c<lo]=-1; return s.ffill().fillna(0)
    if fam=="sma": f,s_=p; return np.sign(c.rolling(f).mean()-c.rolling(s_).mean()).fillna(0)
    if fam=="tsm": return np.sign(c.pct_change(p)).fillna(0)
    if fam=="rsi2":  # long dips in uptrend, short rallies in downtrend, exit at RSI cross 50
        r=rsi(c,2); up=c>c.rolling(200).mean(); s=pd.Series(np.nan,c.index)
        s[(r<p)&up]=1; s[(r>100-p)&~up]=-1; s[((s.shift(1)>0)&(r>50))|((s.shift(1)<0)&(r<50))]=0
        return s.ffill().fillna(0)
    if fam=="bb":
        n,k=p; m=c.rolling(n).mean(); sd=c.rolling(n).std(); z=(c-m)/sd; s=pd.Series(np.nan,c.index)
        s[z<-k]=1; s[z>k]=-1; s[(z.abs()<0.2)]=0; return s.ffill().fillna(0)
GRID=[("don",n) for n in (20,40,60,100,150)]+[("sma",(f,s)) for f,s in ((10,50),(20,100),(50,200),(30,150))]+\
     [("tsm",n) for n in (20,60,120,250)]+[("rsi2",p) for p in (5,10,15)]+[("bb",(20,2)),("bb",(50,2.5))]
def pnl(c,fam,p,cost_bps):
    s=sig(c,fam,p); r=c.pct_change().fillna(0)
    return s.shift(1).fillna(0)*r - s.diff().abs().fillna(0)*cost_bps/1e4
def sharpe(x): return np.sqrt(252)*x.mean()/x.std() if x.std()>0 else -9
def volscale(x,target=0.10,lb=60):
    v=x.rolling(lb).std().shift(1)*np.sqrt(252); return (x*(target/v).clip(upper=4)).dropna()
def stats(x,name=""):
    eq=(1+x).cumprod(); dd=(eq/eq.cummax()-1); yrs=len(x)/252
    d=x.groupby(x.index.date).sum()
    return dict(name=name,CAGR=round(eq.iloc[-1]**(1/yrs)-1,4),Sharpe=round(sharpe(x),2),maxDD=round(dd.min(),4),worstDay=round(x.min(),4),yrs=round(yrs,1))
if __name__=="__main__":
    D=load().dropna(how="all"); print(D.shape, D.index[0].date(), D.index[-1].date())
    P={}  # per asset per config vol-scaled pnl
    for a in D:
        c=D[a].dropna()
        for fam,p in GRID: P[(a,fam,str(p))]=volscale(pnl(c,fam,p,COST[a]))
    P=pd.DataFrame(P).sort_index(); P.to_pickle("/tmp/P.pkl"); print(P.shape)
