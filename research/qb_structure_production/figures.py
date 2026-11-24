"""Scientific, exportable PNG/SVG figures. Uses frozen aggregates, never ranks skill."""
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from common import *
NAMES={'progression':'Progressão registrada','scramble_drill':'Passe SD','scramble':'Scramble QB','throwaway':'Throwaway','sack':'Sack','indeterminate':'Residual / indeterminado'}
COLORS=['#245b78','#399c9d','#8bc3aa','#dfad58','#ad585b','#c9ced2']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','svg.hashsalt':'qb-structure-production-1.0.0','figure.dpi':120,'savefig.dpi':180})

def save(fig,p):
 fig.text(.02,.012,'Fonte: PBP nflverse + FTN Data via nflverse (CC BY-SA 4.0) · v1.0.0 · descritivo, sem atribuição causal',fontsize=8,color='#555555')
 fig.savefig(str(p)+'.png',facecolor='white',bbox_inches='tight',metadata={'Software':'NFL Sideline research v1.0.0'})
 fig.savefig(str(p)+'.svg',facecolor='white',bbox_inches='tight',metadata={'Date':None,'Creator':'NFL Sideline research v1.0.0'})
 plt.close(fig)

def heatmap(frame,labels,title,xlabels,path):
 fig,ax=plt.subplots(figsize=(11,max(6,len(frame)*.29+2)));a=np.array(frame,float);limit=max(.5,np.nanmax(np.abs(a))) if np.isfinite(a).any() else 1
 im=ax.imshow(np.ma.masked_invalid(a),cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit),aspect='auto')
 ax.set_yticks(range(len(labels)),labels);ax.set_xticks(range(len(xlabels)),xlabels);ax.set_title(title,pad=22);ax.tick_params(axis='both',length=0)
 for i in range(a.shape[0]):
  for j in range(a.shape[1]):
   v=a[i,j];ax.text(j,i,'—' if not np.isfinite(v) else f'{v:+.3f}',ha='center',va='center',fontsize=8,color='white' if np.isfinite(v) and abs(v)>limit*.65 else '#222222')
 fig.colorbar(im,ax=ax,shrink=.7,label='EPA/jogada: média A − média B da definição')
 fig.subplots_adjust(left=.25,right=.88,bottom=.12,top=.89);save(fig,path)

