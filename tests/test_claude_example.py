"""The Claude-only example, run against a fake client (no network, no key)."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(__file__))


def _load(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("claude_only", os.path.join(ROOT, "examples", "claude_only.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


class Fake:
    def __init__(self):
        self.calls, self.batches = [], []
        fake = self
        class Msgs:
            def create(self, **kw):
                fake.calls.append(kw)
                return type("M", (), {"content": [type("C", (), {"text": "ok"})()]})()
            class batches:
                @staticmethod
                def create(requests):
                    fake.batches.append(requests); return type("B", (), {"id": "b1"})()
        self.messages = Msgs()


def test_easy_question_goes_to_haiku_hard_to_opus(tmp_path, monkeypatch):
    m, c = _load(tmp_path, monkeypatch), Fake()
    m.ask(c, "Translate 'good morning' into Hindi")
    m.ask(c, "Prove this theorem about prime numbers")
    assert [x["model"] for x in c.calls] == ["claude-haiku-5-5", "claude-opus-5-5"]


def test_can_wait_requests_go_out_as_one_batch_at_the_clean_hour(tmp_path, monkeypatch):
    m, c = _load(tmp_path, monkeypatch), Fake()
    slept = []
    m.ask_later(c, ["Summarise these notes", "Prove this theorem"], forecast=[300, 200, 60, 250],
                sleep=slept.append)
    assert len(c.batches) == 1 and len(c.batches[0]) == 2
    assert slept == [2 * 0.5 * 3600]                # waited for slot 2, the cleanest
