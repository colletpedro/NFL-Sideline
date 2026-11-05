"""Explicit update: acquire own revision -> fixed rules -> package; never activate."""
import argparse
from common import *
from acquire import prepare
from run import build,fixed_spec
from figures import generate
from verify import verify_package
from reconcile import reconcile

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);a.add_argument('--fixed',required=True);a.add_argument('--source',default=str(PREVIOUS));a.add_argument('--frozen-sources');a.add_argument('--previous');a.add_argument('--season',type=int,default=2026);v=a.parse_args()
 if read(v.fixed)!=fixed_spec():raise ValueError('Fixed classification/metric code or contract differs')
 out=new(v.out)
 sources=Path(v.frozen_sources) if v.frozen_sources else prepare(out/'sources',v.source,True,v.season)
 build(sources,out/'package',v.previous)
 generate(out/'package')
 write(out/'verification.json',verify_package(out/'package'))
 reconcile(sources,out/'package',out/'independent-reconciliation.json')