def generate(package,out=None):
 package=Path(package);out=new(out or package/'figures')
 c=pd.read_csv(package/'comparisons.csv');league=pd.read_csv(package/'league.csv');d=pd.read_parquet(package/'plays.parquet');d=d[d.season.ge(2023)];cur=int(c.season.max())
 q=c[c.position_class.eq('qb')];m=q[q.season.eq(cur)&q.definition.eq('main')&q.status.eq('legible')].sort_values(['audited_name','player_id']).reset_index(drop=True)
 m['figure_number']=np.arange(1,len(m)+1);m.to_csv(out/'scatter_support.csv',index=False)
 # 1: all eligible events, including occasional non-QB and known residual.
 counts=d.groupby(['season','category']).size().unstack(fill_value=0).reindex(columns=CATS,fill_value=0);counts.to_csv(out/'distribution_support.csv')
 fig,ax=plt.subplots(figsize=(12,6));left=np.zeros(len(counts))
 for cat,color in zip(CATS,COLORS):
  vals=(100*counts[cat]/counts.sum(axis=1)).to_numpy();ax.barh(np.arange(len(counts)),vals,left=left,label=NAMES[cat],color=color,height=.6)
  for i,v in enumerate(vals):
   if v>=3:ax.text(left[i]+v/2,i,f'{v:.1f}%',ha='center',va='center',fontsize=9,color='white' if cat in ['progression','sack'] else '#18252d')
  left+=vals
 ax.set_yticks(range(len(counts)),[f'{y}  ·  n={int(counts.loc[y].sum()):,}' for y in counts.index]);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('% de todos os dropbacks elegíveis (inclui outras posições)');ax.set_title('Composição dos dropbacks por temporada');ax.legend(loc='upper center',bbox_to_anchor=(.45,-.16),ncol=3,frameon=False);fig.subplots_adjust(left=.18,bottom=.27,top=.88);save(fig,out/'01_distribution')
 # 2 main scatter: numbered point + full names and support linked on right.
 fig,(ax,legend)=plt.subplots(1,2,figsize=(14,9),gridspec_kw={'width_ratios':[2,1]});legend.axis('off');l=league[league.season.eq(cur)].set_index('category');am=l.loc['progression','mean_epa'];bm=(l.loc[['scramble_drill','scramble'],'sum_epa'].sum()/l.loc[['scramble_drill','scramble'],'n_epa'].sum())
 lo=min(m.b_mean.min(),m.a_mean.min(),0)-.12;hi=max(m.b_mean.max(),m.a_mean.max())+.12;ax.plot([lo,hi],[lo,hi],color='#999999',ls=':',lw=1,label='Igualdade: diferença zero');ax.axvline(bm,color='#399c9d',ls='--',label=f'Média liga B = {bm:.3f}');ax.axhline(am,color='#245b78',ls='--',label=f'Média liga A = {am:.3f}')
 ax.scatter(m.b_mean,m.a_mean,s=250,color='#245b78',edgecolor='white',zorder=3)
 for r in m.itertuples():
  near=m[(m.figure_number.ne(r.figure_number)) & ((m.b_mean-r.b_mean).abs()<.035) & ((m.a_mean-r.a_mean).abs()<.03)]
  if len(near):
   offset=-20 if r.figure_number<near.figure_number.min() else 20
   ax.annotate(str(r.figure_number),(r.b_mean,r.a_mean),xytext=(0,offset),textcoords='offset points',ha='center',va='center',fontsize=8,color='#245b78',arrowprops=dict(arrowstyle='-',color='#245b78',lw=.7),zorder=4)
  else:ax.text(r.b_mean,r.a_mean,str(r.figure_number),ha='center',va='center',color='white',fontsize=8,zorder=4)
  legend.text(0,1-.047*(r.figure_number-1),f'{r.figure_number:02d}  {r.audited_name}\n      A {r.a_n_epa} / B {r.b_n_epa} · {r.comparison_games} jogos',fontsize=9,va='top')
 ax.set_xlim(lo,hi);ax.set_ylim(min(-.25,m.a_mean.min()-.08),max(.65,m.a_mean.max()+.08));ax.set_xlabel('Improvisação identificada · EPA/jogada (SD + scramble QB)');ax.set_ylabel('Progressão registrada · EPA/jogada');ax.set_title(f'{cur}: produção observada nas duas condições');ax.legend(loc='lower right',fontsize=8);ax.grid(alpha=.15);legend.set_title('Identidade e suporte: n EPA válido',loc='left',fontsize=10,pad=20)
 fig.subplots_adjust(left=.08,right=.98,bottom=.12,top=.89,wspace=.23);save(fig,out/'02_progression_vs_improvisation')
 # 3 same cohort and denominator.
 fig,(ax,legend)=plt.subplots(1,2,figsize=(14,8),gridspec_kw={'width_ratios':[2,1]});legend.axis('off');ax.scatter(m.b_pct_all,m.b_mean,s=250,color='#399c9d',edgecolor='white')
 for r in m.itertuples():
  ax.text(r.b_pct_all,r.b_mean,str(r.figure_number),ha='center',va='center',fontsize=8,color='#102a2d')
  legend.text(0,1-.05*(r.figure_number-1),f'{r.figure_number:02d}  {r.audited_name} · B {r.b_n_epa}/{r.dropbacks}',fontsize=9,va='top')
 ax.axhline(bm,color='#245b78',ls='--',label=f'Média liga B = {bm:.3f}');freq=100*l.loc[['scramble_drill','scramble'],'n'].sum()/l.n.sum();ax.axvline(freq,color='#777777',ls=':',label=f'Frequência liga = {freq:.1f}%');ax.set_xlabel('SD + scramble QB / todos os dropbacks do jogador (%)');ax.set_ylabel('Improvisação identificada · EPA/jogada');ax.set_title(f'{cur}: frequência e produção em improvisação identificada');ax.legend(fontsize=8);ax.grid(alpha=.15);fig.subplots_adjust(left=.08,right=.97,bottom=.13,top=.9,wspace=.25);save(fig,out/'03_frequency_vs_production')
 # 4 fixed main cohort. Do not admit extra players to broaden B.
 matrix=[];labels=[];support=[]
 for r in m.itertuples():
  vals=[];counts_side=[]
  for definition in ['main','S1','S2','S3']:
   row=q[q.season.eq(cur)&q.player_id.eq(r.player_id)&q.definition.eq(definition)].iloc[0];vals.append(row.difference);counts_side.append(int(row.b_n_epa));support.append(row.to_dict())
  matrix.append(vals);labels.append(f'{r.audited_name} · B '+ '/'.join(map(str,counts_side)))
 pd.DataFrame(support).to_csv(out/'sensitivity_support.csv',index=False)
 heatmap(matrix,labels,f'{cur}: diferença depende da definição\nMesmo conjunto principal; B por definição na margem. S3: n<25 exige cautela.', ['Principal\nSD + scramble','S1\n+ throwaways','S2\n+ todos os sacks','S3\nsomente passes SD'],out/'04_sensitivity')
 # 5 all QB with >=2 legible seasons, fixed selection by support not level.
 h=q[q.definition.eq('main')&q.status.eq('legible')];ids=h.groupby('player_id').size();ids=ids[ids>=2].index;h=h[h.player_id.isin(ids)];names=h[['player_id','audited_name']].drop_duplicates().sort_values('audited_name');years=sorted(q.season.unique());matrix=[];labels=[]
 for r in names.itertuples():
  g=h[h.player_id.eq(r.player_id)].set_index('season');matrix.append([g.loc[y,'difference'] if y in g.index else np.nan for y in years]);labels.append(r.audited_name)
 h.to_csv(out/'historical_support.csv',index=False)
 heatmap(matrix,labels,'Comparações por temporada, sem agregado histórico\nQB com ≥2 temporadas legíveis; — = suporte abaixo do corte / ausência',list(map(str,years)),out/'05_historical')
 write(out/'index.json',dict(metricVersion=VERSION,cohort=dict(position='qb',minimum_A_epa=100,minimum_B_epa=25,minimum_games=5,current_n=len(m)),units='EPA per play; frequency denominator all eligible dropbacks',diagonal='equality indicates zero difference, not ideal performance',attribution='FTN Data via nflverse, CC BY-SA 4.0',files=[p.name for p in sorted(out.iterdir()) if p.is_file()]))
 write(package/'manifest.json',dict(schemaVersion=1,metricVersion=VERSION,sourceManifestSha256=read(package/'index.json')['sourceManifestSha256'],files=[dict(path=str(p.relative_to(package)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(package.rglob('*')) if p.is_file() and p.name!='manifest.json']))
 return out

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--package',required=True);a.add_argument('--out');v=a.parse_args();print(generate(v.package,v.out))
