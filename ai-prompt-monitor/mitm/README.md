# Capture layer (mitmproxy)

This directory replaces the LittleProxy-based capture layer of the walking
skeleton. That layer could not intercept modern conversational interfaces
because it supports neither HTTP/2 nor WebSocket — verified against ChatGPT in
June 2026, where the send endpoint returned 400 at the proxy and streamed
responses were never seen.

## What it does

Three things, deliberately:

1. matches the request URL against the allow-list in `config/study.yaml`;
2. extracts **the pupil's own text** from the request body — not the whole body;
3. appends one JSON object per prompt to `captures/captures-<date>.jsonl`.

Everything else — pseudonymisation policy, prompt classification, PEQI, the
analytic dataset — lives in the Java application layer, which tails that file.
The file is the interface between the two: it survives a crash on either side,
it can be replayed when the derived measures change, and a school can read it
without any tooling.

## Why a file and not a socket

A socket would be faster and is entirely the wrong trade. The capture runs
unattended in a classroom, on a laptop a teenager is using. If the Java side
dies, the capture must keep going; if the capture dies, the Java side must not
lose what was already written. A line-appended file gives that for free, and it
is the artefact a data-protection officer can actually inspect.

## Running

```bash
pip install -r mitm/requirements.txt

mitmdump -s mitm/capture_addon.py \
    --set study_config=config/study.yaml \
    --set session=2026-10-07-2A-P1 \
    --set student=<opaque code issued by the school> \
    --listen-host 127.0.0.1 --listen-port 8080
```

First run on a machine, install the CA that mitmproxy generates
(`~/.mitmproxy/mitmproxy-ca-cert.pem`) into the browser used for the study — and
only there. Remove it when the study ends; that removal is a line in the
fidelity protocol, not an afterthought.

`pseudonym_salt` must be set in `config/study.yaml` before capture starts. It is
held by the school. Without it the addon refuses to run rather than falling back
to storing something reversible.

## Record shapes

```jsonc
// kind = "prompt"
{
  "timestamp": "2026-10-07T09:15:00+00:00",
  "captureId": "…uuid…",
  "kind": "prompt",
  "session": "2026-10-07-2A-P1",
  "pseudonym": "0123456789abcdef",   // sha256(salt | studentCode)[:16]
  "condition": "G", "period": 1,
  "host": "chatgpt.com",
  "url": "https://chatgpt.com/backend-api/conversation",   // query stripped
  "method": "POST",
  "promptText": "preco je to O(log n)?",
  "promptChars": 21, "truncated": false,
  "scrubbed": {"name": 1}            // what was removed, and how much
}

// kind = "response_digest"  — no model output is stored
{
  "kind": "response_digest",
  "bodySha256": "…", "bodyBytes": 4096,
  "shingles": ["9f2c…", "…"]         // 8-gram hashes, for the verbatim-transfer ratio
}
```

## Tests

```bash
python mitm/test_capture.py
```

29 checks, no mitmproxy needed: prompt extraction for four payload shapes plus
the generic fallback, and every scrubbing rule including Slovak name declension.
The two bugs these caught during development — a phone pattern that never
matched `+421 903 123 456`, and roster matching that missed every declined
form — are exactly the class of defect that would have been invisible in
production and unrecoverable after the fact.

## Known limits

- Captures only traffic from the school device. A pupil on their own phone is
  invisible; coverage is measured against the exercise client's own events and
  reported rather than assumed.
- Extraction is provider-specific and will break when a provider changes its
  payload. That is why each extractor is a separate five-line function and why
  the allow-list lives in configuration.
- Scrubbing reduces risk; it does not anonymise. Free text written by minors
  cannot be anonymised, which is why the prompt corpus is never published.
