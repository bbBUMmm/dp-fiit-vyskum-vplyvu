"""Tests for the interaction features: activities, process metrics, live PEQI, QR.

Each section plants a known answer and demands it back, or states a property
that must hold for any input. The PEQI section is a pinning test rather than a
unit test: the live classifier must agree, case by case, with the corpus the
Python reference writes and the Java implementation is held to.

Run:  python test_features.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import activities as act                                         # noqa: E402
import events as ev                                              # noqa: E402
import metrics                                                   # noqa: E402
import peqi_live                                                 # noqa: E402
import qr                                                        # noqa: E402

PASS = FAIL = 0


def check(name, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n       got:  {got!r}\n       want: {want!r}")


def ok(name, cond, detail=""):
    check(name + (f" ({detail})" if detail and not cond else ""), bool(cond), True)


def refused(name, fn):
    try:
        fn()
        ok(name, False, "accepted")
    except act.ActivityError:
        ok(name, True)


# ===================================================================== packs
print("activity packs")
packs = act.load_packs(HERE / "activities")
check("four packs load and validate", sorted(packs),
      ["fyzika", "informatika", "matematika", "vseobecne"])
all_acts = [a for p in packs.values() for a in p["activities"]]
check("activity ids are unique across packs", len({a["id"] for a in all_acts}), len(all_acts))
check("every activity type is used at least once",
      sorted({a["type"] for a in all_acts}), sorted(act.TYPES))
check("every widget is used at least once",
      sorted({a["widget"] for a in all_acts if a.get("widget")}), sorted(act.WIDGETS))

# the informatics pack must not rehearse the test items
bank_text = " ".join((HERE.parent / "assessment" / "banks" / f).read_text(encoding="utf-8")
                     for f in ("t1_ipt.json", "t1_drt.json", "t1_precheck.json", "tt_transfer.json"))
arrays = [json.dumps(a["params"]["array"]).replace(",", ", ") for a in packs["informatika"]["activities"]
          if a.get("widget") == "binary-search"]
ok("no informatics animation uses an array from a test item",
   not any(arr in bank_text for arr in arrays), str(arrays))

# =============================================================== validation
print("validation refuses what it must")
refused("an unknown type", lambda: act.validate({"id": "x", "type": "quiz"}))
refused("a poll with one option", lambda: act.validate(
    {"id": "x", "type": "poll", "question": "q", "options": ["a"]}))
refused("a key that is not an option", lambda: act.validate(
    {"id": "x", "type": "poll", "question": "q", "options": ["a", "b"], "key": 5}))
refused("binary search on an unsorted array by accident", lambda: act.validate(
    {"id": "x", "type": "animation", "widget": "binary-search",
     "params": {"array": [3, 1, 2], "target": 2}}))
ok("but allowed as a declared counter-example", act.validate(
    {"id": "x", "type": "animation", "widget": "binary-search",
     "params": {"array": [3, 1, 2], "target": 2, "allowUnsorted": True}}))
refused("an order task with repeated items", lambda: act.validate(
    {"id": "x", "type": "order", "question": "q", "items": ["a", "a", "b"]}))
refused("an id with spaces", lambda: act.validate(
    {"id": "a b", "type": "reflect", "question": "q"}))
refused("an unknown widget", lambda: act.validate(
    {"id": "x", "type": "handson", "widget": "rocket"}))

# ============================================================ what pupils get
print("what a pupil's device receives")
poll = act.validate({"id": "P", "type": "poll", "question": "q", "options": ["a", "b", "c"],
                     "key": 1, "explain": "because", "note": "teacher only", "confidence": True})
pv = act.public_view(poll, revealed=False)
ok("no key, explanation or teacher note before the reveal",
   not ({"key", "explain", "note"} & set(pv)))
pv2 = act.public_view(poll, revealed=True)
ok("the key and the explanation after it, the note never",
   pv2.get("key") == 1 and pv2.get("explain") and "note" not in pv2)
order = act.validate({"id": "O", "type": "order", "question": "q", "items": list("abcdef")})
ok("an order task is never handed out already solved",
   all(act.public_view(dict(order, id=f"O{i}"), False)["display"] != list(range(6))
       for i in range(40)))

# ================================================================ scoring
print("responses are checked and scored")
check("a poll answer is scored against the key",
      act.check_response(poll, {"choice": 1, "confidence": 60})["correct"], True)
refused("a missing confidence where one is asked for",
        lambda: act.check_response(poll, {"choice": 1}))
refused("a choice out of range", lambda: act.check_response(poll, {"choice": 7, "confidence": 1}))
refused("a boolean smuggled in as a choice",
        lambda: act.check_response(poll, {"choice": True, "confidence": 1}))
num = act.validate({"id": "N", "type": "predict", "question": "q",
                    "input": {"kind": "number", "tolerance": 0.5}, "answer": 8})
check("a number within tolerance is correct",
      act.check_response(num, {"value": 8.4})["correct"], True)
check("outside it is not", act.check_response(num, {"value": 9})["correct"], False)
refused("a non-number prediction", lambda: act.check_response(num, {"value": "8"}))
r = act.check_response(order, {"order": [0, 1, 2, 3, 5, 4]})
check("an order scores the share of items in place", (r["score"], r["correct"]),
      (round(4 / 6, 4), False))
refused("an order that drops an item", lambda: act.check_response(order, {"order": [0, 1, 2]}))
refl = act.validate({"id": "R", "type": "reflect", "question": "q"})
check("free text is capped", len(act.check_response(refl, {"text": "x" * 5000})["text"]),
      act.MAX_TEXT)

# ============================================================ live lifecycle
print("one activity at a time, and only while it runs")
live = act.Live(packs)
cur = live.start("INF-POLL-SORTED")
live.view_for("p1")
live.view_for("p2")
live.respond("p1", "INF-POLL-SORTED", cur["version"], {"choice": 2, "confidence": 80})
live.respond("p1", "INF-POLL-SORTED", cur["version"], {"choice": 0, "confidence": 30})
res = live.results()
check("a changed answer replaces the earlier one", res["counts"], [1, 0, 0, 0])
check("the response rate has a denominator", (res["n"], res["viewers"]), (1, 2))
refused("a response to an old version",
        lambda: live.respond("p2", "INF-POLL-SORTED", cur["version"] - 1, {"choice": 1, "confidence": 1}))
live.reveal()
refused("a response after the reveal",
        lambda: live.respond("p2", "INF-POLL-SORTED", cur["version"], {"choice": 2, "confidence": 1}))
cur2 = live.start("VS-EXIT")
ok("starting another activity archives the first", live.history[-1]["id"] == "INF-POLL-SORTED"
   and cur2["version"] == cur["version"] + 1)
live.respond("p1", "VS-EXIT", cur2["version"], {"text": "rozumiem", "confidence": 70})
ok("the teacher sees free text, pupils never do",
   live.results()["texts"] == ["rozumiem"] and "texts" not in live.results(public=True))
check("closing leaves nothing on the pupils' screens", (live.close() is not None, live.pulse()),
      (True, None))
a1 = live.add({"type": "poll", "question": "q", "options": ["a", "b"]})
a2 = live.add({"type": "poll", "question": "q", "options": ["a", "b"]})
ok("ad-hoc activities get fresh ids", a1["id"] != a2["id"] and a1["id"].startswith("AD-"))

# ================================================================ live PEQI
print("live PEQI is pinned to the shared corpus")
fixture = HERE.parent / "ai-prompt-monitor" / "src" / "test" / "resources" / "cross_impl_corpus.json"
if fixture.exists():
    cases = json.loads(fixture.read_text(encoding="utf-8"))["cases"]
    bad = [(c["prompt"], c["level"], peqi_live.classify(c["prompt"])) for c in cases
           if peqi_live.classify(c["prompt"]) != c["level"]]
    check(f"all {len(cases)} pinned cases get the reference level", bad, [])
else:
    print("  skip (corpus not present in this folder)")
idx = peqi_live.session_index(["L0", "L4", "X"])
check("PEQI averages on-task prompts only", (idx["peqi"], idx["off_task_rate"]), (0.5, 0.3333))
check("no prompts is no index, not a zero", peqi_live.session_index([])["peqi"], None)

# ================================================================== metrics
print("process measures from a planted event stream")


def e(kind, sec, **kw):
    return dict(kind=kind, timestamp=f"2026-10-07T09:{sec // 60:02d}:{sec % 60:02d}+00:00",
                session="S", condition="G", period=1, pseudonym="aaaaaaaaaaaaaaaa", **kw)


E = [
    e(ev.LOGIN, 0, device="d1"),
    e(ev.TASK_SHOWN, 0, taskId="U1"),
    e(ev.FIRST_KEYSTROKE, 30, taskId="U1"),
    e(ev.FIRST_IDEA, 60, taskId="U1", trigger="attempt", draftChars=40, msSinceShown=60000),
    e(ev.ATTEMPT, 60, taskId="U1", correct=False, confidence=80, autoCorrect=False),
    e(ev.PROMPT_SENT, 90, taskId="U1", promptText="preco je to tak", peqiLevel="L2"),
    e(ev.ASSISTANT_REPLY, 92, taskId="U1", replyFeatures={"finalAnswer": True}),
    e(ev.COPY, 95, taskId="U1", source="assistant", chars=50),
    e(ev.PASTE, 96, taskId="U1", target="answer", chars=50, fromAssistant=True),
    e(ev.ATTEMPT, 100, taskId="U1", correct=True, confidence=90, autoCorrect=True,
      assistantOverlap=0.9, pastedFromAssistant=True),
    e(ev.TASK_COMPLETED, 100, taskId="U1"),
    e(ev.TASK_SHOWN, 110, taskId="U2"),
    e(ev.FIRST_IDEA, 130, taskId="U2", trigger="prompt", draftChars=0, msSinceShown=20000),
    e(ev.PROMPT_SENT, 130, taskId="U2", promptText="napis mi riesenie", peqiLevel="L0"),
    e(ev.TASK_SKIPPED, 200, taskId="U2"),
    e(ev.INTERACTION, 200, clicks=10, keys=100, focusLoss=1, activeMs=60000, idleMs=20000,
      hiddenMs=20000),
    e(ev.ACTIVITY_VIEW, 210, activityId="X", version=1),
    e(ev.ACTIVITY_VIEW, 220, activityId="Y", version=2),
    e(ev.ACTIVITY_RESPONSE, 230, activityId="X", version=1, correct=True, confidence=60,
      latencyMs=5000),
]
m = metrics.pupil_metrics(E)
check("time to first keystroke", m["t_first_keystroke_median_s"], 30.0)
check("time to first prompt (median of 90 s and 20 s)", m["t_first_prompt_median_s"], 55.0)
check("ABHR: tried first in one of two episodes with a prompt", m["abhr"], 0.5)
check("first idea: help asked with an empty draft", m["help_with_own_draft_rate"], 0.0)
check("first idea: median size", m["first_idea_chars_median"], 20.0)
check("PEQI of one L2 and one L0", (m["peqi"], m["offload_rate"]), (0.25, 0.5))
check("copy and paste from the assistant",
      (m["copy_from_assistant"], m["paste_from_assistant"]), (1, 1))
check("a copied answer is recognised", m["copied_answer_rate"], 1.0)
check("self-estimation: confidence and calibration bias",
      (m["confidence_mean"], m["lesson_calibration_bias"]), (85.0, round((0.8 - 0 + 0.9 - 1) / 2, 4)))
check("progress", (m["n_completed"], m["n_skipped"], m["n_attempts"]), (1, 1, 2))
check("interaction counters", (m["clicks"], m["keystrokes"], m["focus_losses"]), (10, 100, 1))
check("engagement components", (m["active_ratio"], m["focus_ratio"], m["activity_participation"]),
      (0.6, 0.8, 0.5))
check("engagement index is the mean of its components", m["engagement_index"],
      round((0.6 + 0.8 + 0.5) / 3, 4))
check("the reply handed over a solution", m["reply_solution_exposure"], 1.0)
rows = metrics.compute(E + [dict(E[0], pseudonym="class", kind=ev.PHASE)])
check("class-level events are not a pupil", len(rows), 1)
check("a pupil who did nothing has measures of None, not zero",
      metrics.pupil_metrics([e(ev.LOGIN, 0)])["peqi"], None)

# ======================================================================= QR
print("QR code")
data = [16, 32, 12, 86, 97, 128, 236, 17, 236, 17, 236, 17, 236, 17, 236, 17]
check("Reed-Solomon matches the ISO 18004 worked example",
      qr.rs_remainder(data, qr.rs_divisor(10)), [165, 36, 212, 193, 237, 54, 199, 135, 44, 85])
mat = qr.matrix("http://192.168.0.23:5173/")
check("an address fits a version-2 symbol", len(mat), 25)
finder = [[mat[y][x] for x in range(7)] for y in range(7)]
ok("the finder pattern is in the corner",
   all(finder[0]) and all(finder[6]) and not finder[1][1] and finder[3][3])
try:
    import zxingcpp                                           # optional, test-only
    from PIL import Image
    texts = ["http://10.0.0.5:5173/", "http://172.16.254.199:51730/" + "x" * 120, "Žiak č. 7"]
    good = 0
    for t in texts:
        mm = qr.matrix(t)
        n, b, s = len(mm), 4, 6
        img = Image.new("L", ((n + 2 * b) * s,) * 2, 255)
        px = img.load()
        for y, row in enumerate(mm):
            for x, v in enumerate(row):
                if v:
                    for dy in range(s):
                        for dx in range(s):
                            px[(x + b) * s + dx, (y + b) * s + dy] = 0
        res = zxingcpp.read_barcodes(img)
        good += bool(res and res[0].text == t)
    check("an independent decoder reads the symbols back", good, len(texts))
except ImportError:
    print("  skip (no QR decoder installed; the Reed-Solomon vector above still holds)")
try:
    qr.matrix("x" * 300)
    ok("text beyond version 10 is refused", False)
except ValueError:
    ok("text beyond version 10 is refused", True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
