import numpy as np, pandas as pd
from multi_asset import stats, sharpe
P=pd.read_pickle("/tmp/P.pkl"); P.columns.names=["a","fam","p"]
R=P.fillna(0)
def port(df,target=0.10):
    x=df.mean(axis=1)  # equal-weight sleeves (each 10% vol)
    return x
OOS=R.index>="2015-01-01"
print("== fixed params, whole-family portfolios, all 18 assets, OOS 2015+ (no selection) ==")
for fam in ["don","sma","tsm","rsi2","bb"]:
    cols=[c for c in R.columns if c[1]==fam]; x=R[cols].mean(axis=1)
    print(fam, stats(x[OOS],fam), "IS", stats(x[~OOS],"")["Sharpe"])
allx=R.mean(axis=1); print("ALL families", stats(allx[OOS],"all"))
# per-asset-class
cls={"FX":["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","NZDUSD"],"IDX":["SPX","NDX","DJI","DAX","FTSE","N225"],"CMD":["GOLD","SILVER","OIL"],"CRY":["BTC","ETH"]}
for k,v in cls.items():
    cols=[c for c in R.columns if c[0] in v]; print(k, stats(R[cols].mean(axis=1)[OOS],k))
# walk-forward selection: each year pick top-3 configs per asset by 5y Sharpe
out=[]
for y in range(2012,2027):
    tr=R[(R.index>=f"{y-5}-01-01")&(R.index<f"{y}-01-01")]; te=R[(R.index>=f"{y}-01-01")&(R.index<f"{y+1}-01-01")]
    if len(te)==0: continue
    sleeves=[]
    for a in sorted(set(c[0] for c in R.columns)):
        cols=[c for c in R.columns if c[0]==a]; sh=tr[cols].apply(sharpe).sort_values(ascending=False)
        if sh.iloc[0]>0.3: sleeves.append(te[list(sh.index[:3])].mean(axis=1))
    if sleeves: out.append(pd.concat(sleeves,axis=1).mean(axis=1))
wf=pd.concat(out); print("== WALK-FORWARD select top3/asset by 5y Sharpe ==", stats(wf,"wf"))
wf.to_pickle("/tmp/wf.pkl")
# yearly
print(wf.groupby(wf.index.year).apply(lambda s:(1+s).prod()-1).round(3).to_dict())
# null: random sign flip of signals timing: shuffle wf returns blocks -> Sharpe dist of random long/short on same assets
rng=np.random.default_rng(0); D=pd.read_pickle("/tmp/daily.pkl"); ret=D.pct_change().fillna(0)
ns=[]
for i in range(200):
    xs=[]
    for a in ret:
        r=ret[a]; s=pd.Series(np.sign(rng.standard_normal(len(r)//20+1)).repeat(20)[:len(r)],r.index)  # random 20d positions
        xs.append(s.shift(1).fillna(0)*r)
    x=pd.concat(xs,axis=1).mean(axis=1); ns.append(sharpe(x[x.index>="2015-01-01"]))
print("null random-position equal-weight Sharpe: mean %.2f 95pct %.2f"%(np.mean(ns),np.percentile(ns,95)), " real wf Sharpe %.2f"%sharpe(wf[wf.index>="2015-01-01"]))
