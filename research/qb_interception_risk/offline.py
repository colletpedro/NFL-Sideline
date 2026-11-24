"""Run the complete pipeline with Python network connections explicitly refused."""
import socket
import pipeline

def deny_network(*args,**kwargs):
 raise RuntimeError('Network disabled during offline reproduction')
socket.socket.connect=deny_network
socket.create_connection=deny_network
if __name__=='__main__': pipeline.main()
