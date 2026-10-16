from app.capture import Selection
from app.jobs.manager import JobManager, JobStatus
from app.services import engine as engine_module
from app.services.engine import Engine, ProcessingError
from app.wrappers import ytdlp
from app.wrappers.ffprobe import SourceMeta


def _engine(tmp_path, outcomes):
    """yt-dlp 실행 결과를 outcomes 순서대로 흉내 낸다. 'ok'는 source.mp4를 만든다."""
    engine = Engine(JobManager(tmp_path / 'work'), tmp_path / 'output')
    calls = []

    def fake_run(job_id, generation, args, parser=None):
        outcome = outcomes[len(calls)]
        calls.append(args)
        work = engine.manager.get(job_id).work_dir
        if outcome == 'ok':
            (work / 'source.mp4').write_bytes(b'video')
            return ''
        (work / 'source.f401.mp4.part').write_bytes(b'partial')
        raise ProcessingError(outcome, engine_module.ERROR_MESSAGES.get(outcome, '실패'))

    engine._run = fake_run
    engine._probe = lambda job_id, generation, source: SourceMeta(1920, 1080, 2.0, True)
    return engine, calls


def _acquire(engine):
    job = engine.manager.create(Selection('aqz-KE-bpKQ', 'https://youtu.be/aqz-KE-bpKQ', 10, 12))
    generation = engine.manager.begin_download(job.job_id)
    engine._acquire(job.job_id, generation)
    return engine.manager.get(job.job_id)


def test_transient_403_is_retried_once_and_partial_files_are_removed(tmp_path):
    engine, calls = _engine(tmp_path, ['HTTP_403', 'ok'])
    job = _acquire(engine)
    assert job.status == JobStatus.DOWNLOADED
    assert len(calls) == 2
    assert sorted(p.name for p in job.work_dir.iterdir()) == ['source.mp4']


def test_repeated_403_fails_with_retry_message(tmp_path):
    engine, calls = _engine(tmp_path, ['HTTP_403', 'HTTP_403'])
    job = _acquire(engine)
    assert len(calls) == 2
    assert job.status == JobStatus.ERROR
    assert job.error_code == 'HTTP_403'
    assert '잠시 후' in job.message


def test_other_errors_are_not_retried(tmp_path):
    engine, calls = _engine(tmp_path, ['BOT_BLOCK'])
    job = _acquire(engine)
    assert len(calls) == 1
    assert job.status == JobStatus.ERROR


def test_classify_googlevideo_403():
    text = ('[https @ 0x1] HTTP error 403 Forbidden\n'
            'Error opening input: Server returned 403 Forbidden (access denied)\n'
            'ERROR: ffmpeg exited with code 8')
    assert ytdlp.classify_error(text) == 'HTTP_403'


def test_engine_message_for_403_is_user_actionable():
    assert '잠시 후' in engine_module.ERROR_MESSAGES['HTTP_403']
