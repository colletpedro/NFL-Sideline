"""Exportable scientific figures; no browser/product changes."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
COL={'M0':'#8C6262','M1':'#777777','M2':'#447C89','M3':'#214E34'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'qb-risk-temporal-v2'})

def save(fig,out,name):
 fig.savefig(out/f'{name}.png',dpi=180,bbox_inches='tight',metadata={'Software':'NFL Sideline research v2'})
 svg=out/f'{name}.svg';fig.savefig(svg,bbox_inches='tight',metadata={'Date':None,'Creator':'NFL Sideline research v2'});svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n');plt.close(fig)

def run(experiment,out):
 # v1 plotting in the same process can alter global matplotlib state; reset our fixed export style.
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'qb-risk-temporal-v2'})
 e=Path(experiment);out=Path(out)
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True);r=json.loads((e/'metrics.json').read_text());std=pd.read_csv(e/'drift/standardization.csv');bins=json.loads((e/'calibration_bins.json').read_text())
 fig,axes=plt.subplots(1,2,figsize=(12,5))
 for ax,spec in zip(axes,['primary','coarse']):
  z=std[std.spec.eq(spec)];ax.plot(z.season,100*z.prevalence_common,'o-',label='Crua no suporte comum',color='#555555');ax.plot(z.season,100*z.standardized,'s--',label='Composição comum fixa',color=COL['M3']);ax.set(xlabel='Temporada (2026: somente W1–7)',ylabel='Rótulos FTN por 100 passes',title='Células principais (39)' if spec=='primary' else 'Sensibilidade mais grossa (8)');ax.set_xticks(z.season);ax.grid(alpha=.2)
 axes[0].legend();fig.suptitle('Queda de prevalência permanece após padronização descritiva\nSem extrapolação para células vazias; não é decomposição causal');fig.tight_layout(rect=(0,.09,1,.90));fig.text(.5,.01,'Referência de composição: 2023–25; suporte comum 2022–26, n≥30/célula/ano, peso≤5.\nFTN Data via nflverse · CC BY-SA 4.0; fontes transformadas; sem endosso.',ha='center',fontsize=8);save(fig,out,'standardization')
 fig,axes=plt.subplots(1,3,figsize=(14,5),sharey=True);names=['M0','M2','M3']
 for ax,year in zip(axes,[2024,2025,2026]):
  for i,name in enumerate(names):
   z=next(v for v in r if v['year']==year and v['candidate']==name);c=z['difference_vs_M1']['log_loss'];ax.errorbar(c['delta'],i,xerr=[[c['delta']-c['low']],[c['high']-c['delta']]],fmt='o',color=COL[name],capsize=4)
  ax.axvline(0,color='#888888',ls='--');ax.set_yticks(range(3),labels=names);ax.set(title=str(year)+(' W1–7' if year==2026 else ' completo'),xlabel='Delta log loss versus M1');ax.grid(axis='x',alpha=.2);ax.invert_yaxis()
 fig.suptitle('Comparações retrospectivas conhecidas — constante recente como referência\nIC95% por reamostragem pareada de jogos; negativo favorece candidato');fig.tight_layout(rect=(0,.10,1,.88));fig.text(.5,.01,'2.000 réplicas, seed 20261104.2026 não participa da seleção; intervalos condicionais aos modelos treinados.\nFTN Data via nflverse · CC BY-SA 4.0; fontes transformadas; sem endosso.',ha='center',fontsize=8);save(fig,out,'performance_vs_recent')
 fig,axes=plt.subplots(2,3,figsize=(15,9));support=[]
 for col,year in enumerate([2024,2025,2026]):
  for name in ['M0','M1','M2','M3']:
   z=pd.DataFrame(bins[f'{year}_{name}']);z['year']=year;z['candidate']=name;support.append(z);g=z[z.n.gt(0)];strong=g.n.ge(200)&g.positives.ge(10)
   for row,mask in [(0,strong),(1,~strong)]:
    part=g[mask];axes[row,col].plot(100*part.mean_probability.to_numpy(),100*part.observed_rate.to_numpy(),'o-' if row==0 else 'o',color=COL[name],label=name,markersize=4)
    if row==1:
     for v in part.itertuples():axes[row,col].annotate(f'{name}: n={v.n}/y={v.positives}',(100*v.mean_probability,100*v.observed_rate),xytext=(3,4+['M0','M1','M2','M3'].index(name)*7),textcoords='offset points',fontsize=6,color=COL[name])
  axes[0,col].plot([0,20],[0,20],'--',color='#BBBBBB');axes[0,col].set(xlim=(0,16),ylim=(0,24),title=str(year)+(' W1–7' if year==2026 else ' completo'),xlabel='p média (%)',ylabel='Observado (%) · n≥200 e y≥10');axes[0,col].grid(alpha=.2)
  axes[1,col].plot([0,35],[0,35],'--',color='#BBBBBB');axes[1,col].set(xlim=(0,35),ylim=(-3,105),xlabel='p média (%)',ylabel='Observado (%) · suporte menor');axes[1,col].grid(alpha=.2)
 axes[0,0].legend();fig.suptitle('Calibração retrospectiva conhecida — sem correção com rótulos do período avaliado\nTodas as faixas não vazias: suporte maior acima, menor abaixo; n/y completo no CSV');fig.tight_layout(rect=(0,.09,1,.92));fig.text(.5,.01,'Faixas de baixo suporte não são conectadas: poucos casos podem gerar taxas extremas, sem precisão individual.\nFTN Data via nflverse · CC BY-SA 4.0; fontes transformadas; sem endosso.',ha='center',fontsize=8);save(fig,out,'calibration_known_periods');pd.concat(support).to_csv(out/'calibration_support.csv',index=False)
 fig,axes=plt.subplots(1,2,figsize=(12,6));base=np.arange(3)
 for j,name in enumerate(['M0','M2','M3']):
  for i,year in enumerate([2024,2025,2026]):
   v=next(z for z in r if z['year']==year and z['candidate']==name)['calibration_diagnostic'];y=i+(j-1)*.17
   for ax,k,ci in [(axes[0],'offset_intercept','offset_intercept_ci'),(axes[1],'slope','slope_ci')]:
    val=v[k];lo,hi=v[ci];ax.errorbar(val,y,xerr=[[val-lo],[hi-val]],fmt='o',color=COL[name],capsize=3,label=name if i==0 else None)
 for ax in axes:ax.set_yticks(base,labels=['2024','2025','2026 W1–7']);ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
 axes[0].axvline(0,color='#999999',ls='--');axes[1].axvline(1,color='#999999',ls='--');axes[0].set_xlabel('Intercepto de calibração com offset (ideal 0)');axes[1].set_xlabel('Inclinação de calibração (ideal 1)');axes[1].legend();fig.suptitle('Diagnósticos de calibração com incerteza por jogos\nAjustes diagnósticos no período avaliado não são aplicados às previsões');fig.tight_layout(rect=(0,.10,1,.88));fig.text(.5,.01,'2.000 réplicas de jogos; M1 constante não tem inclinação identificável. Incerteza condicional, sem garantia individual.\nFTN Data via nflverse · CC BY-SA 4.0; fontes transformadas; sem endosso.',ha='center',fontsize=8);save(fig,out,'calibration_diagnostics')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--experiment',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.experiment,a.out)
