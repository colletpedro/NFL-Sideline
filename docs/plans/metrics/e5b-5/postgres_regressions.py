"""Run accepted E5b-2 SQL regressions in a separate NEW own disposable cluster.

The historical suite truncates its test relations between tests. It never runs
against the integration proof's database or any historical/global instance.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('own_instance',ROOT/'docs/plans/metrics/e5b-2/instance.py')
instance=importlib.util.module_from_spec(spec);spec.loader.exec_module(instance)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('root','pg-bin','output'):parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.root.exists():parser.error('New output/root required')
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    marker=instance.start(args.root,args.pg_bin,port)
    report={'scope':'REAL_OWN_POSTGRESQL_E5B2_REGRESSIONS','instance':marker,
            'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    try:
        result=subprocess.run([sys.executable,'-B','-m','pytest','docs/plans/metrics/e5b-2/postgres_tests','-q',
            '-p','no:cacheprovider','--e5b2-instance-root',str(args.root)],cwd=ROOT,capture_output=True,text=True,timeout=120)
        (args.root/'regressions.log').write_text(result.stdout+result.stderr)
        report['returncode']=result.returncode;report['log']=result.stdout+result.stderr
        assert result.returncode==0,report['log']
    finally:
        instance.stop(args.root,args.pg_bin)
        result=subprocess.run([str(args.pg_bin/'pg_ctl'),'-D',str(args.root/'data'),'status'],capture_output=True)
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        report['shutdown']={'pgCtlStatus':result.returncode,'pidAbsent':not (args.root/'data/postmaster.pid').exists(),'portBindReleased':True}
        with args.output.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
        assert result.returncode==3 and report['shutdown']['pidAbsent']
    print(json.dumps({'returncode':report['returncode'],'port':port,'shutdown':report['shutdown']}))


if __name__=='__main__':main()
