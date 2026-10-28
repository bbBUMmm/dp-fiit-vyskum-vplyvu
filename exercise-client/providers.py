"""providers.py -- the model, behind one interface.

Conditions G and A must use the SAME model. That is the design's central
control, and the cheapest way to break it by accident is to let two code paths
each construct their own client. So there is one interface, one configured
provider, and the only difference between the conditions is the message list
handed to it (see pedagogy.build_messages vs build_messages_generic).

Three implementations:

  StubProvider    deterministic, no network, no key. Used by the tests and by
                  the pilot rehearsal, so the whole client can be exercised in
                  a classroom with no internet and no cost.
  OpenAIProvider  any OpenAI-compatible chat endpoint, via stdlib urllib.
  EchoProvider    returns the prompt back; used to verify the capture layer
                  sees what it should without spending anything.

No third-party dependencies anywhere: this has to run on a school laptop that
nobody is allowed to install packages on.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class Reply:
    text: str
    provider: str
    model: str
    latency_ms: int
    error: str | None = None


class Provider:
    name = "base"

    def complete(self, messages: list[dict], max_tokens: int = 300) -> Reply:
        raise NotImplementedError


# --------------------------------------------------------------------------
class StubProvider(Provider):
    """Deterministic replies, no network.

    The replies are shaped like a Socratic tutor's, so a rehearsal exercises the
    same code paths as a live session -- including the output guard, which must
    see plausible text to be a meaningful test. Determinism is on purpose: a
    pilot that cannot be re-run identically cannot be debugged.
    """

    name = "stub"

    DIAGNOSTIC = [
        "Kde presne si uviazol? Napíš mi posledný krok, ktorý ti dával zmysel.",
        "Čo v tejto úlohe už vieš určiť s istotou?",
        "Skús mi povedať, čo si skúsil a čo ti z toho vyšlo.",
    ]
    LADDER = {
        1: ["Pripomeň si, čo musí platiť o poli, aby sa dalo deliť na polovice.",
            "Zamysli sa nad tým, čo sa s intervalom stane po jednom porovnaní."],
        2: ["Pozri sa na krok, v ktorom posúvaš hranicu. Ktorú z nich meníš a prečo?",
            "Skontroluj, čo sa stane s premennou, ktorú si naposledy zmenil."],
        3: ["Predstav si kratšie pole, napríklad [2, 5, 9]. Ako by si v ňom "
            "hľadal 9? Ten istý postup skús preniesť na svoju úlohu.",
            "Vezmi si analogický prípad s troma prvkami a sleduj, ako sa mení interval."],
        4: ["Rozdelíme to. Najprv mi povedz len jedno: ktorý prvok sa porovná "
            "ako prvý? Keď to budeme mať, ideme ďalej.",
            "Urobme prvý krok spolu: aká je hodnota premennej stred na začiatku?"],
    }
    REFUSAL = ("Hotové riešenie ti nedám. Povedz mi radšej, ktorý krok ti "
               "nesedí, a pôjdeme od neho.")

    def complete(self, messages: list[dict], max_tokens: int = 300) -> Reply:
        t0 = time.time()
        user = next((m["content"] for m in reversed(messages)
                     if m.get("role") == "user"), "")
        system = next((m["content"] for m in messages
                       if m.get("role") == "system"), "")
        n_user = sum(1 for m in messages if m.get("role") == "user")

        seed = int(hashlib.sha1(user.encode("utf-8")).hexdigest()[:8], 16)

        if not system:
            # condition G: no pedagogy, so the stub answers as a plain assistant
            text = ("Binárne vyhľadávanie funguje tak, že porovná stredný prvok "
                    "a podľa výsledku zahodí polovicu intervalu.")
        elif _asks_for_solution(user):
            text = self.REFUSAL
        elif n_user <= 1:
            text = self.DIAGNOSTIC[seed % len(self.DIAGNOSTIC)]
        else:
            level = _hint_level_from_system(system)
            pool = self.LADDER.get(level, self.LADDER[1])
            text = pool[seed % len(pool)]

        return Reply(text, self.name, "stub-1",
                     int((time.time() - t0) * 1000))


def _asks_for_solution(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ("napis mi", "napíš mi", "daj mi riesenie",
                                "daj mi riešenie", "cely kod", "celý kód",
                                "hotove riesenie", "hotové riešenie",
                                "ignoruj", "vyries to", "vyrieš to"))


def _hint_level_from_system(system: str) -> int:
    for token in system.split():
        if token.isdigit() and 1 <= int(token) <= 4:
            return int(token)
    return 1


# --------------------------------------------------------------------------
class EchoProvider(Provider):
    name = "echo"

    def complete(self, messages: list[dict], max_tokens: int = 300) -> Reply:
        user = next((m["content"] for m in reversed(messages)
                     if m.get("role") == "user"), "")
        return Reply(f"[echo] {user}", self.name, "echo-1", 0)


# --------------------------------------------------------------------------
class OpenAIProvider(Provider):
    """Any OpenAI-compatible chat endpoint, over stdlib urllib.

    The endpoint is configurable so the study can be run against a provider
    that processes data inside the EU, which the data-protection assessment
    requires.
    """

    name = "openai"

    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None, timeout: float = 20.0):
        self.model = model or os.environ.get("STUDY_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.environ.get("STUDY_BASE_URL")
                         or "https://api.openai.com/v1")
        self.api_key = api_key or os.environ.get("STUDY_API_KEY", "")
        self.timeout = timeout

    def complete(self, messages: list[dict], max_tokens: int = 300) -> Reply:
        t0 = time.time()
        if not self.api_key:
            return Reply("", self.name, self.model, 0,
                         error="STUDY_API_KEY is not set")
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            return Reply(text, self.name, self.model,
                         int((time.time() - t0) * 1000))
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as e:
            # A lesson must not stop because an API did. The caller shows a
            # fallback and the incident goes into the fidelity log.
            return Reply("", self.name, self.model,
                         int((time.time() - t0) * 1000), error=str(e))


# --------------------------------------------------------------------------
def get_provider(name: str | None = None) -> Provider:
    name = (name or os.environ.get("STUDY_PROVIDER", "stub")).lower()
    return {"stub": StubProvider, "echo": EchoProvider,
            "openai": OpenAIProvider}.get(name, StubProvider)()
