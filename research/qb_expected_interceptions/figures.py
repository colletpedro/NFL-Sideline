"""Exportable scientific figures; all supports remain in companion CSVs."""
import argparse
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from common import *

COLORS={'B0':'#8b9199','B1':'#b56b23','B2':'#147d83','C':'#a33d5d'}
ATTR='FTN Data via nflverse · CC BY-SA 4.0 · dados transformados · sem endosso'

def setup():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'axes.grid':True,'grid.alpha':.18,'axes.titleweight':'bold','figure.facecolor':'#faf9f6',
        'axes.facecolor':'#faf9f6','svg.hashsalt':'xint-ftn-v1-20261105','savefig.facecolor':'#faf9f6'})

def save(fig,out,name):
    fig.set_layout_engine(None)
    fig.tight_layout(rect=(0,.065,1,.89 if fig._suptitle else .98))
    fig.text(.02,.018,ATTR,fontsize=8,color='#555555')
    fig.savefig(out/f'{name}.png',dpi=180,bbox_inches='tight',metadata={'Software':'NFL Sideline research xint v1'})
    fig.savefig(out/f'{name}.svg',bbox_inches='tight',metadata={'Date':None,'Creator':'NFL Sideline research xint v1'})
    plt.close(fig)

def calibration_plot(evaluation,application,out):
    a=pd.read_csv(evaluation/'calibration.csv');b=pd.read_csv(application/'calibration.csv')
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    groups=[('all','Global',.8),('ftn_1','FTN: interceptável',.8),('ftn_0','FTN: não interceptável',.012)]
    for row,(data,period) in enumerate([(a,'2025 · fora do ajuste'),(b,'2026 · W1–8 · exploratório')]):
        for col,(group,label,limit) in enumerate(groups):
            ax=axes[row,col];ax.plot([0,limit],[0,limit],color='#505050',lw=1,ls='--',label='Observado = previsto')
            for k in (['B2','C'] if row==0 else ['B2']):
                c=data[(data.model==k)&(data.group==group)&data.n.gt(0)]
                ax.plot(c.mean_prediction,c.observed_rate,'o-',color=COLORS[k],label=k,lw=1.2)
                if k=='B2':
                    for r in c.itertuples():
                        ax.annotate(f'n={r.n}; INT={r.observed_interceptions}',(r.mean_prediction,r.observed_rate),xytext=(6,7),textcoords='offset points',fontsize=8)
            ax.set(xlim=(0,limit),ylim=(0,limit),xlabel='Probabilidade prevista média',ylabel='Frequência observada',title=f'{label}\n{period}')
            ax.xaxis.set_major_formatter(PercentFormatter(1));ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend(fontsize=8,loc='lower right')
    fig.suptitle('Calibração condicionada à classificação FTN do passe\nBins fixos; suporte anotado para B2; FTN pode conhecer o desfecho',fontsize=15)
    save(fig,out,'calibration_global_and_ftn')
    pd.concat([a.assign(period='2025'),b.assign(period='2026_W1_8')]).to_csv(out/'calibration_support.csv',index=False)

def performance_plot(evaluation,out):
    m=pd.read_csv(evaluation/'metrics.csv');bs=read(evaluation/'paired_bootstrap.json')
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for col,metric in enumerate(['log_loss','brier']):
        ax=axes[0,col];g=m[m.group.eq('all')].set_index('model').loc[['B0','B1','B2','C']]
        bars=ax.bar(g.index,g[metric],color=[COLORS[k] for k in g.index]);ax.bar_label(bars,fmt='%.5f',padding=4,fontsize=9)
        ax.set(ylabel=metric,title=f'2025 · {metric} · menor é melhor',ylim=(0,float(g[metric].max())*1.2))
        ax=axes[1,col];pairs=['C-B1','C-B2','B2-B1'];ax.axvline(0,color='#555',ls='--',lw=1)
        for i,key in enumerate(pairs):
            r=bs['all'][key][metric];ax.errorbar(r['delta'],i,xerr=[[r['delta']-r['low']],[r['high']-r['delta']]],fmt='o',color=COLORS['C'] if key.startswith('C') else COLORS['B2'],capsize=4)
            ax.annotate(f"{r['delta']:+.6f} [{r['low']:+.6f}, {r['high']:+.6f}]",(r['delta'],i),xytext=(0,12),textcoords='offset points',ha='center',fontsize=8)
        ax.set(yticks=range(len(pairs)),yticklabels=pairs,ylim=(-.6,2.6),xlabel=f'Delta {metric} · negativo favorece o primeiro',title='Bootstrap pareado de jogos · 95% percentil')
        ax.ticklabel_format(axis='x',style='sci',scilimits=(-3,3))
    fig.suptitle('Interceptações observadas · avaliação temporal retrospectiva de 2025\n17.358 passes / 272 jogos / 380 INT · 2.000 réplicas · seed 20261105',fontsize=14)
    save(fig,out,'performance_vs_references_2025')
    m.to_csv(out/'performance_2025.csv',index=False)

