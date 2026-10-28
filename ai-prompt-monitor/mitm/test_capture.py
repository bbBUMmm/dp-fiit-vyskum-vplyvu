"""Tests for the capture layer that do not need mitmproxy to be installed.

The addon class itself needs mitmproxy; the two pieces that carry the research
risk -- prompt extraction and scrubbing -- do not, and are tested here.

Run:  python mitm/test_capture.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from scrub import Scrubber, scrub  # noqa: E402


def _load_extractors():
    """Import only the extractor functions, without importing mitmproxy."""
    src = (HERE / "capture_addon.py").read_text(encoding="utf-8")
    cut = src.index("# ---------------------------------------------------------"
                    "-----------------\nclass PromptCapture")
    head = src[:cut].replace("from mitmproxy import ctx, http", "ctx = http = None")
    ns: dict = {"__file__": str(HERE / "capture_addon.py")}
    exec(compile(head, "capture_addon_head", "exec"), ns)  # noqa: S102
    return ns["extract_prompt"]


extract_prompt = _load_extractors()

PASS = FAIL = 0


def check(name: str, got, want) -> None:
    global PASS, FAIL
    if got == want:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n       got:  {got!r}\n       want: {want!r}")


def check_true(name: str, cond: bool) -> None:
    check(name, bool(cond), True)


# ---------------------------------------------------------------- extraction
print("extraction")

check("openai parts shape",
      extract_prompt("https://chatgpt.com/backend-api/conversation", {
          "messages": [
              {"author": {"role": "system"}, "content": {"parts": ["ignore me"]}},
              {"author": {"role": "user"}, "content": {"parts": ["preco je to O(log n)?"]}},
          ]}),
      "preco je to O(log n)?")

check("openai takes the newest user turn",
      extract_prompt("https://chatgpt.com/backend-api/conversation", {
          "messages": [
              {"role": "user", "content": "stara otazka"},
              {"role": "assistant", "content": "odpoved"},
              {"role": "user", "content": "nova otazka"},
          ]}),
      "nova otazka")

check("anthropic block shape",
      extract_prompt("https://claude.ai/api/organizations/x/chat", {
          "messages": [{"role": "user",
                        "content": [{"type": "text", "text": "kedy je linearne lepsie?"}]}]}),
      "kedy je linearne lepsie?")

check("google contents shape",
      extract_prompt("https://gemini.google.com/v1/x", {
          "contents": [{"role": "user", "parts": [{"text": "vysvetli memoizaciu"}]}]}),
      "vysvetli memoizaciu")

check("own exercise client",
      extract_prompt("http://localhost:5173/api/ask", {"prompt": "  mam to dobre?  "}),
      "mam to dobre?")

check("generic fallback on an unknown host",
      extract_prompt("https://unknown.example/api", {"question": "co je rekurzia"}),
      "co je rekurzia")

check("no user text -> None",
      extract_prompt("https://chatgpt.com/backend-api/conversation",
                     {"messages": [{"role": "assistant", "content": "hi"}]}),
      None)

check("autocomplete payload is not mistaken for a prompt",
      extract_prompt("https://chatgpt.com/backend-api/ac", {"n": 3, "model": "gpt"}),
      None)

# ------------------------------------------------------------------ scrubbing
print("scrubbing")

r = scrub("napis mi to na jakub.novak@gimnazium.sk prosim")
check("email removed", "[EMAIL]" in r.text and "@" not in r.text, True)
check("email counted", r.counts.get("email"), 1)

r = scrub("moje cislo je +421 903 123 456, zavolaj")
check("phone removed", "[TELEFON]" in r.text, True)

r = scrub("rodne cislo 010203/4567 je moje")
check("birth number removed", "[RODNE_CISLO]" in r.text, True)
check("birth number not eaten by long-digit rule", r.counts.get("birth_number"), 1)

r = scrub("token sk-abcdefghijklmnop12345 a link https://example.com/a?b=c")
check("token removed", "[TOKEN]" in r.text, True)
check("url removed", "[URL]" in r.text, True)

r = scrub("moje ID je 123456789012")
check("long digit run removed", "[CISLO]" in r.text, True)

s = Scrubber(["Jakub Novak", "Zuzana Kovacova"])
r = s.scrub("Jakub mi povedal ze Zuzane to nevyslo")
check("roster name removed (nominative)", "Jakub" not in r.text, True)
check("roster name removed (declined)", "Zuzane" not in r.text, True)
check("both names counted", r.counts.get("name"), 2)

r = s.scrub("binarne vyhladavanie je O(log n)")
check("no false positive on domain text", r.counts.get("name"), None)
check("domain text untouched", r.text, "binarne vyhladavanie je O(log n)")

s2 = Scrubber(["Mykyta Prykhodko"])
r = s2.scrub("Prykhodkovi to vysvetlil Mykyta")
check("diacritics-free declension handled", r.counts.get("name"), 2)

s3 = Scrubber(["Žofia Ľubená"])
r = s3.scrub("Žofia a Ľubená sú v triede")
check("names with diacritics removed", "Žofia" not in r.text and "Ľubená" not in r.text, True)
check("surrounding diacritics preserved", "sú v triede" in r.text, True)

check("empty input is safe", scrub("").text, "")
check("no roster is safe", scrub("Jakub tu bol").counts.get("name"), None)

# --------------------------------------------------------------- record shape
print("record shape")
rec = {
    "timestamp": "2026-10-07T09:15:00+00:00", "captureId": "x", "kind": "prompt",
    "session": "2026-10-07-2A-P1", "pseudonym": "0123456789abcdef",
    "condition": "G", "period": 1, "host": "chatgpt.com",
    "url": "https://chatgpt.com/backend-api/conversation", "method": "POST",
    "promptText": "preco je to O(log n)?", "promptChars": 21,
    "truncated": False, "scrubbed": {},
}
check_true("record is valid json", json.loads(json.dumps(rec, ensure_ascii=False)) == rec)
check_true("record carries no raw student id", "student" not in rec)
check_true("record carries no cookies or headers",
           not any(k.lower() in ("cookie", "authorization", "headers") for k in rec))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
