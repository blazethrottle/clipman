from app import processes
from app.jobs.manager import JobManager


def test_exited_parent_does_not_hide_its_owned_posix_group(monkeypatch):
    events = []
    monkeypatch.setattr(processes, 'WINDOWS', False)
    monkeypatch.setattr(processes.os, 'killpg', lambda pid, sig: events.append((pid, sig)), raising=False)
    proc = processes.OwnedProcess.__new__(processes.OwnedProcess)
    proc._child_created = False
    proc.pid = 12345
    proc.poll = lambda: 0
    JobManager._stop(proc)
    assert events == [(12345, 9)]


def test_parent_wait_success_still_kills_remaining_posix_children(monkeypatch):
    events = []
    monkeypatch.setattr(processes, 'WINDOWS', False)
    monkeypatch.setattr(processes.os, 'killpg', lambda pid, sig: events.append((pid, sig)), raising=False)
    proc = processes.OwnedProcess.__new__(processes.OwnedProcess)
    proc._child_created = False
    proc.pid = 12345
    state = {'alive': True}
    proc.poll = lambda: None if state['alive'] else 0
    def wait(timeout):
        state['alive'] = False
        return 0
    proc.wait = wait
    JobManager._stop(proc)
    assert events[0] == (12345, processes.signal.SIGTERM)
    assert events[-1] == (12345, 9)
