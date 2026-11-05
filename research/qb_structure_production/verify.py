"""Package invariants, rebuild sensitivity formulas, and compare two reproductions."""
import argparse
from common import *

def verify_package(p):
 p=Path(p);manifest=read(p/'manifest.json')
 for f in manifest['files']:assert sha(p/f['path'])==f['sha256'] and (p/f['path']).stat().st_size==f['bytes']
 d=pd.read_parquet(p/'plays.parquet');unique(d,'package');assert d.category.isin(CATS).all();assert d.rule.notna().all();assert d[d.category.eq('indeterminate')].reason.notna().all()
 assert not (d.category.eq('scramble_drill')&d.event_type.ne('pass')).any();assert not (d.category.eq('progression')&d.read_normalized.eq('DES')).any()
 c=pd.read_csv(p/'comparisons.csv');cats=pd.read_csv(p/'categories.csv')
 for (year,pid),g in d[d.season.ge(2023)].groupby(['season','player_id'],dropna=False):
  tab=cats[(cats.season.eq(year))&(cats.player_id.eq(pid) if pd.notna(pid) else cats.player_id.isna())];co=c[(c.season.eq(year))&(c.player_id.eq(pid) if pd.notna(pid) else c.player_id.isna())]
  assert len(tab)==6 and tab.n.sum()==len(g) and abs(tab.pct_all.sum()-100)<1e-10
  assert set(co.definition)==set(GROUPS)
  for row in co.itertuples():
   a=g[g.category.eq('progression')];b=g[g.category.isin(GROUPS[row.definition])];am=a.epa.mean();bm=b.epa.mean()
   assert len(a)==row.a_n and len(b)==row.b_n and a.epa.notna().sum()==row.a_n_epa and b.epa.notna().sum()==row.b_n_epa
   np.testing.assert_allclose([row.a_mean,row.b_mean,row.difference],[am,bm,am-bm],rtol=0,atol=1e-12,equal_nan=True)
   np.testing.assert_allclose([row.a_sum,row.b_sum],[a.epa.sum(min_count=1),b.epa.sum(min_count=1)],rtol=0,atol=1e-10,equal_nan=True)
 return dict(passed=True,files=len(manifest['files']),rows=len(d),main_rows=int(d.season.ge(2023).sum()),categories_exclusive_exhaustive=True,all_player_sensitivity_formulas_and_denominators=True,manifest_sha256=sha(p/'manifest.json'))

def compare(a,b):
 a=Path(a);b=Path(b);ma=read(a/'manifest.json');mb=read(b/'manifest.json');fa={r['path']:r for r in ma['files']};fb={r['path']:r for r in mb['files']};assert fa.keys()==fb.keys()
 unequal=[k for k in fa if fa[k]['sha256']!=fb[k]['sha256']]
 tables=[]
 for name in ['categories.csv','comparisons.csv','league.csv','context_bins.csv','context_summary.csv','extreme_diagnostics.csv','group_extremes.csv','stability.csv']:
  x=pd.read_csv(a/name);y=pd.read_csv(b/name);pd.testing.assert_frame_equal(x,y,check_exact=False,atol=1e-12,rtol=0);tables.append(name)
 pd.testing.assert_frame_equal(pd.read_parquet(a/'plays.parquet'),pd.read_parquet(b/'plays.parquet'),check_exact=True)
 return dict(passed=True,byte_identical=len(fa)-len(unequal),total_files=len(fa),different_bytes=unequal,numerical_equivalence=True,numeric_absolute_tolerance=1e-12,tables=tables,elementary_plays_exact=True,manifests_byte_identical=sha(a/'manifest.json')==sha(b/'manifest.json'))

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--package',required=True);a.add_argument('--compare');a.add_argument('--out',required=True);v=a.parse_args();r=verify_package(v.package)
 if v.compare:r['reproduction']=compare(v.package,v.compare)
 write(v.out,r);print(r)
