"""peqi_live.py -- the PEQI coding rule, applied at the moment a prompt is sent.

Why a third copy of the rule exists, and why it cannot drift
------------------------------------------------------------
The taxonomy already exists twice: `analysis/peqi.py` (the reference, which the
human coders' manual follows) and `PromptClassifier.java` (which scores captured
traffic). They drifted once, and the repair was to pin the specification as
data -- `cross_impl_corpus.json`, written by the Python reference, read by a
JUnit test.

The exercise client needs the label too, for one reason: the specification of
the study (chapter 5, "aké otázky mu kladie") asks the tool to record what kind
of question a pupil asks, and the client is the only producer that sees every
prompt together with the task it belongs to. So the label is attached to the
`prompt` event when the prompt is sent.

This module is a line-for-line port of `rule_classify` with no third-party
imports, because the client must run on a school laptop. It is held to the same
pinned corpus as the Java implementation (`test_peqi_live.py`), so the three
copies can be changed only together. The label written here is a convenience
for the class-level technical overview and for the export; the analysis of
record still recomputes it from `promptText`, exactly as before.

    L0 SOLVE  L1 VERIFY  L2 EXPLAIN  L3 ELABORATE  L4 SELF-EXPLAIN  X OFF-TASK
    PEQI = mean weight of on-task prompts, weights 0, .25, .5, .75, 1
"""
from __future__ import annotations

import re
import unicodedata

LEVELS = ("L0", "L1", "L2", "L3", "L4", "X")
WEIGHTS = {"L0": 0.00, "L1": 0.25, "L2": 0.50, "L3": 0.75, "L4": 1.00}
NAMES = {"L0": "riešenie", "L1": "overenie", "L2": "vysvetlenie",
         "L3": "rozšírenie", "L4": "vlastná úvaha", "X": "mimo úlohy"}

# --- the lexicons, copied verbatim from analysis/peqi.py --------------------
SOLVE_VERBS = r"\b(napis|naprogramuj|vyries|sprav|urob|daj mi|doplň|dopln|" \
              r"vypis|vytvor|implementuj|zostav|vygeneruj)\b"
ARTEFACT = r"(kod|funkci|pseudokod|riesenie|odpoved|program|implementaci|tabulku|" \
           r"skript|triedu|metodu)"
VERIFY = r"(je to spravne|je toto spravne|mam to dobre|skontroluj|over |overte|oprav|" \
         r"dobre alebo zle|v poriadku|je .* spravna|funguje toto|nefunguje)"
EXPLAIN = r"(preco|vysvetli|co znamena|co je to|ako funguje|co presne robi|ako sa pocita|" \
          r"naco |ako viem)"
ELABORATE = r"(kedy je|rozdiel medzi|porovnaj|v akych pripadoch|co by sa stalo|protipriklad|" \
            r"oplati|hranicne pripady|plati to aj|da sa .* pouzit aj|ako suvisi|" \
            r"ake su .* pripady|namiesto|ako sa zmeni|ako by sa zmenil|co sa stane ked|" \
            r"a nie |preco nestaci|preco nemozeme|preco sa nepouziva)"
SELFEXPL = r"(myslim si|myslim ze|podla mna|mam pocit|uvazujem|moja uvaha|moja hypoteza|" \
           r"moja domnienka|tipujem|chapem to tak|napisal som ze|napadlo mi|skusil som|" \
           r"kde robim chybu|kde sa mylim|kde mi to nesedi|je to tak|sedi to|" \
           r"suhlasis|potvrd mi|dava to zmysel|je ta uvaha|je moja uvaha|overil som si)"
OFFTASK = r"(ahoj|ako sa mas|datum|basen|do konca hodiny|emoji|ucitel|dejepis|\bhra\b|" \
          r"vtipne|test test|pocasie)"
DOMAIN = r"(pole|zlozit|algoritm|rekurz|memoiz|fibonacci|sort|triedeni|vyhladav|binarn|" \
         r"linearn|cyklus|iterac|log n|o\(|interval|zluc|krok|index|porovnan)"
DEMAND_VERB = r"(\b(napis|naprogramuj|vyries|dopln|vypis|vytvor|implementuj|zostav|" \
              r"vygeneruj|potrebujem|chcem)\b|sprav mi|urob mi|daj mi|posli mi|ukaz mi cel)"
ANSWER_ONLY = r"(len vysledok|len odpoved|iba vysledok|iba odpoved|bez vysvetlenia|" \
              r"nevysvetluj|aka je odpoved|aky je vysledok|aka je spravna odpoved)"
