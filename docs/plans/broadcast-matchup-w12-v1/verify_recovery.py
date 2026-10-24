"""Run in a fresh process, with historical/current original locations blocked."""
import argparse
import json
from pathlib import Path
import sys
from nfl_sideline_etl.matchup_w12.package import read, reproduce, hashes

p=argparse.ArgumentParser();p.add_argument('--recovery',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
root=a.recovery.parent
blocked=[str(root/name) for name in ('bundle','bundle-reconciled','bundle-final','verified-copy','reproduced-bundle')]+[
    '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/',
    '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/',
    '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/',
    '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/',
    '/Users/pedrocollet/.codex/worktrees/broadcast-w12-expansion-v1/',
    '/Users/pedrocollet/.codex/worktrees/broadcast-comprehension-v1/']
def guard(event,args):
    if event in ('open','os.listdir','os.scandir') and args and isinstance(args[0],(str,bytes)) and any(str(args[0]).startswith(x) for x in blocked):
        raise PermissionError('Original location blocked by recovery verification')
sys.addaudithook(guard)
i,d,m=read(a.recovery);reproduce(a.recovery,a.output)
report=dict(bundleId=m['bundleId'],games=len(d),offensiveProductions=i['counts']['offensiveProductions'],files=len(hashes(a.recovery)),
    originalLocationsBlocked=blocked,independentProcess=True,reproducedFromRecovery=True,identical=hashes(a.recovery)==hashes(a.output),
    source=str(a.recovery),output=str(a.output),sameDiskOnly=True)
a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
