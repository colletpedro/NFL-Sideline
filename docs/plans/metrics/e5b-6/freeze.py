"""Inventory only the project data root recorded by previous audits; freeze copies."""
import argparse
import json
from pathlib import Path
import shutil
from audit import encoded, parquet, sha

ROOT=Path(__file__).resolve().parents[4]


def freeze(source, workspace):
    previous=json.loads((ROOT/'contracts/metrics/e5a-v1/local-audit.json').read_text())
    # Discovery never extends to a personal directory or an arbitrary supplied path.
    if source.resolve()!=Path(previous['sourceRoot']).resolve() and source.resolve()!=ROOT/'etl-pipeline/data/raw':
        raise ValueError('Source must be project raw data root explicitly recorded in E5a')
    if workspace.exists():raise FileExistsError(workspace)
    workspace.mkdir(parents=True)
    entries=[]
    for path in sorted(source.rglob('*.parquet')):
        kind='pbp' if 'pbp' in path.relative_to(source).parts else 'calendar'
        try:
            frame=parquet(path)
        except Exception as exc:
            entries.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,status='INVALID_PARQUET',error_type=type(exc).__name__))
            (workspace/'inventory-failed.json').write_bytes(encoded(dict(files=entries,status='INVALID_PARQUET',executionAuthorized=False)))
            raise
        old=[f['sha256'] for f in previous['files'] if f['path']==str(path)]
        ids=sorted(frame['game_id'].drop_nulls().unique().to_list())
        teams=sorted({t for k in ('posteam','defteam','home_team','away_team') if k in frame.columns for t in frame[k].drop_nulls().unique().to_list()})
        seasons=sorted(frame['season'].unique().to_list());phase_col='season_type' if kind=='pbp' else 'game_type'
        entries.append(dict(path=str(path),relative=str(path.relative_to(source)),kind=kind,format='parquet',sha256=sha(path),
            bytes=path.stat().st_size,rows=frame.height,schema={k:str(v) for k,v in frame.schema.items()},seasons=seasons,
            phases=sorted(frame[phase_col].unique().to_list()),weeks=sorted(frame['week'].unique().to_list()),
            game_ids=ids,games_n=len(ids),participants=teams,prior_sha256=old,prior_bytes_match=sha(path) in old if old else None,
            selected=any(f'season={s}' in path.relative_to(source).parts for s in (2025,2026)),origin_declared='nflverse via nflreadpy (prior project audits)',
            historical_available_at=None,historical_ingested_at=None,event_end=None,epa_model='UNKNOWN',completeness='UNKNOWN'))
    (workspace/'inventory-before-selection.json').write_bytes(encoded(dict(files=entries,executionAuthorized=False)))
    chosen=[e for e in entries if e['selected']]
    if any(e['seasons'] not in ([2025],[2026]) for e in chosen):raise ValueError('Invalid or mixed season in selected partition; no silent omission')
    if len(chosen)>8 or sum(e['bytes'] for e in chosen)>256*1024*1024 or sum(e['rows'] for e in chosen if e['kind']=='pbp')>150000 or sum(e['games_n'] for e in chosen if e['kind']=='calendar')>1000:
        raise ValueError('Protocol volume cap exceeded')
    seasons={}
    for season in (2025,2026):
        c=[e for e in chosen if e['seasons']==[season] and e['kind']=='calendar']
        p=[e for e in chosen if e['seasons']==[season] and e['kind']=='pbp']
        if len(c)!=1 or c[0]['relative']!=f'schedules/season={season}/schedules.parquet' or not p:
            raise ValueError(f'Insufficient/canonical inputs season {season}; inventory cannot authorize load')
        seasons[str(season)]={k:[str(workspace/'data/raw'/e['relative']) for e in selected] for k,selected in [('calendar',c),('pbp',p)]}|{'metadata':None}
    for e in chosen:
        destination=workspace/'data/raw'/e['relative'];destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(e['path'],destination)
        assert sha(destination)==e['sha256']==sha(e['path'])
        destination.chmod(0o444)
        e['frozen_path']=str(destination)
    overlap=[]
    for i,a in enumerate(entries):
        for b in entries[i+1:]:
            if a['kind']==b['kind'] and set(a['seasons'])&set(b['seasons']):
                overlap.append(dict(left=a['relative'],right=b['relative'],common_games_n=len(set(a['game_ids'])&set(b['game_ids'])),
                                    limitation='game overlap only; contractual key/projection checked independently before load'))
    report=dict(inventoryVersion='metrics-backfill-inventory-v1',sourceRoot=str(source),workspace=str(workspace),files=entries,
                selectedSeasons=[2025,2026],partitionOverlaps=overlap,excludedSeasons=[2023],
                noAdditionalRealRevisions=len(entries)==6 and all(e['prior_bytes_match'] is True for e in entries),
                acquisition=False,archivesCopied=False,bytesSelected=sum(e['bytes'] for e in chosen),
                criteria='PROTOCOL.md; all observed partitions of selected seasons, no game/week/EPA selection')
    (workspace/'inventory.json').write_bytes(encoded(report));(workspace/'inputs.json').write_bytes(encoded(dict(inputsVersion=1,seasons=seasons)))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args();r=freeze(args.source_root,args.workspace)
    print(json.dumps(dict(files=len(r['files']),selectedBytes=r['bytesSelected'],workspace=r['workspace'])))
