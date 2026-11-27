"""Client for the cluster's Gemma 4 31B (vLLM, OpenAI-compatible API), and a scripted stand-in."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

URL = "http://gemma-4-31b.cpd-instance.svc:3000/v1/chat/completions"
MODEL = "google/gemma-4-31b"


@dataclass
class LLMReply:
    answer: str = ""
    reasoning: str = ""
    seconds: float = 0.0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    finish: Optional[str] = None
    error: Optional[str] = None


def _requests_post(url, json, timeout):   # imported lazily: only needed for real calls
    import requests
    return requests.post(url, json=json, timeout=timeout)


class _HTTPError(Exception):
    def __init__(self, status: int, text: str):
        super().__init__(f"HTTP {status}: {text[:300]}")
        self.status = status


class GemmaClient:
    def __init__(self, url: str = URL, model: str = MODEL, timeout: float = 900, retries: int = 3,
                 backoff: float = 10.0, post: Callable = _requests_post, sleep: Callable = time.sleep):
        self.url, self.model, self.timeout = url, model, timeout
        self.retries, self.backoff = max(1, retries), backoff
        self.post, self.sleep = post, sleep

    def ask(self, messages: List[dict], think: bool, max_tokens: Optional[int] = None,
            temperature: Optional[float] = None) -> LLMReply:
        """Never raises: on repeated failure the reply carries `error`."""
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or (16384 if think else 2048),
            "temperature": temperature if temperature is not None else (1.0 if think else 0.3),
            "chat_template_kwargs": {"enable_thinking": bool(think)},
        }
        t = time.time()
        last = ""
        for attempt in range(1, self.retries + 1):
            try:
                r = self.post(self.url, json=body, timeout=self.timeout)
                status = getattr(r, "status_code", 200)
                if status >= 400:
                    text = getattr(r, "text", "") or ""
                    raise _HTTPError(status, text if isinstance(text, str) else "")
                out = r.json()
                choice = out["choices"][0]
                msg = choice.get("message") or {}
                usage = out.get("usage") or {}
                details = usage.get("completion_tokens_details") or {}
                return LLMReply(
                    answer=(msg.get("content") or "").strip(),
                    reasoning=msg.get("reasoning") or msg.get("reasoning_content") or "",
                    seconds=round(time.time() - t, 1),
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    reasoning_tokens=details.get("reasoning_tokens"),
                    finish=choice.get("finish_reason"),
                )
            except _HTTPError as e:
                last = str(e)
                if e.status < 500:
                    break
            except Exception as e:   # connection errors, timeouts, malformed bodies
                last = f"{type(e).__name__}: {e}"
            if attempt < self.retries:
                self.sleep(self.backoff * attempt)
        return LLMReply(seconds=round(time.time() - t, 1), error=last or "unknown error")


class ScriptedLLM:
    """Returns pre-written replies in order (repeating the last). For tests and --fake dry runs."""

    def __init__(self, replies: list):
        self.replies = list(replies)
        self.received: List[List[dict]] = []
        self._i = 0

    def ask(self, messages: List[dict], think: bool, max_tokens: Optional[int] = None,
            temperature: Optional[float] = None) -> LLMReply:
        self.received.append(list(messages))
        r = self.replies[min(self._i, len(self.replies) - 1)]
        self._i += 1
        if isinstance(r, LLMReply):
            return r
        return LLMReply(answer=str(r), seconds=0.0, prompt_tokens=100, completion_tokens=50,
                        reasoning_tokens=None, finish="stop")


def json_from(text: str) -> Optional[dict]:
    """The circuit JSON in a reply: a fenced ```json block first, else the first object containing
    "components", else the first JSON object. None if there is none."""
    if not text:
        return None
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S):
        try:
            d = json.loads(m.group(1))
            if isinstance(d, dict):
                return d
        except ValueError:
            pass
    dec = json.JSONDecoder()
    first = None
    for m in re.finditer(r"\{", text):
        try:
            d, _end = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(d, dict):
            if "components" in d:
                return d
            if first is None:
                first = d
    return first