REASON = r"\b(lebo|pretoze|preto|takze|kedze|tym padom|z toho vyplyva|" \
         r"je chyba v tom|chyba je v tom|problem je v tom|je to tym ze|" \
         r"a teda|kvoli tomu|a preto)\b"
OWN_WORK = r"(tu je kod|tu je moj|toto som napisal|toto som spravil|mam tu|moj kod|" \
           r"moja funkcia|moj pseudokod|napisal som|spravil som|skusil som|" \
           r"mam v tabulke|som zoradil|moja odpoved)"
FAILURE = r"(nefunguje|nejde mi|hadze chybu|hodilo|vypisuje chybu|padne|spadne|" \
          r"zly vysledok|iny vysledok ako|nespravny vystup|sprav s tym|" \
          r"oprav|indexerror|chybu v tomto)"
REASONING_NOUN = r"(moja uvaha|ta uvaha|tu uvahu|je moja uvaha|moja hypoteza|" \
                 r"moja domnienka|odovodnenie|moj postup|moja diagnoza|" \
                 r"touto diagnozou|moje vysvetlenie)"
CONJECTURE = r"(by sa dalo|bolo by|malo by|mohlo by|dal by sa|co keby|keby som)"
DIAGNOSTIC = r"(kde robim chybu|kde sa mylim|kde mi to nesedi|co mi tu nesedi|" \
             r"kde je chyba v mojej|kde je chyba v mojom|preco mi to nevychadza|" \
             r"kde mam chybu)"
CODE = r"(def |for |while |return|\{|\}|==|<=|>=|\[i\]|;|\(\))"


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def _claim_span(t: str) -> str:
    m = re.search(SELFEXPL, t)
    if not m:
        return ""
    rest = t[m.end():]
    d = re.search(DEMAND_VERB, rest)
    return rest[:d.start()] if d else rest


def _has_derivation(span: str, has_code: bool) -> bool:
    if has_code:
        return False
    return (len(re.findall(r"\d+", span)) >= 2
            or bool(re.search(r"\d\s*[\^*/+=<>-]", span)))


def _is_veneer(t: str) -> bool:
    """An epistemic marker with no argument behind it (see analysis/peqi.py)."""
    if not re.search(SELFEXPL, t):
        return False
    span = _claim_span(t)
    has_code = bool(re.search(CODE, t))
    justified = (bool(re.search(REASON, span))
                 or bool(re.search(REASONING_NOUN, t))
                 or bool(re.search(CONJECTURE, span))
                 or bool(re.search(DIAGNOSTIC, t))
                 or _has_derivation(span, has_code))
    return not (len(span.split()) >= 3 and justified)


def classify(text: str) -> str:
    """The coders' decision ladder; the first rule that fires wins."""
    t = normalise(text)
    has_code = bool(re.search(CODE, t))
    solve = bool(re.search(SOLVE_VERBS, t)) and bool(re.search(ARTEFACT, t))
    if re.search(OFFTASK, t) and not re.search(DOMAIN, t):
        return "X"
    if re.search(ANSWER_ONLY, t):
        return "L0"
    if re.search(SELFEXPL, t) and not _is_veneer(t):
        return "L4"
    if re.search(OWN_WORK, t) and re.search(FAILURE, t):
        return "L1"
    if re.search(ELABORATE, t):
        return "L3"
    if re.search(EXPLAIN, t):
        return "L2"
    if re.search(VERIFY, t) or re.search(FAILURE, t) or (has_code and not solve):
        return "L1"
    demand = bool(re.search(DEMAND_VERB, t)) and bool(re.search(ARTEFACT, t))
    if demand or re.search(SOLVE_VERBS, t):
        return "L0"
    return "L1"


def session_index(levels: list[str]) -> dict:
    """PEQI and its companions for one pupil's prompts. None, never zero, when
    there is nothing on task to average -- a pupil who asked nothing has no
    prompt quality, which is not the same as the lowest one."""
    on = [lv for lv in levels if lv != "X"]
    counts = {lv: levels.count(lv) for lv in LEVELS}
    if not on:
        return dict(n_prompts=len(levels), n_on_task=0, peqi=None,
                    offload_rate=None, generative_rate=None,
                    off_task_rate=(1.0 if levels else None), counts=counts)
    n = len(on)
    return dict(
        n_prompts=len(levels), n_on_task=n,
        peqi=round(sum(WEIGHTS[lv] for lv in on) / n, 4),
        offload_rate=round(sum(1 for lv in on if lv in ("L0", "L1")) / n, 4),
        generative_rate=round(sum(1 for lv in on if lv in ("L2", "L3", "L4")) / n, 4),
        off_task_rate=round((len(levels) - n) / len(levels), 4),
        counts=counts)
