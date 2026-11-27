import unittest

from piezo_synth.llm import GemmaClient, LLMReply, ScriptedLLM, json_from


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


BODY = {"choices": [{"finish_reason": "stop",
                     "message": {"content": " {\"a\": 1} ", "reasoning": "thought hard"}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 800,
                  "completion_tokens_details": {"reasoning_tokens": 650}}}


def post_returning(calls, status=200, body=BODY, exc=None):
    def post(url, json, timeout):
        calls.append(json)
        if exc:
            raise exc
        return _Resp(status, body)
    return post


class LLMTest(unittest.TestCase):
    def test_ask_parses_usage_and_reasoning(self):
        calls = []
        r = GemmaClient(post=post_returning(calls)).ask([{"role": "user", "content": "x"}], think=True)
        self.assertEqual((r.prompt_tokens, r.completion_tokens, r.reasoning_tokens), (120, 800, 650))
        self.assertEqual(r.reasoning, "thought hard")
        self.assertEqual(r.answer, '{"a": 1}')
        self.assertIsNone(r.error)
        self.assertTrue(calls[0]["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(calls[0]["max_tokens"], 16384)
        self.assertEqual(calls[0]["model"], "google/gemma-4-31b")

    def test_ask_retries_then_reports_error(self):
        calls, sleeps = [], []
        c = GemmaClient(post=post_returning(calls, status=503), sleep=sleeps.append)
        r = c.ask([{"role": "user", "content": "x"}], think=True)
        self.assertTrue(r.error)
        self.assertEqual(len(calls), 3)
        self.assertEqual(r.answer, "")
        self.assertEqual(len(sleeps), 2)

    def test_connection_error_retried(self):
        calls = []
        r = GemmaClient(post=post_returning(calls, exc=ConnectionError("down")), sleep=lambda s: None).ask(
            [{"role": "user", "content": "x"}], think=False)
        self.assertEqual(len(calls), 3)
        self.assertIn("down", r.error)

    def test_read_timeout_not_retried(self):
        class ReadTimeout(Exception):
            pass
        calls = []
        r = GemmaClient(post=post_returning(calls, exc=ReadTimeout("read timed out")), sleep=lambda s: None).ask(
            [{"role": "user", "content": "x"}], think=True)
        self.assertEqual(len(calls), 1)
        self.assertIn("ReadTimeout", r.error)

    def test_timeout_override(self):
        seen = []

        def post(url, json, timeout):
            seen.append(timeout)
            return _Resp(200, BODY)
        GemmaClient(post=post, timeout=900).ask([{"role": "user", "content": "x"}], think=True, timeout=42)
        self.assertEqual(seen, [42])

    def test_4xx_not_retried(self):
        calls = []
        r = GemmaClient(post=post_returning(calls, status=400), sleep=lambda s: None).ask(
            [{"role": "user", "content": "x"}], think=False)
        self.assertEqual(len(calls), 1)
        self.assertTrue(r.error)

    def test_json_from_fenced_and_nested(self):
        self.assertEqual(json_from('blah ```json\n{"components": [{"id": "R1"}]}\n``` x')["components"][0]["id"], "R1")
        self.assertEqual(json_from('text {"a": {"b": 1}} {"components": []}'), {"components": []})
        self.assertEqual(json_from('only {"a": {"b": 1}} here'), {"a": {"b": 1}})
        self.assertIsNone(json_from("no json"))
        self.assertIsNone(json_from(""))

    def test_scripted_llm(self):
        s = ScriptedLLM(["one", LLMReply(error="503")])
        self.assertEqual(s.ask([{"role": "user", "content": "a"}], think=True).answer, "one")
        self.assertEqual(s.ask([], think=True).error, "503")
        self.assertEqual(s.ask([], think=True).error, "503")     # repeats the last
        self.assertEqual(len(s.received), 3)


if __name__ == "__main__":
    unittest.main()
