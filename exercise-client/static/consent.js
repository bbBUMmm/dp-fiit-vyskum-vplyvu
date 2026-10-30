/* consent.js -- the consent screen: one component for the lesson and the test.
 *
 * The server decides what is recorded; this file only asks and shows. It is one
 * file for both apps (the test runner serves it from here), so a pupil sees the
 * same words and the same buttons in a lesson and in a test. It styles itself
 * from the design tokens both pages define, with fallbacks.
 *
 * What it keeps to (EDPB Guidelines 05/2020 on consent):
 *   - "Súhlasím" and "Nesúhlasím" look the same and sit side by side; neither is
 *     pre-selected or pre-focused, so refusing is exactly as easy as agreeing;
 *   - the first question cannot be dismissed without an answer, and after a no
 *     the pupil works exactly like everyone else;
 *   - nothing on the page shows the choice to a neighbour: the "Súhlas" button
 *     is the same for everyone, and the app answers both choices the same way.
 *
 *   Consent.ask({ view, send })     -> Promise<view>  the first question
 *   Consent.manage({ view, send })  -> void           status, withdraw, agree later
 *
 * `view` is what the server returns ({state, version, text}); `send(choice)`
 * posts "yes" / "no" (or null to read) and resolves with the new view.
 */
(function () {
  "use strict";

  const CSS = `
.cs-layer{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:16px;
  background:rgba(15,17,23,.55);overflow-y:auto}
.cs-card{width:100%;max-width:560px;max-height:calc(100vh - 32px);max-height:calc(100dvh - 32px);overflow-y:auto;
  background:var(--surface,#fff);color:var(--ink,#111827);border:1px solid var(--line,#e3e6ee);border-radius:16px;
  box-shadow:var(--shadow,0 10px 30px rgba(0,0,0,.2));padding:24px;font:16px/1.55 var(--font,system-ui,sans-serif);text-align:left}
.cs-card h2{font-size:1.25rem;line-height:1.3;margin:0 0 10px;outline:none}
.cs-lead{margin:0 0 6px;color:var(--ink-2,#374151)}
.cs-sec{margin:14px 0 0}
.cs-sec h3{font-size:.75rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted,#6b7280);margin:0 0 4px}
.cs-sec ul{margin:0;padding-left:20px}
.cs-sec li{margin:3px 0}
.cs-foot{position:sticky;bottom:-24px;margin:16px -24px -24px;padding:14px 24px 16px;background:var(--surface,#fff);
  border-top:1px solid var(--line,#e3e6ee);box-shadow:0 -10px 18px -14px rgba(0,0,0,.35)}
.cs-q{font-weight:700;margin:0 0 10px}
.cs-choices{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cs-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
.cs-btn{appearance:none;font:inherit;font-weight:650;min-height:48px;padding:10px 16px;border-radius:12px;cursor:pointer;
  background:var(--surface,#fff);color:var(--primary,#3f3cbb);border:2px solid var(--primary,#3f3cbb)}
.cs-btn:hover:not(:disabled){background:var(--primary-soft,#eceafe)}
.cs-btn:focus-visible{outline:none;box-shadow:var(--focus,0 0 0 3px rgba(63,60,187,.35))}
.cs-btn:disabled{opacity:.55;cursor:not-allowed}
.cs-btn.cs-solid{background:var(--primary,#3f3cbb);color:var(--primary-ink,#fff)}
.cs-btn.cs-solid:hover:not(:disabled){background:var(--primary-hover,#34319e)}
.cs-btn.cs-quiet{border-color:var(--line-strong,#cdd2de);color:var(--ink-2,#374151)}
.cs-err{color:var(--bad,#b42318);font-size:.92rem;min-height:1.2em;margin-top:10px}
.cs-status{padding:12px 14px;border-radius:12px;background:var(--surface-2,#f0f2f8);margin:0 0 6px}
.cs-meta{color:var(--muted,#6b7280);font-size:.75rem;margin:14px 0 0}
.cs-card details{margin-top:12px}
.cs-card summary{cursor:pointer;font-weight:600;color:var(--primary,#3f3cbb)}
@media (max-width:560px){.cs-layer{padding:8px}.cs-card{padding:18px;border-radius:14px}
  .cs-foot{bottom:-18px;margin:14px -18px -18px;padding:12px 18px 14px}}
@media (prefers-reduced-motion:reduce){.cs-layer *{transition:none!important}}
`;

  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const c of kids.flat()) {
      if (c !== null && c !== undefined && c !== false) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return e;
  }

  let styled = false;
  function addStyle() {
    if (styled) return;
    styled = true;
    document.head.appendChild(h("style", { text: CSS }));
  }

  // One dialog at a time. Focus goes to the heading, not to a button: a focused
  // "Súhlasím" is one Enter away from an answer nobody read.
  let current = null;
  function dialog(build, dismissable) {
    addStyle();
    if (current) current.close();
    const before = document.activeElement;
    const card = h("div", { class: "cs-card", role: "dialog", "aria-modal": "true", "aria-labelledby": "cs-title" });
    const layer = h("div", { class: "cs-layer" }, card);
    const onKey = (e) => {
      if (e.key === "Escape" && dismissable) { e.preventDefault(); close(); return; }
      if (e.key !== "Tab") return;
      const f = [...card.querySelectorAll("button:not([disabled]), summary, [tabindex='-1']")];
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      else if (!card.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
    };
    function close() {
      layer.remove();
      document.removeEventListener("keydown", onKey, true);
      if (current && current.layer === layer) current = null;
      if (before && before.focus && document.contains(before)) before.focus();
    }
    document.addEventListener("keydown", onKey, true);
    document.body.appendChild(layer);
    current = { layer, close };
    build(card, close);
    const title = card.querySelector("#cs-title");
    if (title) title.focus();
    return close;
  }

  function title(text) { return h("h2", { id: "cs-title", tabindex: "-1", text }); }

  function sections(t) {
    const sec = (head, items) => h("div", { class: "cs-sec" },
      h("h3", { text: head }), h("ul", {}, items.map((x) => h("li", { text: x }))));
    return [sec(t.recordedTitle, t.recorded), sec(t.notRecordedTitle, t.notRecorded), sec(t.rightsTitle, t.rights)];
  }

  function message(e) {
    return (e && e.message) || "Nepodarilo sa uložiť. Skús to znova.";
  }

  // ---------------------------------------------------------------- ask
  function ask({ view, send }) {
    return new Promise((resolve) => {
      const t = view.text;
      dialog((card, close) => {
        if (view.state === "none") {
          const go = h("button", { class: "cs-btn cs-solid", type: "button" }, t.buttons.continue);
          go.addEventListener("click", () => { close(); resolve(view); });
          card.append(title(t.noPaper.title), h("p", { class: "cs-lead", text: t.noPaper.lead }), h("div", { class: "cs-row" }, go));
          return;
        }
        const err = h("div", { class: "cs-err", role: "alert" });
        const yes = h("button", { class: "cs-btn", type: "button" }, t.buttons.yes);
        const no = h("button", { class: "cs-btn", type: "button" }, t.buttons.no);
        const choose = async (choice) => {
          yes.disabled = no.disabled = true;
          err.textContent = "";
          try {
            const v = await send(choice);
            close();
            resolve(v);
          } catch (e) {
            err.textContent = message(e);
            yes.disabled = no.disabled = false;
          }
        };
        yes.addEventListener("click", () => choose("yes"));
        no.addEventListener("click", () => choose("no"));
        // the question and both answers stay in view while the text scrolls
        card.append(
          title(t.title),
          h("p", { class: "cs-lead", text: t.lead }),
          ...sections(t),
          h("p", { class: "cs-meta", text: `Verzia textu ${view.version}` }),
          h("div", { class: "cs-foot" },
            h("p", { class: "cs-q", text: t.question }),
            h("div", { class: "cs-choices" }, yes, no),
            err));
      }, false);
    });
  }

  // -------------------------------------------------------------- manage
  const STATUS = {
    yes: "Záznam je zapnutý — súhlasil/a si.",
    no: "Záznam je vypnutý — o tebe sa nič neukladá.",
    pending: "Ešte si sa nerozhodol/nerozhodla.",
    none: "Záznam je vypnutý — pre tvoj kód nie je podpísaný písomný súhlas.",
  };

  function manage({ view, send, onChange }) {
    dialog((card, close) => {
      const body = h("div");
      card.append(title("Súhlas so záznamom"), body);

      function buttons(row) { return [...row.querySelectorAll("button")]; }

      async function act(choice, row, err) {
        buttons(row).forEach((b) => { b.disabled = true; });
        err.textContent = "";
        try {
          const v = await send(choice);
          if (onChange) onChange(v);
          const where = v.text.where;
          let note = "Záznam je zapnutý.";
          if (choice === "no") {
            note = v.purged === false
              ? `Súhlas je odvolaný a nič nové sa už nezaznamenáva. Čo sa ${where} zaznamenalo, sa vymaže po skončení.`
              : `Súhlas je odvolaný. Všetko, čo sa o tebe ${where} zaznamenalo, je vymazané.`;
          }
          render(v, note);
        } catch (e) {
          err.textContent = message(e);
          buttons(row).forEach((b) => { b.disabled = false; });
        }
      }

      function confirmWithdraw(v) {
        const err = h("div", { class: "cs-err", role: "alert" });
        const row = h("div", { class: "cs-row" });
        row.append(
          h("button", { class: "cs-btn cs-solid", type: "button", onclick: () => act("no", row, err) }, "Áno, odvolať a vymazať"),
          h("button", { class: "cs-btn cs-quiet", type: "button", onclick: () => render(v) }, "Späť"));
        body.replaceChildren(
          h("p", { class: "cs-status", text: `Hneď sa vymaže všetko, čo sa o tebe ${v.text.where} zaznamenalo, a ďalej sa už nič nezaznamená. Pracovať budeš ďalej rovnako ako doteraz.` }),
          row, err);
      }

      function render(v, note) {
        view = v;
        const err = h("div", { class: "cs-err", role: "alert" });
        const row = h("div", { class: "cs-row" });
        if (v.state === "yes") {
          row.append(h("button", { class: "cs-btn", type: "button", onclick: () => confirmWithdraw(v) }, "Odvolať súhlas"));
        } else if (v.state === "no" || v.state === "pending") {
          row.append(h("button", { class: "cs-btn", type: "button", onclick: () => act("yes", row, err) }, "Súhlasím so záznamom"));
        }
        row.append(h("button", { class: "cs-btn cs-quiet", type: "button", onclick: close }, "Zavrieť"));
        const parts = [h("p", { class: "cs-status", role: note ? "status" : null, text: note || STATUS[v.state] || "" })];
        if (v.state !== "none") {
          parts.push(h("details", {}, h("summary", { text: "Čo sa zaznamenáva a čo nie" }), ...sections(v.text)));
        }
        parts.push(row, err, h("p", { class: "cs-meta", text: `Verzia textu ${v.version}` }));
        body.replaceChildren(...parts);
      }

      render(view);
    }, true);
  }

  window.Consent = { ask, manage };
})();
