"""Standalone scientific figures from saved evaluation/application artifacts."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180,'svg.hashsalt':'qb-iw-v1'})
COLORS={'context':'#22577A','depth':'#AB5E20'}
def save(fig,out,name):
 fig.savefig(out/f'{name}.png',bbox_inches='tight',metadata={'Software':'NFL Sideline research v1'})
 fig.savefig(out/f'{name}.svg',bbox_inches='tight',metadata={'Date':None,'Creator':'NFL Sideline research v1'})
 plt.close(fig)
def plots(evaluation,application,out):
 evaluation=Path(evaluation);application=Path(application);out=Path(out)
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True)
 fig,axes=plt.subplots(1,2,figsize=(13,9)); tables=[]
 for v in ['context','depth']:
  rows=json.loads((evaluation/f'calibration_{v}.json').read_text()); b=pd.DataFrame(rows);b=b[b.n.gt(0)];tables.append(b.assign(variant=v))
  for ax,mask in [(axes[0],b.n.ge(50)),(axes[1],b.n.lt(50))]:
   g=b[mask]
   ax.errorbar((100*g.mean_probability).to_numpy(),(100*g.observed_rate).to_numpy(),yerr=np.array([100*(g.observed_rate-g.wilson_low),100*(g.wilson_high-g.observed_rate)]),fmt='o-',color=COLORS[v],capsize=3,label={'context':'Contexto pré-jogada','depth':'+ profundidade (sensibilidade)'}[v])
   for row in g[g.n.lt(50)].itertuples(): ax.annotate(f'n={row.n} / y={row.positives}',(100*row.mean_probability,100*row.observed_rate),xytext=(4,6 if v=='context' else -15),textcoords='offset points',fontsize=7,color=COLORS[v])
 for ax in axes:
  ax.plot([0,100],[0,100],'--',color='#777777',lw=1);ax.set(xlabel='Probabilidade média estimada (%)',ylabel='Frequência do rótulo FTN (%)');ax.grid(alpha=.2)
 axes[0].set(xlim=(0,21),ylim=(0,24),title='Faixas com n ≥ 50');axes[1].set(xlim=(0,35),ylim=(0,85),title='Faixas com n < 50 (baixa precisão)');axes[0].legend(loc='upper left')
 fig.suptitle('Calibração retrospectiva — teste REG2025 · treino 2022–2024\nFaixas fixas; sem recalibração no teste');fig.subplots_adjust(bottom=.43,top=.88,wspace=.22)
 support=[]
 for c,d in zip(json.loads((evaluation/'calibration_context.json').read_text()),json.loads((evaluation/'calibration_depth.json').read_text())):
  fmt=lambda r,k: '—' if r['n']==0 else f"{100*r[k]:.2f}%"
  support.append([c['bin'],f"{c['n']} / {c['positives']}",fmt(c,'mean_probability'),fmt(c,'observed_rate'),f"{d['n']} / {d['positives']}",fmt(d,'mean_probability'),fmt(d,'observed_rate')])
 ta=fig.add_axes([.06,.07,.90,.26]);ta.axis('off');tab=ta.table(cellText=support,colLabels=['Faixa','Contexto n / y','p médio','observado','Profund. n / y','p médio','observado'],loc='center',cellLoc='center');tab.auto_set_font_size(False);tab.set_fontsize(9);tab.scale(1,1.3)
 fig.text(.5,.01,'n = passes; y = positivos. Barras Wilson 95% por passe (não corrigidas por jogo). Faixas vazias no CSV.\nFTN Data via nflverse · CC BY-SA 4.0. Fonte transformada; pesquisa local, sem endosso.',ha='center',fontsize=8);save(fig,out,'calibration_2025')
 pd.concat(tables).to_csv(out/'calibration_support.csv',index=False)
 q=pd.read_csv(application/'qb_context.csv');b=pd.read_csv(application/'qb_depth.csv');shown=q[q.passes.ge(100)].sort_values('names'); small=q[q.passes.lt(100)]
 shown=shown.reset_index(drop=True);shown['figure_id']=np.arange(1,len(shown)+1);shown[['figure_id','passer_player_id','names','teams','passes','games']].to_csv(out/'plot_passers.csv',index=False)
 fig,(ax,key)=plt.subplots(1,2,figsize=(13,9),gridspec_kw={'width_ratios':[2.8,1]});ax.scatter(small.expected,small.observed,s=18,color='#999999',alpha=.7,label='Menos de 100 passes');ax.scatter(shown.expected,shown.observed,s=shown.passes/3,color=COLORS['context'],alpha=.65,label='100+ passes (convenção)')
 for _,g in shown.groupby('observed'):
  for i,r in enumerate(g.sort_values('expected').itertuples()):
   offset=[5,17,-11,29,-23][i%5]
   ax.annotate(str(r.figure_id),(r.expected,r.observed),xytext=(4,offset),textcoords='offset points',fontsize=8,color=COLORS['context'],arrowprops={'arrowstyle':'-','color':'#BBBBBB','lw':.5})
 key.axis('off');key.text(0,1,'ID · passer / equipe · passes',fontsize=9,weight='bold',va='top')
 for i,r in enumerate(shown.itertuples()): key.text(0,.96-i*.029,f'{r.figure_id:02} · {r.names} / {r.teams} · {r.passes}',fontsize=8,va='top')
 lim=max(q.expected.max(),q.observed.max())+2;ax.plot([0,lim],[0,lim],'--',color='#777777');ax.set(xlabel='Soma de probabilidades esperadas',ylabel='Passes rotulados interceptáveis observados',xlim=(-.2,lim),ylim=(-.3,lim));ax.legend();ax.grid(alpha=.2);fig.suptitle('Observado versus esperado — REG2026 W1–7\nContexto pré-jogada; modelo refit 2022–2025; todos os passers');fig.subplots_adjust(top=.88,bottom=.12,wspace=.13);fig.text(.5,.025,'Identificação por GSIS; tamanho do ponto ∝ passes. Sem interpretação causal ou ranking de qualidade.\nFTN Data via nflverse · CC BY-SA 4.0. Fonte transformada; pesquisa local, sem endosso.',ha='center',fontsize=8);save(fig,out,'observed_expected_2026')
 fig,ax=plt.subplots(figsize=(10,max(9,len(shown)*.28)));y=np.arange(len(shown));valid=shown.ci_low_per100.notna();s=shown.loc[valid]
 ax.errorbar(s.difference_per100,y[valid],xerr=[s.difference_per100-s.ci_low_per100,s.ci_high_per100-s.difference_per100],fmt='o',color=COLORS['context'],capsize=3);ax.set_yticks(y,labels=[f'{r.names} / {r.teams} · n={r.passes}, g={r.games}' for r in shown.itertuples()],fontsize=8);ax.axvline(0,color='#777777',ls='--');ax.set(xlabel='100 × (observado − esperado) / passes',title='Diferença exploratória por 100 passes — REG2026 W1–7\n100+ passes para legibilidade; ordem alfabética; tabela completa inclui todos');ax.grid(axis='x',alpha=.2);ax.invert_yaxis();fig.text(.5,.005,'IC percentil 95%: 2.000 reamostragens de jogos por passer, modelo fixo. Não é teste de habilidade persistente.\nPositivo = mais rótulos que o esperado. FTN Data via nflverse · CC BY-SA 4.0; sem endosso.',ha='center',fontsize=8);save(fig,out,'difference_per100_2026')
 z=q.merge(b,on='passer_player_id',suffixes=('_context','_depth'));z=z[z.passes_context.ge(100)].sort_values(['names_context','passer_player_id']);fig,ax=plt.subplots(figsize=(10,max(9,len(z)*.28)));y=np.arange(len(z))
 ax.hlines(y,z.difference_per100_context,z.difference_per100_depth,color='#999999',lw=1.5);ax.scatter(z.difference_per100_context,y,color=COLORS['context'],label='Contexto pré-jogada',s=30,zorder=3);ax.scatter(z.difference_per100_depth,y,color=COLORS['depth'],label='+ profundidade',s=28,marker='s',zorder=3)
 ax.set_yticks(y,labels=[f'{r.names_context} / {r.teams_context} · n={r.passes_context}' for r in z.itertuples()],fontsize=8);ax.axvline(0,color='#777777',ls='--');ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.set(xlabel='Diferença por 100 passes',title='Sensibilidade à profundidade escolhida — REG2026 W1–7\n100+ passes (convenção); ordem alfabética; perguntas condicionais diferentes');ax.legend(loc='lower right');fig.text(.5,.005,'Mesmo alvo, população, protocolo e algoritmo. Gráfico: 32 passers; tabela completa: todos os 62.\nPontos não são efeitos causais. FTN Data via nflverse · CC BY-SA 4.0; sem endosso.',ha='center',fontsize=8);save(fig,out,'depth_sensitivity_2026')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evaluation',required=True);p.add_argument('--application',required=True);p.add_argument('--out',required=True);a=p.parse_args();plots(a.evaluation,a.application,a.out)