def player_plot(application,out):
    q=pd.read_csv(application/'players.csv');qb=q[q.position_class.eq('qb')];supported=qb[qb.eligible_passes.ge(100)]
    small=q[q.eligible_passes.lt(100)|q.position_class.ne('qb')]
    fig,(ax,key)=plt.subplots(1,2,figsize=(15,11),gridspec_kw={'width_ratios':[1.6,1]})
    limit=max(supported.observed_interceptions.max(),supported.expected_interceptions.max())+3
    ax.plot([0,limit],[0,limit],ls='--',lw=1.5,color='#555',label='Observado = esperado (identidade matemática)')
    ax.scatter(supported.expected_interceptions,supported.observed_interceptions,s=40+supported.eligible_passes*.45,color=COLORS['B2'],edgecolors='white',linewidths=1,alpha=.85)
    ordered=supported.sort_values(['name','gsis_id']);annotations=[];coords=[]
    for i,(_,r) in enumerate(ordered.iterrows(),1):
        xy=np.array([r.expected_interceptions,r.observed_interceptions]);coords.append(xy+np.array([.12,.16]))
        annotations.append((i,xy))
    # Deterministic label repulsion in data coordinates; keep point identity via thin connectors.
    coords=np.asarray(coords)
    for iteration in range(160):
        for i in range(len(coords)):
            for j in range(i):
                delta=coords[i]-coords[j]
                if abs(delta[0])<.46 and abs(delta[1])<.34:
                    step=np.array([.03 if i%2 else -.03,.045 if i>j else -.045])
                    coords[i]+=step;coords[j]-=step
        coords[:,0]=np.clip(coords[:,0],.2,limit-.2);coords[:,1]=np.clip(coords[:,1],.15,limit-.2)
    for (i,xy),label in zip(annotations,coords):
        ax.annotate(f'{i:02}',xy=xy,xytext=label,ha='center',va='center',fontsize=8,
            bbox=dict(facecolor='#faf9f6',edgecolor='none',alpha=.85,pad=.3),arrowprops=dict(arrowstyle='-',color='#999',lw=.5))
    key.axis('off');key.set_title('Jogador · passes / jogos',loc='left')
    for i,(_,r) in enumerate(ordered.iterrows(),1):
        key.text(0,1-(i-.4)/len(ordered),f'{i:02}  {r["name"]} · {r.eligible_passes}p / {r.games}j',transform=key.transAxes,fontsize=9,va='top')
    ax.set(xlim=(0,limit),ylim=(-.4,limit),xlabel='Interceptações esperadas · soma de P(INT | FTN)',ylabel='Interceptações sofridas · contagem PBP',
        title='QBs com ≥100 passes elegíveis · 2026 W1–8\nAcima: mais interceptações que a estimativa · abaixo: menos')
    ax.legend(loc='upper left',fontsize=9)
    fig.suptitle('B2 fixo · referência retrospectiva condicionada ao passe\nA diagonal não é regressão entre jogadores; residual não atribui responsabilidade',fontsize=14)
    fig.text(.02,.053,f'{len(supported)} QBs no painel; {len(small)} lançadores com <100 passes/outra posição no painel complementar e tabela completa.',fontsize=9)
    save(fig,out,'qb_observed_vs_expected_2026')
    fig,ax=plt.subplots(figsize=(11,max(5,len(small)*.22+1.8)),layout='constrained')
    small=small.sort_values(['eligible_passes','name']);yy=np.arange(len(small))
    ax.scatter(small.expected_interceptions,yy,color=COLORS['B2'],label='INT esperadas',marker='o',s=30)
    ax.scatter(small.observed_interceptions,yy,color='#a33d5d',label='INT sofridas',marker='x',s=32)
    ax.set(yticks=yy,yticklabels=[f'{r["name"]} ({r.position}) · {r.eligible_passes}p/{r.games}j' for _,r in small.iterrows()],xlabel='Interceptações · contagens',title='Pouco suporte e lançadores de outras posições · todos preservados\n2026 W1–8 · sem intervalos de habilidade');ax.legend(loc='lower right');save(fig,out,'small_support_all_positions_2026')
    q.to_csv(out/'all_players_2026.csv',index=False)

def decomposition_plot(application,out):
    q=pd.read_csv(application/'players.csv').sort_values(['position_class','name']);fig,ax=plt.subplots(figsize=(12,max(9,len(q)*.23)),layout='constrained')
    yy=np.arange(len(q));ax.barh(yy,q.expected_from_ftn_1,color=COLORS['B2'],label='Esperado em FTN=1')
    ax.barh(yy,q.expected_from_ftn_0,left=q.expected_from_ftn_1,color='#d69b38',label='Esperado em FTN=0')
    ax.scatter(q.observed_interceptions,yy,s=18,color='#34363b',marker='x',label='INT observadas')
    ax.set(yticks=yy,yticklabels=[f'{r["name"]} · {r.position} · {r.eligible_passes}p/{r.games}j' for _,r in q.iterrows()],xlabel='Interceptações · contagens (não taxas)',title='Composição da expectativa B2 · 2026 W1–8\nTodos os lançadores; contribuição de FTN=0 preservada')
    ax.tick_params(axis='y',labelsize=7.5);ax.invert_yaxis();ax.legend(loc='lower right');save(fig,out,'expected_decomposition_2026')
    q[['gsis_id','name','position','eligible_passes','games','expected_from_ftn_1','expected_from_ftn_0','expected_interceptions','observed_interceptions']].to_csv(out/'decomposition_support.csv',index=False)

def figures(evaluation,application,out):
    out=new_dir(out);evaluation=Path(evaluation);application=Path(application);setup()
    calibration_plot(evaluation,application,out);performance_plot(evaluation,out);player_plot(application,out);decomposition_plot(application,out)
    write(out/'integrity.json',dict(files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--evaluation',required=True);a.add_argument('--application',required=True);a.add_argument('--out',required=True);v=a.parse_args();offline();figures(v.evaluation,v.application,v.out)
