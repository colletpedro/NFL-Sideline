"""Independent raw-Parquet rational ledger versus every selected original/document.
Does not import the projector, its COUNT_MAP, or its arithmetic functions.
"""
import argparse
import base64
from collections import Counter
from decimal import Decimal, localcontext, ROUND_HALF_UP
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

from nominal_selection import ROOT, save, hashes
from nfl_sideline_etl.metrics_observations.lineage import load_source
from nfl_sideline_etl.metrics_observations.publication import read


def run(artifacts):
    selection = json.loads((artifacts / 'selection.json').read_bytes())
    source, backup = Path(selection['source']), Path(selection['backup'])
    before = json.loads((artifacts / 'preserved-hashes.json').read_bytes())
    assert hashes(source) == before == hashes(backup)
    temporal, lineage = load_source(source / 'materialized')
    documents, manifest = read(artifacts / 'bundle')
    # Independent accepted raw auditor, no adapter/writer/projector imports.
    spec = importlib.util.spec_from_file_location('raw_auditor', ROOT / 'docs/plans/metrics/e5b-6/audit.py')
    auditor = importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)
    raw = artifacts / 'independent-raw'; raw.mkdir(exist_ok=False)
    paths = {}
    for resource in temporal['resources']:
        if resource['kind'] != 'FILE': continue
        payload = resource['payload']; path = raw / (payload['sha256'] + '.parquet')
        path.write_bytes(base64.b64decode(payload['bytes_base64']))
        assert auditor.sha(path) == payload['sha256']
        paths[resource['revision_id']] = path
    inputs = {}
    for c in temporal['calculations']:
        for i in c['original']['manifest']['inputs']:
            assert i['source_revision_id'] not in inputs or inputs[i['source_revision_id']] == i['kind']
            inputs[i['source_revision_id']] = i['kind']
    led = auditor.ledger([p for rid,p in paths.items() if inputs[rid] == 'calendar'],
                         [p for rid,p in paths.items() if inputs[rid] == 'pbp'])
    games = {gid:g for gid,g in led['games'].items() if g['season']==2026 and g['phase']=='REG' and g['week'] in (1,2)}
    assert sorted(games.values(),key=lambda g:g['game_id']) == selection['games']
    assert len(games)==32 and len({t for g in games.values() for t in (g['home_team'],g['away_team'])})==32
    assert Counter((g['season'],g['phase']) for gid,g in led['games'].items() if led['audits'][gid]['unique_n']) == {(2025,'REG'):272,(2025,'POST'):13,(2026,'REG'):32}
    count_fields = {'eligibleN':'eligible_n','epaN':'epa_n','successN':'success_n',
                    'epaMissingN':'epa_missing_n','epaNonfiniteN':'epa_nonfinite_n'}
    # All observed originals are checked directly against raw ledger, before documents.
    original_groups = 0
    for c in temporal['calculations']:
        gid = c['game']['game_id']
        audit = led['audits'][gid]
        for k,v in audit.items(): assert c['original']['coverage'][k] == v, (gid,k)
        for s in c['statistics']:
            expected = led['statistics'][gid,s['team'],s['role'],s['foundation']]
            for k in count_fields.values(): assert s[k] == expected[k], (gid,k)
            assert Fraction(Decimal(s['epa_sum'])) == expected['epa_sum'] if s['epa_n'] else s['epa_sum'] is None
            original_groups += 1
    seen, categories, member_count, examples, rounding = set(), Counter(), 0, {}, 0
    by_revision = {c['revision_id']: c for c in temporal['calculations']}
    for d in documents:
        team,role,foundation = (d['subject'][k] for k in ('team','role','foundation'))
        rq=d['request']; weeks=rq['period']['weeks']
        key=(rq['season'],rq['phase'],tuple(weeks),team,role,foundation)
        assert key not in seen; seen.add(key)
        category = 'individual' if rq['season']==2026 and weeks in ([1],[2]) else 'inclusive' if rq['season']==2026 and weeks==[1,2] else 'retained'
        categories[category]+=1
        mapping=manifest['lineageByObservation'][d['observationId']]['associations']
        assert len(mapping)==len({a['gameId'] for a in mapping})
        declared={gid for gid,g in led['games'].items() if (g['season'],g['phase'])==(rq['season'],rq['phase']) and g['week'] in weeks and team in (g['home_team'],g['away_team'])}
        assert {m['gameId'] for m in d['members']}==declared
        assert {a['gameId'] for a in mapping}==declared
        eligible_members=[]; general_n=0; unknown_n=0
        for m in d['members']:
            gid=m['gameId']; a=next(a for a in mapping if a['gameId']==gid)
            if not led['audits'][gid]['unique_n']:
                assert m['sourceState']=='ABSENT' and m['statistics'] is None and a['temporalRevisionId'] is None
                continue
            c=by_revision[a['temporalRevisionId']]
            assert c['game']['game_id']==gid and c['calculation_id']==a['calculationId'] and c['coverage_revision_id']==a['coverageRevisionId']
            assert m['calculationId']==a['calculationId'] and m['coverageRevisionId']==a['coverageRevisionId'] and m['artifactId']==a['artifactId']
            s=led['statistics'][gid,team,role,foundation]
            general=led['statistics'][gid,team,role,'general']['eligible_n']
            for camel,snake in count_fields.items(): assert m['statistics'][camel]==s[snake]
            assert m['statistics']['generalEligibleN']==general
            assert m['statistics']['unknownFilterFlagsN']==led['audits'][gid]['unknown_filter_flags_n']
            assert Fraction(Decimal(m['statistics']['epaSum']))==s['epa_sum'] if s['epa_n'] else m['statistics']['epaSum'] is None
            eligible_members.append((gid,s)); general_n+=general; unknown_n+=led['audits'][gid]['unknown_filter_flags_n']; member_count+=1
        if eligible_members:
            sums={snake:sum(s[snake] for _,s in eligible_members) for snake in count_fields.values()}
            exact_epa=sum((s['epa_sum'] for _,s in eligible_members),Fraction(0))
            for camel,snake in count_fields.items(): assert d['totals'][camel]==sums[snake]
            assert d['totals']['generalEligibleN']==general_n and d['totals']['unknownFilterFlagsN']==unknown_n
            assert Fraction(Decimal(d['totals']['epaSum']))==exact_epa if sums['epa_n'] else d['totals']['epaSum'] is None
            expected_values={'volume':Fraction(sums['eligible_n']),
                'epa':exact_epa/sums['epa_n'] if sums['epa_n'] else None,
                'successRate':Fraction(sums['success_n'],sums['epa_n']) if sums['epa_n'] else None,
                'frequency':Fraction(sums['eligible_n'],general_n) if foundation!='general' and general_n else None}
            for family,expected in expected_values.items():
                actual=d['values'][family]
                assert actual is None if expected is None else Fraction(Decimal(actual['numerator']))/actual['denominator']==expected
            if sums['epa_n']:
                sign='positive' if exact_epa>0 else 'negative' if exact_epa<0 else 'zero'
                examples.setdefault(sign,dict(observationId=d['observationId'],subject=d['subject'],request=rq))
            # Independently precompute accepted decimal presentation for HTTP/browser proof.
            with localcontext() as ctx:
                ctx.prec=100
                display={}
                for family,decimals,percent in [('epa',3,False),('successRate',1,True),('frequency',1,True)]:
                    value=expected_values[family]
                    display[family]=None if value is None else str((Decimal(value.numerator)/Decimal(value.denominator)*(100 if percent else 1)).quantize(Decimal(1).scaleb(-decimals),rounding=ROUND_HALF_UP))
                    rounding+=int(value is not None)
                dkey=d['observationId']; examples.setdefault('rounded',{})[dkey]=display
        else:
            assert d['totals'] is None and all(v is None for v in d['values'].values())
        assert d['observed']['includedGameIds']==sorted(gid for gid,_ in eligible_members)
        assert d['guarantees']['completeness']['state']=='UNKNOWN'
        assert d['guarantees']['coverage']['expectedCount'] is None
        assert d['guarantees']['temporal']['state']=='UNKNOWN'
        assert d['guarantees']['compatibility']['epaModel']['state']=='UNKNOWN'
    expected={(2026,'REG',tuple(w),t,r,f) for w in ([1],[2],[1,2]) for t in selection['teams'] for r in ('off','def') for f in ('general','classified_pass','classified_rush')}
    assert {k for k in seen if k in expected}==expected and len(expected)==576
    assert categories==dict(individual=384,inclusive=192,retained=12) and len(documents)==588
    old,_=read(source/'bundle')
    retained=[d for d in documents if (d['request']['season'],d['request']['period']['weeks']) in [(2025,[19,20,21,22]),(2026,[3])]]
    assert len(retained)==12
    for d in retained:
        original=next(o for o in old if o['observationId']==d['observationId'])
        assert {k:v for k,v in d.items() if k!='derivedAt'}=={k:v for k,v in original.items() if k!='derivedAt'}
    copy=artifacts.with_name(artifacts.name+'-portable')
    assert not copy.exists(); shutil.copytree(artifacts/'bundle',copy)
    # Fresh reader process denies any filesystem open in original data roots or primary bundle.
    code="""import sys,json
from pathlib import Path
from nfl_sideline_etl.metrics_observations.publication import read
blocked=[Path(p) for p in sys.argv[2:]]
def deny(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  path=Path(args[0]).absolute()
  if any(path==p or p in path.parents for p in blocked): raise RuntimeError('Original root access forbidden')
sys.addaudithook(deny)
d,m=read(Path(sys.argv[1])); print(json.dumps({'count':len(d),'bundleId':m['bundleId']}))
"""
    import os
    env={**os.environ,'PYTHONPATH':str(ROOT/'etl-pipeline/src'),'PYTHONDONTWRITEBYTECODE':'1'}
    result=json.loads(subprocess.check_output([sys.executable,'-B','-c',code,str(copy),str(source),str(backup),str(artifacts/'bundle')],cwd='/private/tmp',env=env))
    assert result==dict(count=588,bundleId=manifest['bundleId']) and hashes(copy)==hashes(artifacts/'bundle')
    config=dict(configVersion='metrics-lab-config-v1',bundles=[dict(dataKind='REAL_ARCHIVE',entryId='w12-expansion-v1',
        expectedBundleId=manifest['bundleId'],label='Arquivo 2026 W1–2 · 32 times; NE POST2025; lacuna BAL W3',path=str(artifacts/'bundle'))])
    save(artifacts/'lab-config.json',config)
    report=dict(kind='REAL_ARCHIVE_INDEPENDENT_RAW_LEDGER',games=32,teams=32,documents=len(documents),categories=dict(categories),
        originalGroupsFromRaw=original_groups,memberGroupsReconciled=member_count,roundedValuesChecked=rounding,
        source=manifest['source'],bundleId=manifest['bundleId'],bundlePath=str(artifacts/'bundle'),portablePath=str(copy),
        portableFreshReaderWithOriginalRootsDenied=result,bundleHashes=hashes(artifacts/'bundle'),
        rawFileHashes={p.name:auditor.sha(p) for p in paths.values()},preservedCopiesUnchanged=True,
        retainedLegacyDocumentsSameSemanticIdentity=12,activeUniqueScopes=588,expectationDifference=0,
        overlapPolicy='Sum distinct original games only within one nominal observation; never sum observations; raw Fraction ledger independent of projector.',
        sampleMissingEpa=sum(s['epa_missing_n'] for (g,t,r,f),s in led['statistics'].items() if g in games and r=='off' and f=='general'),
        unknown=['completeness','coverageExpectation','epaModel','historicalAvailability','historicalIngestion','eventFinal'],
        humanAcceptance='PENDING')
    assert hashes(source)==before==hashes(backup)
    save(artifacts/'reconciliation.json',report); save(artifacts/'examples.json',examples)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifacts',type=Path,required=True)
    run(p.parse_args().artifacts)
