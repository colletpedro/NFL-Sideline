"""Rebuild all deliverables in a NEW destination with network entry points disabled."""
import argparse,socket,urllib.request
from common import *
from run import build,fixed_spec
from figures import generate
from verify import verify_package,compare
from reconcile import reconcile

def no_network(*a,**kw):raise RuntimeError('Offline reproduction cannot use network')

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--sources',required=True);a.add_argument('--out',required=True);a.add_argument('--reference',required=True);a.add_argument('--receipt',required=True);v=a.parse_args()
 socket.create_connection=no_network;urllib.request.urlopen=no_network
 if read(Path(v.reference)/'fixed.json')!=fixed_spec():raise ValueError('Fixed code/contract mismatch')
 build(v.sources,v.out);generate(v.out);r=verify_package(v.out);r['comparison']=compare(v.reference,v.out)
 r['independent_reconciliation']=reconcile(v.sources,v.out,Path(v.receipt).with_suffix('.sql.json'))
 r['network_disabled']=True;write(v.receipt,r);print(r)
