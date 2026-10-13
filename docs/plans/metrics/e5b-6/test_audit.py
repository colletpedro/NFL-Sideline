"""Synthetic counterexamples for independent auditor; never substitute real proof."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
import pytest
import polars as pl
sys.path.insert(0,str(Path(__file__).parent))
from audit import ledger, compare, summary
from nfl_sideline_etl.offline_metrics.artifact import calculate
from nfl_sideline_etl.offline_metrics.inputs import read_inputs

FIXTURE=Path(__file__).resolve().parents[4]/'etl-pipeline/tests/fixtures/offline_metrics'


def sources(tmp_path):
    paths=[]
    for kind in ('calendar','pbp'):
        rows=json.loads((FIXTURE/(kind+'.json')).read_text())['rows']
        path=tmp_path/(kind+'.parquet');pl.DataFrame(rows).write_parquet(path);paths.append(path)
    return paths


def test_exact_missing_nonfinite_and_replicas(tmp_path):
    c,p=sources(tmp_path);led=ledger([c],[p]);summ=summary(led)
    assert (summ['pbp_raw_n'],summ['pbp_unique_n'],summ['duplicate_rows_ignored'])==(27,26,1)
    assert summ['missing_epa_n']>0 and summ['nonfinite_epa_n']>0
    rows,plays,descriptors=read_inputs([c],[p]);result=calculate(rows,plays,descriptors,seasons=(2026,))
    compare(led,result['game-audit.json'],result['statistics.json'],result['manifest.json'])
    modified=deepcopy(result['statistics.json']);modified[0]['eligible_n']+=1
    with pytest.raises(AssertionError):compare(led,result['game-audit.json'],modified,result['manifest.json'])


@pytest.mark.parametrize('column,value',[('drive',9876),('epa',9876),('posteam','WRONG')])
def test_conflicting_replica_is_not_hidden_by_exclusion(tmp_path,column,value):
    c,p=sources(tmp_path);frame=pl.read_parquet(p);r=frame.to_dicts()[0];r[column]=value
    extra=tmp_path/'extra.parquet';pl.DataFrame([r],schema=frame.schema).write_parquet(extra)
    with pytest.raises(ValueError):ledger([c],[p,extra])


def test_fraction_is_exact_under_low_decimal_precision(tmp_path):
    from decimal import localcontext
    c,p=sources(tmp_path)
    with localcontext() as ctx:
        ctx.prec=4
        low=ledger([c],[p])
    high=ledger([c],[p])
    assert low==high
    assert all(isinstance(s['epa_sum'],Fraction) for s in low['statistics'].values())


def test_unobserved_calendar_has_no_zero_groups(tmp_path):
    c,p=sources(tmp_path);led=ledger([c],[p])
    gid='synthetic-5'
    assert led['audits'][gid]['eligible_content_n'] is None
    assert not any(k[0]==gid for k in led['statistics'])


def test_double_partition_preserves_content_but_counts_replicas(tmp_path):
    c,p=sources(tmp_path);one=ledger([c],[p]);two=ledger([c],[p,p])
    assert one['statistics']==two['statistics']
    for gid,a in one['audits'].items():assert a['pbp_content_id']==two['audits'][gid]['pbp_content_id']
    assert summary(two)['pbp_raw_n']==2*summary(one)['pbp_raw_n']
