"""Offline v2 workflow; public acquisition lives in prepare.py."""
import argparse,socket
from experiment import run

def no_network(*a,**k):raise RuntimeError('Network disabled during research reproduction')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--out',required=True);a=p.parse_args();socket.socket.connect=no_network;socket.create_connection=no_network;run(a.store,a.out)
