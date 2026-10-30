"""capture_addon.py -- mitmproxy addon: the capture layer of the revised architecture.

Replaces the LittleProxy-based capture layer of the walking skeleton, which could
not intercept modern conversational interfaces because it supports neither HTTP/2
nor WebSocket.  This addon does three things and nothing else, so that it stays
small enough to replace again when providers change their wire format:

  1. match the request URL against an allow-list;
  2. extract the *user's own text* from the request body, rather than storing the
     whole body -- data minimisation applied at the point of capture;
  3. append one JSON object per prompt to a JSON Lines file.

Everything downstream -- pseudonymisation policy, classification, PEQI, the
analytic dataset -- lives in the Java application layer, which tails that file.
The file is the interface: it survives a crash on either side, it can be replayed
when the derived measures change, and a school can read it without any tooling.

Responses are NOT stored verbatim.  Only a digest and a length are recorded,
which is enough to compute the verbatim-transfer ratio against the pupil's
submitted answer without keeping the model's output.

Run:
    mitmdump -s mitm/capture_addon.py \
        --set study_config=config/study.yaml \
        --set session=2026-10-07-2A-P1 \
        --listen-host 127.0.0.1 --listen-port 8080
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrub import Scrubber  # noqa: E402

try:
    import yaml
except ImportError:  # mitmproxy ships without pyyaml in some installs
    yaml = None

from mitmproxy import ctx, http


# --------------------------------------------------------------------------
# Provider-specific extraction of the user's text.
#
# Each entry is (url fragment, extractor).  An extractor receives the parsed
# JSON body and returns the newest user-authored message, or None.  Keeping
# these separate and tiny is deliberate: when a provider changes its payload,
# exactly one function here breaks, and the allow-list plus everything
# downstream keeps working.
# --------------------------------------------------------------------------
def _openai(body: dict) -> str | None:
    msgs = body.get("messages") or []
    for m in reversed(msgs):
        if m.get("author", {}).get("role") == "user" or m.get("role") == "user":
            content = m.get("content")
            if isinstance(content, dict):
                parts = content.get("parts") or []
                return "\n".join(p for p in parts if isinstance(p, str))
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
    return None


def _anthropic(body: dict) -> str | None:
    if isinstance(body.get("prompt"), str):
        return body["prompt"]
    msgs = body.get("messages") or []
    for m in reversed(msgs):
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return "\n".join(p.get("text", "") for p in c if isinstance(p, dict))
    return None


def _google(body: dict) -> str | None:
    contents = body.get("contents") or []
    for c in reversed(contents):
        if c.get("role") in (None, "user"):
            parts = c.get("parts") or []
            return "\n".join(p.get("text", "") for p in parts if isinstance(p, dict))
    return None


def _study_client(body: dict) -> str | None:
    """Our own exercise client posts a flat, documented shape."""
    return body.get("prompt") or body.get("text")


EXTRACTORS: list[tuple[str, callable]] = [
    ("chatgpt.com", _openai),
    ("openai.com", _openai),
    ("claude.ai", _anthropic),
    ("anthropic.com", _anthropic),
    ("gemini.google.com", _google),
    ("generativelanguage.googleapis.com", _google),
    ("localhost", _study_client),
    ("127.0.0.1", _study_client),
]

GENERIC_KEYS = ("prompt", "text", "input", "query", "message", "question")


def extract_prompt(url: str, body: dict) -> str | None:
    for fragment, fn in EXTRACTORS:
        if fragment in url:
            got = fn(body)
            if got:
                return got.strip()
    # last resort: a single obvious top-level string field
    for k in GENERIC_KEYS:
        v = body.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


# --------------------------------------------------------------------------
class PromptCapture:
    """The addon itself."""

    def __init__(self) -> None:
        self.patterns: list[re.Pattern] = []
        self.out_path: Path | None = None
        self.scrubber = Scrubber([])
        self.session = "unset"
        self.pseudonym = "unset"
        self.condition = "unset"
        self.period = 0
        self.max_chars = 8000
        self.store_response_digest = True
        self.n_seen = 0
        self.n_captured = 0
        self.n_skipped_no_prompt = 0

    # ---- mitmproxy lifecycle ---------------------------------------------
    def load(self, loader) -> None:
        loader.add_option("study_config", str, "config/study.yaml",
                          "Path to the study YAML configuration.")
        loader.add_option("session", str, "",
                          "Session id: <date>-<class>-<period>, e.g. 2026-10-07-2A-P1.")
        loader.add_option("student", str, "",
                          "Opaque per-device student code assigned by the school.")

    def configure(self, updates) -> None:
        if "study_config" in updates or not self.patterns:
            self._load_config(Path(ctx.options.study_config))
        if ctx.options.session:
            self.session = ctx.options.session
        if ctx.options.student:
            self.pseudonym = self._pseudonymise(ctx.options.student)

    def done(self) -> None:
        ctx.log.info(
            f"[capture] seen={self.n_seen} captured={self.n_captured} "
            f"skipped_no_prompt={self.n_skipped_no_prompt} -> {self.out_path}")

    # ---- configuration ----------------------------------------------------
    def _load_config(self, path: Path) -> None:
        if yaml is None:
            raise RuntimeError("pyyaml is required: pip install pyyaml")
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cap = cfg.get("capture", {})
        study = cfg.get("study", {})

        self.patterns = [re.compile(p) for p in cfg.get("url_patterns", [])]
        if not self.patterns:
            raise RuntimeError(f"No url_patterns in {path} -- nothing would be captured.")

        out_dir = Path(cap.get("output_dir", "./captures"))
        out_dir.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.out_path = out_dir / f"captures-{day}.jsonl"

        self.max_chars = int(cap.get("max_prompt_chars", 8000))
        self.store_response_digest = bool(cap.get("store_response_digest", True))
        self.salt = str(cap.get("pseudonym_salt", "")) or None

        roster_file = cap.get("roster_file")
        roster: list[str] = []
        if roster_file and Path(roster_file).exists():
            roster = [ln.strip() for ln in
                      Path(roster_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.scrubber = Scrubber(roster)

        self.condition = study.get("condition", "unset")
        self.period = int(study.get("period", 0))

        ctx.log.info(f"[capture] {len(self.patterns)} patterns, roster={len(roster)} names, "
                     f"condition={self.condition}, out={self.out_path}")

    def _pseudonymise(self, student_code: str) -> str:
        if not self.salt:
            raise RuntimeError("pseudonym_salt must be set before capturing; "
                               "the salt is held by the school, not the researcher.")
        # Canonical form first (no spaces or dashes, upper case), exactly as the
        # exercise client and the test runner do -- otherwise "gy-k7m4p-q" typed
        # here and "GY-K7M4P-Q" typed there are two pupils whose captured prompts
        # cannot be joined to their lesson or their tests.
        canonical = "".join((student_code or "").split()).replace("-", "") \
            .replace("—", "").upper()
        h = hashlib.sha256((self.salt + "|" + canonical).encode("utf-8"))
        return h.hexdigest()[:16]

    # ---- interception -----------------------------------------------------
    def request(self, flow: http.HTTPFlow) -> None:
        self.n_seen += 1
        url = flow.request.pretty_url
        if flow.request.method != "POST" or not self._matches(url):
            return

        body = self._parse_json(flow.request.get_text(strict=False))
        if body is None:
            return
        prompt = extract_prompt(url, body)
        if not prompt:
            self.n_skipped_no_prompt += 1
            return

        raw_len = len(prompt)
        prompt = prompt[: self.max_chars]
        result = self.scrubber.scrub(prompt)

        self._write({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "captureId": str(uuid.uuid4()),
            "kind": "prompt",
            "session": self.session,
            "pseudonym": self.pseudonym,
            "condition": self.condition,
            "period": self.period,
            "host": flow.request.host,
            "url": self._strip_query(url),
            "method": flow.request.method,
            "promptText": result.text,
            "promptChars": raw_len,
            "truncated": raw_len > self.max_chars,
            "scrubbed": result.counts,
        })
        self.n_captured += 1
        flow.metadata["captured"] = True

    def response(self, flow: http.HTTPFlow) -> None:
        """Store only a digest and a length of the model's answer.  That is
        enough for the verbatim-transfer ratio and keeps no model output."""
        if not self.store_response_digest or not flow.metadata.get("captured"):
            return
        content = flow.response.get_content(strict=False) or b""
        self._write({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "captureId": str(uuid.uuid4()),
            "kind": "response_digest",
            "session": self.session,
            "pseudonym": self.pseudonym,
            "host": flow.request.host,
            "status": flow.response.status_code,
            "bodySha256": hashlib.sha256(content).hexdigest(),
            "bodyBytes": len(content),
            # shingles let us compute overlap with a pupil's answer without
            # keeping the text: 8-gram hashes, truncated, order preserved
            "shingles": self._shingles(content),
        })

    # ---- helpers ----------------------------------------------------------
    def _matches(self, url: str) -> bool:
        return any(p.search(url) for p in self.patterns)

    @staticmethod
    def _parse_json(text: str | None) -> dict | None:
        if not text:
            return None
        try:
            obj = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
        return obj if isinstance(obj, dict) else None

    @staticmethod
    def _strip_query(url: str) -> str:
        return url.split("?", 1)[0]

    @staticmethod
    def _shingles(content: bytes, k: int = 8, limit: int = 400) -> list[str]:
        try:
            words = content.decode("utf-8", "ignore").split()
        except Exception:
            return []
        out = []
        for i in range(0, max(len(words) - k + 1, 0)):
            gram = " ".join(words[i:i + k]).lower()
            out.append(hashlib.sha1(gram.encode("utf-8")).hexdigest()[:12])
            if len(out) >= limit:
                break
        return out

    def _write(self, record: dict) -> None:
        assert self.out_path is not None
        with self.out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


addons = [PromptCapture()]
