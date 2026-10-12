"""Reproducible fresh fixture construction, no database/network or historical archive."""
from copy import deepcopy
from pathlib import Path

from nfl_sideline_etl.offline_metrics.artifact import calculate, write_artifact, identity
from nfl_sideline_etl.offline_metrics.inputs import read_inputs, load_json
from nfl_sideline_etl.metrics_persistence.archive import Archive
from nfl_sideline_etl.metrics_persistence.plan import prepare
from nfl_sideline_etl.metrics_materialization import RELATIONS_VERSION
from nfl_sideline_etl.metrics_materialization.relations import records, TABLES
from nfl_sideline_etl.metrics_materialization.recovery import recover

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / 'etl-pipeline/tests/fixtures/metrics_materialization'


def build(root, *, multi=False, empty=False, archive=None):
    root = Path(root); root.mkdir(parents=True, exist_ok=False)
    calendars = [FIXTURE/'calendar.json']
    pbps = [FIXTURE/'pbp-empty.json'] if empty else [FIXTURE/'pbp-a.json', FIXTURE/'pbp-b.json', FIXTURE/'pbp-a.json']
    inputs = read_inputs(calendars, pbps)
    metadata = None
    if empty or multi:
        metadata = {'metadataVersion':1, 'calendar_sha256':sorted({d['sha256'] for d in inputs[2] if d['kind']=='calendar'}),
                    'pbp_sha256':sorted({d['sha256'] for d in inputs[2] if d['kind']=='pbp'}),
                    'games':{'synthetic-6':{'completeness':'COMPLETE','expected_unique_rows':0,
                                          'evidence':{'basis':'SYNTHETIC_FIXTURE','reference':'fixture-ledger'}}}}
    result = calculate(*inputs, metadata, seasons=(2026,))
    write_artifact(root/'artifact', result)
    archive = archive or Archive(root/'archive')
    plan = prepare(root/'artifact', calendars, pbps, archive.root)
    rows = records(plan)
    all_bytes = {sha:(data,{'type':'explicit_source',**origin}) for sha,(data,origin) in plan.source_bytes.items()}
    all_bytes.update({plan.file_hashes[n]:(data,{'type':'artifact_file','filename':n,'artifact_id':plan.artifact_id})
                      for n,data in plan.artifact_bytes.items()})
    for sha,(data,origin) in sorted(all_bytes.items()):
        receipt = archive.put(data, sha, origin)
        rows['metric_archive_receipt'].append({**{k:receipt[k] for k in
            ('receipt_id','sha256','archive_id','archive_root','locator','observed_at')},'receipt_json':receipt})
    for table in ('metric_archive_blob','metric_calculation','metric_archive_receipt'):
        for row in rows[table]:row['persisted_at']='2026-10-11T12:00:00+00:00'
    choice = {'calculation_id':result['manifest.json']['calculation_id'],'artifact_id':plan.artifact_id,'archive_id':archive.archive_id}
    package={'relationsVersion':RELATIONS_VERSION,'selection':[choice],'relations':rows}
    return package, recover(package,{archive.archive_id:str(archive.root)}), plan, archive


def merge(packages):
    merged = {'relationsVersion':RELATIONS_VERSION,'selection':[], 'relations':{t:[] for t in TABLES}}
    for p in packages:
        merged['selection'].extend(p['selection'])
        for t,rows in p['relations'].items():
            for row in rows:
                # SQL persistence times are not equality keys for shared immutable records.
                if row not in merged['relations'][t]:merged['relations'][t].append(deepcopy(row))
    return merged


def auxiliary(plans):
    """Synthetic statements, consciously trusted by the fixture; not real historical evidence."""
    aux = load_json((FIXTURE/'auxiliary-empty.json').read_bytes())
    aux['policy']['trustedOrigins']=['synthetic-e5b4']
    docid = identity({'syntheticDocument':'e5b4-calendar-state-and-completeness-v1'})
    aux['resources'].append({'revision_id':docid,'kind':'METADATA','dependencies':[],
        'available_at':None,'ingested_at':None,'payload':{'origin':'synthetic-e5b4',
        'document':{'documentVersion':'metrics-auxiliary-document-v1','origin':'synthetic-e5b4','received_at':'2026-10-11T12:00:00Z',
                    'reference':'versioned-fixture-ledger','content':{'assertion':'Synthetic calendar/states/completeness; not authenticated'}}}})
    def proof(kind,subject,value):
        e={'kind':kind,'subject_id':subject,'origin':'synthetic-e5b4','reference':'versioned-fixture-ledger',
           'recorded_at':'2026-10-11T12:00:00.000000000001Z','value':value,'dependencies':[docid]}
        e['evidence_id']=identity(e);aux['evidence'].append(e)
        return {'value':value,'evidence_id':e['evidence_id']}
    seen=set()
    for plan in plans:
        m=plan.result['manifest.json']; audits=plan.result['game-audit.json']; sid=audits[0]['calendar_revision_id']
        calid=identity({'syntheticFrozenCalendar':sid,'document':docid})
        if calid not in seen:
            seen.add(calid)
            games=[{k:a[k] for k in ('game_id','season','phase','round','week','home_team','away_team')} for a in audits]
            aux['resources'].append({'revision_id':calid,'kind':'CALENDAR','dependencies':[sid,docid],
                'available_at':None,'ingested_at':None,'payload':{'season':2026,'phase':'REG','games':games,
                'complete':proof('CALENDAR_COMPLETE',calid,True),'closed_weeks':[]}})
            for g in games:
                stateid=identity({'stateGame':g['game_id'],'calendar':calid,'document':docid})
                aux['resources'].append({'revision_id':stateid,'kind':'STATE','dependencies':[calid,docid],
                    'available_at':None,'ingested_at':None,'payload':{'game_id':g['game_id'],'calendar_revision_id':calid,
                    'status':'FINAL','event_upper_bound':proof('EVENT_END_BOUND',stateid,'2026-09-28T11:59:59.999999999999Z'),
                    'event_lower_bound':None,'kickoff':None}})
        completeness={a['coverage_revision_id']:proof('PBP_COMPLETE',a['coverage_revision_id'],a['completeness'])
                      for a in audits if a['statistics_status']!='SOURCE_UNKNOWN'}
        aux['bindings'].append({'calculation_id':m['calculation_id'],'calendars':{'2026/REG':calid},
            'metadata_revision_ids':[docid],'completeness':completeness,'model':None,
            'source_models':{d['source_revision_id']:None for d in plan.sets['pbp']}})
    return aux
