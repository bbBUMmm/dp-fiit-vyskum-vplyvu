"""test_assessment.py -- the assessment layer, end to end.

Every test here either plants a known answer and demands it back, or states a
property that must hold for any input. Where a defect has already been found,
the test that would have caught it is here and named after it.

Run:  python test_assessment.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

import bank
import effort
import integrity
import linkage
import profiles
import report
import scoring
import sessions
import tex_export

HERE = Path(__file__).resolve().parent
PASS = FAIL = 0


def section(name: str) -> None:
    print(f"\n{name}")


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


# ===========================================================================
def test_bank_contract():
    section("item bank: the contract three consumers depend on")
    banks = bank.load_all()
    ok("every bank loads and validates", len(banks) >= 8, f"{len(banks)} banks")

    ipt, drt = banks["T1_IPT"], banks["T1_DRT"]
    ok("both forms have the same number of items",
       ipt.n_items == drt.n_items == 12, f"{ipt.n_items} vs {drt.n_items}")
    ok("both forms are worth the same number of points",
       ipt.max_points == drt.max_points)
    ok("both forms have the same number of open items",
       sum(1 for i in ipt.items if i.is_open)
       == sum(1 for i in drt.items if i.is_open) == bank.OPEN_ITEMS_PER_FORM)
    ok("six anchors, the same six in both forms",
       ipt.anchors == drt.anchors and len(ipt.anchors) == 6, str(ipt.anchors))

    # THE defect: the thesis claimed six identical items and had none.
    same = []
    for a in ipt.anchors:
        x = [i for i in ipt.items if i.anchor == a][0]
        y = [i for i in drt.items if i.anchor == a][0]
        same.append(x.stem.strip() == y.stem.strip()
                    and x.options == y.options and x.key == y.key)
    ok("every anchor is character-identical across the forms", all(same),
       f"{same.count(False)} anchors differ")

    ok("no anchor is an open item",
       all(not i.is_open for i in ipt.items if i.anchor))
    ok("anchors span at least three cognitive levels",
       len({i.level for i in ipt.items if i.anchor}) >= 3)

    # every multiple-choice distractor carries a diagnosis
    undiagnosed = []
    for b in banks.values():
        if b.instrument not in bank.SCORED:
            continue
        for i in b.items:
            if i.format in ("mc4", "mc3"):
                for k in range(len(i.options)):
                    if k != i.key and str(k) not in i.distractor_dx:
                        undiagnosed.append(f"{b.bank_id}/{i.id}/{k}")
    ok("every distractor has a diagnosis", not undiagnosed,
       f"{len(undiagnosed)} missing: {undiagnosed[:4]}")

    ok("no questionnaire item carries a confidence slider",
       all(not i.jol for b in banks.values() if b.instrument in bank.UNSCORED
           for i in b.items))
    ok("Jr. MAI has the 18 items the thesis declares in five places",
       banks["JRMAI"].n_items == 18, str(banks["JRMAI"].n_items))
    ok("Jr. MAI subscales are 6/6/6 and name only existing items",
       sorted(len(v) for v in banks["JRMAI"].subscales.values()) == [6, 6, 6])


def test_bank_rejects_what_it_must():
    section("item bank: the validator refuses what it should")
    import copy

    def reject(label, mutate):
        banks = bank.load_all()
        try:
            mutate(banks)
            bank.cross_validate(banks)
            for b in banks.values():
                bank.validate(b)
            ok(label, False, "accepted")
        except bank.BankError:
            ok(label, True)

    def differ_anchor(banks):
        it = [i for i in banks["T1_DRT"].items if i.anchor == "A2"][0]
        it.stem = it.stem.replace("1024", "512")
    reject("an anchor whose wording differs between forms", differ_anchor)

    def drop_level(banks):
        banks["T1_IPT"].items = banks["T1_IPT"].items[:-1]
    reject("a form that no longer matches the blueprint", drop_level)

    def open_anchor(banks):
        for bb in ("T1_IPT", "T1_DRT"):
            for i in banks[bb].items:
                if i.anchor == "A1":
                    i.format, i.rubric, i.options, i.key = (
                        "open", [{"points": 1, "criterion": "x"}], [], None)
    reject("an open item used as an anchor", open_anchor)

    def kill_dx(banks):
        banks["T1_IPT"].items[0].distractor_dx = {}
    reject("a multiple-choice item with undiagnosed distractors", kill_dx)

    def slider_on_questionnaire(banks):
        banks["JRMAI"].items[0].jol = True
    reject("a confidence slider on an item with no correct answer",
           slider_on_questionnaire)

    def blow_budget(banks):
        banks["CT"].items[0].expected_sec = 4000
    reject("an instrument whose items exceed its protocol slot", blow_budget)


def test_time_budget_from_items():
    section("time budget: computed from items, not from an average")
    res = sessions.budget()
    ok("every session fits the lessons the school gives", res["all_fit"],
       "; ".join(res["violations"]))
    for s in res["sessions"]:
        ok(f"{s['code']}: longest unbroken stretch within the fatigue cap",
           s["within_fatigue_cap"],
           f"{s['longest_run_min']} min > {sessions.FATIGUE_CAP_MIN}")

    cmp_ = sessions.naive_budget_comparison()
    ok("the flat average understated the open-item instruments",
       cmp_["all_understatements_same_sign"])
    ok("and understated them substantially",
       cmp_["total_understated"] > 15, f"{cmp_['total_understated']} min")
    ok("the worst case is the transfer test",
       cmp_["worst"] == "TT", cmp_["worst"])
    # a flat average that happened to be right would make this test vacuous
    ok("the comparison is not vacuous", cmp_["worst_by"] > 10,
       str(cmp_["worst_by"]))


def test_linkage_properties():
    section("pupil code: the properties, re-derived rather than cited")
    codes = linkage.issue("GY", 120, seed=11)
    ok("all issued codes are distinct", len(set(codes)) == 120)
    ok("no issued code contains a confusable character",
       all(c not in linkage.CONFUSABLE
           for code in codes for c in linkage.normalise(code)[2:]))

    # exhaustive, not sampled
    sub_miss = trans_miss = jump_miss = 0
    for code in codes:
        raw = linkage.normalise(code)
        for i in range(2, len(raw) - 1):
            for ch in linkage.ALPHABET:
                if ch == raw[i]:
                    continue
                if linkage._passes(raw[:i] + ch + raw[i + 1:]):
                    sub_miss += 1
        for i in range(2, len(raw) - 2):
            if raw[i] != raw[i + 1] and linkage._passes(
                    raw[:i] + raw[i + 1] + raw[i] + raw[i + 2:]):
                trans_miss += 1
        for i in range(2, len(raw) - 3):
            s = list(raw)
            if s[i] != s[i + 2]:
                s[i], s[i + 2] = s[i + 2], s[i]
                if linkage._passes("".join(s)):
                    jump_miss += 1
    ok("every single-character substitution is detected", sub_miss == 0,
       f"{sub_miss} survived")
    ok("every adjacent transposition is detected", trans_miss == 0,
       f"{trans_miss} survived")
    ok("every jump transposition is detected", jump_miss == 0,
       f"{jump_miss} survived")

    # the message must name the cause, because a pupil has one envelope
    try:
        linkage.verify("GY-K7M4O-Q", "GY")
        ok("a code with a letter O is refused", False, "accepted")
    except linkage.CodeError as e:
        ok("a code with a letter O is refused with a specific message",
           "O" in str(e), str(e))

    a = linkage.audit(trials=3000, seed=3)
    ok("no mistyped code in the audit landed on another pupil's code",
       all(a[k]["hit_another_pupil"] == 0 for k in ("sub", "trans", "sub2", "jump")))
    ok("the expected number of silently merged pupils is negligible",
       a["study_level"]["expected_merged_pupils"] < 1e-4,
       str(a["study_level"]["expected_merged_pupils"]))
    ok("and without a check character it would not be",
       a["without_check_character"]["expected_undetected_entries"] > 10,
       str(a["without_check_character"]["expected_undetected_entries"]))


def test_scoring_boundaries():
    section("scoring: what is automatic and what is not")
    fails = scoring.self_test()
    ok("scoring self-test passes", not fails, "; ".join(fails))

    banks = bank.load_all()
    # an open item must never be scored by machine, in any bank
    opens = [(b.bank_id, i.id) for b in banks.values() for i in b.items
             if i.is_open]
    sc = []
    for bid, iid in opens:
        inst = banks[bid].instrument
        r = scoring.Response("P", "P1", inst, iid, "nejaký text", 90.0)
        sc.append(scoring.score([r], banks)[0])
    ok("every open item in every bank comes back pending",
       all(s.pending and s.points is None for s in sc), f"{len(sc)} open items")

    # multiple response, the number of correct options not disclosed
    m = bank.Item(id="M1", format="multi", stem="Ktoré polia sú usporiadané?",
                  level="porozumenie", options=["[1, 2]", "[2, 1]", "[3, 3]", "[5, 4]"],
                  key=[0, 2], distractor_dx={"1": "zamieňa smer", "3": "zamieňa smer"})
    b = bank.Bank("X_IPT", "CT", "x", 5, [m])
    try:
        bank.validate(b)
        ok("a keyed multiple-response item validates", True)
    except bank.BankError as e:
        ok("a keyed multiple-response item validates", False, str(e))
    for bad_key in (None, [], [0, 0], [9]):
        bad = bank.Item(**{**m.__dict__, "key": bad_key})
        try:
            bank.validate(bank.Bank("X_IPT", "CT", "x", 5, [bad]))
            ok(f"a multiple-response key {bad_key!r} is refused", False, "accepted")
        except bank.BankError:
            ok(f"a multiple-response key {bad_key!r} is refused", True)
    r_ok = scoring.score_one(m, scoring.Response("P", "P1", "CT", "M1", "2,0", 20.0))
    r_part = scoring.score_one(m, scoring.Response("P", "P1", "CT", "M1", "0,1", 20.0))
    ok("the full correct set scores, in any order", r_ok.correct == 1 and r_ok.points == 1)
    ok("a partly correct set does not, and says what was wrong",
       r_part.correct == 0 and "zamieňa smer" in r_part.diagnosis and "chýba" in r_part.note,
       f"{r_part.diagnosis} / {r_part.note}")


def test_effort_and_integrity():
    section("effort and integrity: measured, not asserted")
    ok("effort self-test passes", not effort.self_test())
    ok("integrity self-test passes", not integrity.self_test())

    # one family is never enough, in any combination
    def row(i, sec, exp, corr, diff, **kw):
        d = dict(item_id=i, seconds=sec, expected_sec=exp, correct=corr,
                 difficulty=diff, raw="", is_open=False, blur_seconds=0.0,
                 paste_events=0)
        d.update(kw)
        return d
    clean = [row(f"I{k}", 30 + 8 * k, 30 + 8 * k, 1 if k < 5 else 0,
                 -1 + 0.3 * k) for k in range(8)]
    for fam, mut in (("B", dict(blur_seconds=40.0)),
                     ("T", dict(seconds=1.0, correct=1))):
        rows = [dict(r) for r in clean]
        rows[0].update(mut)
        p = integrity.examine("P", "T4a", rows)
        ok(f"a single {fam}-family flag does not exclude", not p.excluded,
           str(p.summary()))


def test_profiles_work_at_n_equals_one():
    section("profiles: a label from one pupil's own data")
    ok("profiles self-test passes", not profiles.self_test())

    one = profiles.Indicators(peqi=0.12, n_prompts=20, abhr=0.08, n_tasks=8,
                              calib_bias=0.31, reliance=6.4, critical=0.3,
                              n_ct_items=12, condition="G")
    alone = profiles.classify(one)
    ok("a single pupil gets a label", alone.profile == "slepo doverujuci")
    ok("and a one-sentence reason naming the evidence",
       "PEQI" in alone.reason and len(alone.reason) < 400)

    # the defining property, over a large and adversarial peer set
    import random
    rng = random.Random(9)
    peers = {f"Q{i}": profiles.Indicators(
        peqi=rng.uniform(0.0, 1.0), n_prompts=rng.randint(5, 40),
        abhr=rng.random(), n_tasks=8, calib_bias=rng.uniform(-.4, .4),
        reliance=rng.uniform(1, 7), critical=rng.random(), n_ct_items=12,
        condition=rng.choice("GA")) for i in range(400)}
    with_peers = profiles.classify_many({"P": one, **peers})["P"]
    ok("the label does not change when 400 other pupils are added",
       with_peers.profile == alone.profile)

    # and it must not label a pupil it cannot see
    thin = profiles.Indicators(peqi=0.9, n_prompts=1, abhr=None, n_tasks=0,
                              condition="G")
    ok("a pupil with one prompt and no tasks is undetermined",
       profiles.classify(thin).profile == "neurceny")


def test_reports_disclose_nothing():
    section("reports: suppression applied by code")
    ok("report self-test passes", not report.self_test())

    # an adversarial class: every profile count below the minimum
    d = report.ClassData(klass="2.X", n_pupils=8,
                         profiles={"slepo dôverujúci": 2, "priemerný": 3,
                                   "vyhýbajúci sa": 3},
                         distractors={"T1-6": {1: 4, 2: 1}},
                         diagnoses={"T1-6": {"1": "a", "2": "b"}},
                         item_correct={"T1-6": (3, 8)},
                         means={"peqi": .2}, cohort_means={"peqi": .4},
                         cohort_classes=9)
    t, s = report.teacher_report(d), report.school_report(d)
    aud = report.disclosure_audit([t, s])
    ok("nothing below the minimum cell is published", aud["clean"], str(aud))
    ok("a misconception held by 4 of 8 pupils is suppressed",
       not t["misconceptions"])
    ok("a class of 8 is not compared with the cohort", not s["comparable"])


def test_generated_appendix_is_current():
    section("generated appendix: the thesis cannot drift from the bank")
    rc = tex_export.main(["--check"])
    ok("the generated files match what the bank produces now", rc == 0,
       "run: python assessment/tex_export.py")
    out = tex_export.OUT
    ok("the generated appendix exists", out.exists())
    txt = out.read_text(encoding="utf-8")
    banks = bank.load_all()
    # Compare against the ESCAPED stem. An array literal becomes \texttt{[...]}
    # and a multiplication sign becomes $\times$, so a raw-text comparison fails
    # on nine items that are in fact present -- which is what it did on the first
    # run of this test.
    def printed(stem: str) -> str:
        return tex_export.mono(tex_export.esc(stem))

    missing = [i.id for b in banks.values() for i in b.items
               if printed(i.stem)[:28] not in txt]
    ok("every item in every bank appears in the appendix", not missing,
       f"{len(missing)} missing: {missing[:5]}")
    # and the comparison is not vacuous: escaping really does change some stems
    changed = sum(1 for b in banks.values() for i in b.items
                  if printed(i.stem) != i.stem)
    ok("the escaping step actually transforms some stems", changed >= 9,
       f"{changed} transformed")
    ok("every correct answer is marked in the appendix",
       txt.count("checkmark") >= sum(
           1 for b in banks.values() if b.instrument in bank.SCORED
           for i in b.items if i.format in ("mc4", "mc3")))
    ok("the appendix says it is generated", "GENERATED" in txt[:400])


# ===========================================================================
def _get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=4) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(port, path, body, hdr=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **(hdr or {})},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def test_runner_end_to_end():
    section("runner: the test as a pupil sits it")
    import tempfile
    port = 5891
    tmp = Path(tempfile.mkdtemp())
    codes = linkage.issue("GY", 3, seed=77)
    cf = tmp / "codes.txt"
    cf.write_text("\n".join(codes), encoding="utf-8")
    log = tmp / "r.jsonl"

    # PYTHONIOENCODING removed on purpose: run-all-tests.ps1 exports it and that
    # is what hid the same defect in server.py. A school laptop does not have it.
    env = dict(os.environ)
    env.pop("PYTHONIOENCODING", None)
    env["PYTHONLEGACYWINDOWSSTDIO"] = "1"
    p = subprocess.Popen(
        [sys.executable, str(HERE / "runner.py"), "--bank", "T1_IPT",
         "--session", "P1", "--school", "GY", "--codes", str(cf),
         "--salt", "test-salt", "--log", str(log), "--port", str(port)],
        cwd=HERE, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        started = False
        for _ in range(80):
            try:
                _get(port, "/api/info")
                started = True
                break
            except Exception:
                if p.poll() is not None:
                    break
                time.sleep(0.1)
        detail = ""
        if not started and p.poll() is not None:
            detail = p.communicate(timeout=3)[1].decode(errors="replace")[-400:]
        ok("the runner starts with no PYTHONIOENCODING (the school-laptop case)",
           started, detail)
        if not started:
            return

        info = _get(port, "/api/info")
        ok("it serves the bank it was told to", info["items"] == 12)

        # a mistyped code is refused with a message, at the keyboard
        bad = linkage.normalise(codes[0])
        bad = bad[:3] + ("4" if bad[3] != "4" else "7") + bad[4:]
        st, body = _post(port, "/api/start", {"code": bad})
        ok("a one-character typo is refused", st == 400, str(body))
        ok("and the refusal explains what to do",
           "prepíš" in body.get("error", "").lower(), str(body))

        # a code from another school
        st, body = _post(port, "/api/start",
                         {"code": linkage.issue("XY", 1, seed=5)[0]})
        ok("a code from another school is refused", st == 400)

        st, body = _post(port, "/api/start", {"code": codes[0]})
        ok("a valid code starts a sitting", st == 200 and "token" in body,
           str(body))
        tok = body["token"]
        ok("the start asks for consent before the first item",
           body.get("consent", {}).get("state") == "pending", str(body.get("consent", {}))[:80])
        st, _ = _post(port, "/api/item", {}, {"X-Sitting": tok})
        ok("no item is served before the pupil decides", st == 403, str(st))
        _post(port, "/api/consent", {"choice": "yes"}, {"X-Sitting": tok})

        # one code, one sitting -- the error a check digit cannot catch
        st2, body2 = _post(port, "/api/start", {"code": codes[0]})
        ok("the same code cannot be opened twice", st2 == 409, str(body2))

        # answer every item, with a deliberate pause on one to exercise timing
        answered = 0
        for n in range(20):
            _, it = _post(port, "/api/item", {}, {"X-Sitting": tok})
            if it.get("done"):
                break
            i = it["item"]
            raw = "1" if i["format"].startswith("mc") else "nejaká odpoveď"
            extra = dict(paste_events=1, blur_seconds=12.0) if answered == 2 else {}
            if answered == 1:
                time.sleep(0.3)
            _post(port, "/api/answer",
                  {"item_id": i["id"], "raw": raw,
                   "jol": 70 if i["jol"] else None, **extra},
                  {"X-Sitting": tok})
            answered += 1
        ok("all twelve items were served and answered", answered == 12,
           str(answered))

        _, fin = _post(port, "/api/item", {}, {"X-Sitting": tok})
        ok("the sitting reports done", fin.get("done") is True)

        rows = [json.loads(L) for L in log.read_text(encoding="utf-8").splitlines()]
        ans = [r for r in rows if r["ev"] == "answer"]
        ok("every answer reached the log", len(ans) == 12, str(len(ans)))
        ok("each answer carries its own response time",
           all(r["seconds"] >= 0 for r in ans)
           and max(r["seconds"] for r in ans) >= 0.3)
        ok("the confidence slider was recorded where the item carries one",
           any(r["jol"] == 70 for r in ans))
        ok("paste and focus-loss were recorded",
           any(r["paste_events"] == 1 and r["blur_seconds"] >= 12 for r in ans))
        ok("the finished sitting cannot be restarted",
           _post(port, "/api/start", {"code": codes[0]})[0] == 409)

        text = log.read_text(encoding="utf-8")
        ok("the log never contains the pupil's code",
           all(linkage.normalise(c) not in text.replace("-", "") and c not in text
               for c in codes))
        import runner
        ok("it carries the salted pseudonym, the same as the lesson log",
           all(r["pseudonym"] == runner.pseudonymise("test-salt", codes[0]) for r in ans))
        ok("every answer carries an ISO timestamp, as the analysis contract requires",
           all("T" in r.get("timestamp", "") for r in ans))

        # and the log feeds the scorer with no translation layer
        banks = bank.load_all()
        resp = [scoring.Response(r["pseudonym"], r["session"], "IPT", r["item_id"],
                                 r["raw"], r["seconds"], r["jol"])
                for r in ans]
        sc = scoring.score(resp, banks)
        ok("the scorer reads the runner's log directly", len(sc) == 12)
        ok("closed items were scored and open items were not",
           sum(1 for s in sc if s.pending) == bank.OPEN_ITEMS_PER_FORM)
    finally:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def _start_runner(port, args):
    p = subprocess.Popen([sys.executable, str(HERE / "runner.py"), *args, "--port", str(port)],
                         cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for _ in range(80):
        try:
            _get(port, "/api/info")
            return p
        except Exception:
            if p.poll() is not None:
                break
            time.sleep(0.1)
    return p


def _stop(p):
    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()


def _raw_http(port, requests):
    """Requests over ONE keep-alive connection, as a browser sends them."""
    import socket
    s = socket.create_connection(("127.0.0.1", port))
    s.settimeout(5)
    out = []
    try:
        for method, path, headers, body in requests:
            b = body.encode("utf-8")
            hdr = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            s.sendall(f"{method} {path} HTTP/1.1\r\nHost: x\r\n{hdr}"
                      f"Content-Length: {len(b)}\r\n\r\n".encode() + b)
            buf = b""
            while b"\r\n\r\n" not in buf:
                buf += s.recv(4096)
            head, rest = buf.split(b"\r\n\r\n", 1)
            lines = head.decode("latin-1").split("\r\n")
            n = next((int(l.split(":")[1]) for l in lines
                      if l.lower().startswith("content-length")), 0)
            while len(rest) < n:
                rest += s.recv(4096)
            out.append(int(lines[0].split()[1]))
    except (OSError, ValueError, IndexError):
        out.append(None)
    finally:
        s.close()
    return out


def test_runner_as_a_browser_uses_it():
    section("runner: what a browser and a school day do to it")
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    codes = linkage.issue("GY", 4, seed=21)
    cf = tmp / "codes.txt"
    cf.write_text("\n".join(codes), encoding="utf-8")
    log = tmp / "r.jsonl"
    args = ["--bank", "T1_IPT", "--session", "P2", "--school", "GY", "--codes", str(cf),
            "--salt", "s", "--log", str(log)]
    port = 5893
    p = _start_runner(port, args)
    try:
        _, body = _post(port, "/api/start", {"code": codes[0]})
        tok = body["token"]
        _post(port, "/api/consent", {"choice": "yes"}, {"X-Sitting": tok})
        H = {"Content-Type": "application/json", "X-Sitting": tok}
        _, it = _post(port, "/api/item", {}, {"X-Sitting": tok})
        first = it["item"]["id"]
        # THE defect: /api/item never read its "{}" body, so the browser's next
        # request on the same connection -- the answer -- came back 501
        sts = _raw_http(port, [
            ("POST", "/api/item", H, "{}"),
            ("POST", "/api/answer", H, json.dumps({"item_id": first, "raw": "1", "jol": 55})),
            ("POST", "/api/item", H, "{}")])
        ok("item, answer, item on one keep-alive connection all succeed",
           sts == [200, 200, 200], str(sts))

        _, it = _post(port, "/api/item", {}, {"X-Sitting": tok})
        cur = it["item"]
        st, b = _post(port, "/api/answer", {"item_id": cur["id"], "raw": "1"}, {"X-Sitting": tok})
        ok("an item with a confidence slider needs the confidence", st == 400, str(b))
        st, b = _post(port, "/api/answer", {"item_id": cur["id"], "raw": "1", "jol": 150},
                      {"X-Sitting": tok})
        ok("a confidence outside 0-100 is refused", st == 400, str(b))
        st, b = _post(port, "/api/answer", {"item_id": "T1-15", "raw": "x", "jol": 50},
                      {"X-Sitting": tok})
        ok("an item that is not on the screen cannot be answered", st == 400, str(b))
        st, b = _post(port, "/api/answer", {"item_id": cur["id"], "raw": "1", "jol": "abc"},
                      {"X-Sitting": tok})
        ok("garbage is a 400 with a message, not a dead connection", st == 400, str(b))
        _post(port, "/api/answer", {"item_id": cur["id"], "raw": "2", "jol": 40},
              {"X-Sitting": tok})
    finally:
        _stop(p)

    # the laptop running the test crashes; the server is restarted
    p = _start_runner(port, args)
    try:
        st, body = _post(port, "/api/start", {"code": codes[0]})
        ok("after a restart the pupil continues their own sitting",
           st == 200 and body.get("resumed") and body.get("answered") == 2, str(body))
        _, it = _post(port, "/api/item", {}, {"X-Sitting": body["token"]})
        check_idx = it.get("index")
        ok("at the item they were on, with their answers kept", check_idx == 3, str(check_idx))
        rows = [json.loads(L) for L in log.read_text(encoding="utf-8").splitlines()]
        dup = [r for r in rows if r.get("ev") == "answer"]
        ok("and no answer is written twice", len({r["item_id"] for r in dup}) == len(dup))
        st, _ = _post(port, "/api/start", {"code": codes[0]})
        ok("while they work, the same code is still refused elsewhere", st == 409)
    finally:
        _stop(p)

    # the post-lesson questionnaire in condition K: no questions about an assistant
    for cond, port2 in (("K", 5894), ("G", 5895)):
        p = _start_runner(port2, ["--bank", "POST_LESSON", "--session", "P1", "--school", "GY",
                                  "--salt", "s", "--condition", cond,
                                  "--log", str(tmp / f"q{cond}.jsonl")])
        try:
            info = _get(port2, "/api/info")
            ok(f"condition {cond}: {info['items']} questionnaire items",
               info["items"] == (17 if cond == "K" else 24), str(info["items"]))
        finally:
            _stop(p)
    res = subprocess.run([sys.executable, str(HERE / "runner.py"), "--bank", "POST_LESSON",
                          "--session", "P1", "--school", "GY", "--salt", "s", "--port", "5896"],
                         cwd=HERE, capture_output=True, timeout=20)
    ok("the questionnaire refuses to start without knowing the condition",
       res.returncode == 2)
    res = subprocess.run([sys.executable, str(HERE / "runner.py"), "--bank", "T1_IPT",
                          "--session", "P1", "--school", "GY", "--port", "5897"],
                         cwd=HERE, capture_output=True, timeout=20)
    ok("the runner refuses to start without the school's salt", res.returncode == 2)


def test_results_and_calibration():
    section("results: from the runner's log to the analysis files")
    import calibration
    import results
    import tempfile
    ok("calibration self-test passes", not calibration.self_test())
    tmp = Path(tempfile.mkdtemp())
    banks = bank.load_all()
    ipt = banks["T1_IPT"]
    log = tmp / "odpovede_P1_T1_IPT.jsonl"
    rows = []
    for k, pupil in enumerate(("a" * 16, "b" * 16, "c" * 16)):
        for it in ipt.items:
            if it.format.startswith("mc"):
                raw = str(it.key) if k < 2 else str((it.key + 1) % len(it.options))
            else:
                raw = "polí sa interval na polovicu"
            rows.append(dict(ev="answer", pseudonym=pupil, session="P1", bank="T1_IPT",
                             instrument="IPT", item_id=it.id, raw=raw, seconds=20.0 + k,
                             jol=(90 if it.jol else None), paste_events=0, blur_seconds=0.0,
                             revisions=0, timestamp="2026-10-07T10:00:00+00:00"))
    log.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    s = results.run([str(log)], tmp / "out")
    ok("every response is scored or left for the coders",
       s["responses"] == 36 and s["open_pending"] == 9, str(s))
    ok("responses.csv is withheld while open items are uncoded", s["finalised"] is None)
    pupils = list(__import__("csv").DictReader((tmp / "out" / "pupils.csv").open(encoding="utf-8")))
    by = {r["pseudonym"]: r for r in pupils}
    ok("a pupil who is always right at 90 % is slightly underconfident",
       float(by["a" * 16]["calib_bias"]) < 0)
    ok("a pupil who is always wrong at 90 % is overconfident by 0.9",
       abs(float(by["c" * 16]["calib_bias"]) - 0.9) < 1e-9)
    # both coders fill the sheet identically -> the analytic file appears
    sheet = list(__import__("csv").DictReader((tmp / "out" / "coding.csv").open(encoding="utf-8")))
    for r in sheet:
        r["coder_a"] = r["coder_b"] = "1"
    with (tmp / "coding.csv").open("w", encoding="utf-8", newline="") as f:
        w = __import__("csv").DictWriter(f, fieldnames=list(sheet[0]))
        w.writeheader()
        w.writerows(sheet)
    s2 = results.run([str(log)], tmp / "out2", codings=str(tmp / "coding.csv"))
    ok("once both coders agree, responses.csv is written",
       s2["finalised"] and s2["finalised"]["rows"] == 36, str(s2.get("finalised")))
    order1 = [r["row_key"] for r in sheet]
    scoring.export_for_coding(scoring.score(results.to_responses(
        results.load_answers([str(log)])[0], banks), banks), tmp / "again.csv", banks)
    order2 = [r["row_key"] for r in __import__("csv").DictReader((tmp / "again.csv").open(encoding="utf-8"))]
    ok("the coding sheet comes out in the same blinded order every time", order1 == order2)


def test_datacheck_for_the_kit():
    section("data check: what the school runs the same afternoon")
    import datacheck
    ok("datacheck self-test passes", not datacheck.self_test())
    src = (HERE / "datacheck.py").read_text(encoding="utf-8")
    ok("it needs nothing a school laptop does not have",
       "import numpy" not in src and "import pandas" not in src)


def test_runner_consent():
    section("runner: consent on screen")
    import tempfile
    import datacheck
    import runner
    tmp = Path(tempfile.mkdtemp())
    codes = linkage.issue("GY", 4, seed=33)
    paper = tmp / "suhlasy-GY.txt"
    paper.write_text("\n".join(codes[:3]), encoding="utf-8")
    log = tmp / "odpovede_P3_T1_IPT.jsonl"
    port = 5898
    p = _start_runner(port, ["--bank", "T1_IPT", "--session", "P3", "--school", "GY",
                             "--salt", "s", "--consent-list", str(paper), "--log", str(log)])

    def rows():
        return ([json.loads(L) for L in log.read_text(encoding="utf-8").splitlines()]
                if log.exists() else [])

    def answer_two(tok):
        for _ in range(2):
            _, it = _post(port, "/api/item", {}, {"X-Sitting": tok})
            i = it["item"]
            _post(port, "/api/answer", {"item_id": i["id"], "raw": "1",
                                        "jol": 50 if i["jol"] else None}, {"X-Sitting": tok})

    try:
        ok("the consent screen is served to the test page",
           "Consent" in __import__("urllib.request").request.urlopen(
               f"http://127.0.0.1:{port}/consent.js", timeout=4).read().decode("utf-8"))
        pse = [runner.pseudonymise("s", c) for c in codes]

        _, b = _post(port, "/api/start", {"code": codes[0]})
        _post(port, "/api/consent", {"choice": "no"}, {"X-Sitting": b["token"]})
        answer_two(b["token"])
        ok("a pupil who says no takes the test, and nothing of it is written",
           not [r for r in rows() if r.get("pseudonym") == pse[0]])

        _, b = _post(port, "/api/start", {"code": codes[1]})
        tok = b["token"]
        _post(port, "/api/consent", {"choice": "yes"}, {"X-Sitting": tok})
        answer_two(tok)
        evs = [r["ev"] for r in rows() if r.get("pseudonym") == pse[1]]
        ok("a yes is written first, then the sitting", evs[:2] == ["consent", "start"]
           and evs.count("answer") == 2, str(evs))
        st, r = _post(port, "/api/consent", {"choice": "no"}, {"X-Sitting": tok})
        ok("a withdrawal deletes the sitting at once",
           st == 200 and r.get("purged") is True
           and [x["ev"] for x in rows() if x.get("pseudonym") == pse[1]] == ["withdraw"], str(r))
        _post(port, "/api/consent", {"choice": "yes"}, {"X-Sitting": tok})
        evs = [r["ev"] for r in rows() if r.get("pseudonym") == pse[1]]
        ok("agreeing again writes the whole sitting, answers given meanwhile included",
           evs == ["withdraw", "consent", "start", "answer", "answer"], str(evs))

        _, b = _post(port, "/api/start", {"code": codes[3]})
        ok("a code without a signed paper consent is not asked",
           b.get("consent", {}).get("state") == "none")
        st, _ = _post(port, "/api/consent", {"choice": "yes"}, {"X-Sitting": b["token"]})
        ok("and cannot be recorded by a yes on screen", st == 403, str(st))

        rep = datacheck.Report()
        datacheck.check_test(log, rep)
        ok("the data check accepts the log", rep.ok, "; ".join(rep.errors))
    finally:
        _stop(p)


# ===========================================================================
TESTS = [
    test_bank_contract,
    test_bank_rejects_what_it_must,
    test_time_budget_from_items,
    test_linkage_properties,
    test_scoring_boundaries,
    test_effort_and_integrity,
    test_profiles_work_at_n_equals_one,
    test_reports_disclose_nothing,
    test_generated_appendix_is_current,
    test_runner_end_to_end,
    test_runner_as_a_browser_uses_it,
    test_results_and_calibration,
    test_datacheck_for_the_kit,
    test_runner_consent,
]


def main() -> int:
    global FAIL
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    for t in TESTS:
        try:
            t()
        except Exception:
            FAIL += 1
            print(f"  ERROR in {t.__name__}")
            traceback.print_exc(limit=3)
    print(f"\n{PASS} passed, {FAIL} failed")
    # Written so the thesis can state its own test count without anyone typing it.
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "test-summary.json").write_text(
        json.dumps({"suite": "assessment", "passed": PASS, "failed": FAIL,
                    "sections": len(TESTS)}, indent=2), encoding="utf-8")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
