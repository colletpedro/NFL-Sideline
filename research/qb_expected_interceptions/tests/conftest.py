from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest

@pytest.fixture(autouse=True)
def prohibit_test_downloads(monkeypatch):
    import socket
    def denied(*args,**kwargs):raise AssertionError('Tests must remain offline')
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(socket,'create_connection',denied)
