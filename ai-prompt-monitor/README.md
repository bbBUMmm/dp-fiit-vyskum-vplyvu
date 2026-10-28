# AI Prompt Monitor

Walking-skeleton CLI tool that runs a local HTTPS MITM proxy and captures the request bodies
(prompts) that a browser sends to configured AI service URLs.

Built as the technical artefact for a Master's thesis at FIIT STU Bratislava
(*Výskum vplyvu generických a adaptívnych nástrojov umelej inteligencie v školskom prostredí*).

> **Status — read this first.** The tool is mid-migration between two capture layers.
>
> - **`src/` (Java, LittleProxy) — superseded.** It boots, it proxies, and it captures POST
>   bodies. Verified against ChatGPT in June 2026: it captures autocomplete and conversation
>   preparation, but the send endpoint returns **400 at the proxy** and streamed responses are
>   never seen. Root cause: LittleProxy 1.1.2 (2019) supports neither HTTP/2 nor WebSocket over
>   terminated TLS, and both are load-bearing in every current conversational interface. The
>   fault is the library choice, not the application logic — which is why the application logic
>   is kept.
> - **`mitm/` (Python, mitmproxy) — the replacement, and where new work goes.** It matches the
>   allow-list, extracts the pupil's own text from the request body, scrubs personal data
>   against a school-supplied roster, and appends JSON Lines. 29 tests, no mitmproxy needed to
>   run them: `python mitm/test_capture.py`. See [`mitm/README.md`](mitm/README.md).
>
> The two layers meet at a JSON Lines file. The Java side keeps the parts that are the subject
> of the thesis — pseudonymisation, prompt classification, PEQI, reporting — and tails that
> file instead of proxying. Most of this README still describes the Java proxy; treat its
> capture sections as historical, and its configuration, output-format and ethics sections as
> current.

---

## How it works (one paragraph)

The tool starts a local HTTP proxy on `127.0.0.1:8080`. You configure your browser to use it as
both HTTP and HTTPS proxy. When the browser opens an HTTPS connection through the proxy, the
proxy terminates TLS using its own self-signed certificate — which the browser only trusts
because you have explicitly imported the proxy's root CA. With TLS terminated, the proxy can
read the decrypted request, check the URL against your patterns, and if it matches, persist the
request body (which is where the prompt lives) into a JSON-lines file. The request then
continues unchanged to the real service, so the user's experience is untouched.

---

## Requirements

- Java 17+
- Maven 3.8+
- A browser whose proxy and certificate trust you can configure (Firefox is easiest)

---

## Build

```bash
mvn clean package
```

Produces `target/ai-prompt-monitor.jar` — a runnable fat-jar containing all dependencies.

## Run

```bash
# Start the proxy
java -jar target/ai-prompt-monitor.jar monitor --config config/urls.example.yaml

# In another terminal, after capturing some traffic:
java -jar target/ai-prompt-monitor.jar report --dir captures
```

`Ctrl+C` shuts the proxy down cleanly.

---

## First-run setup (one-time per machine)

### 1. Generate the CA by running the proxy once

Start the tool with the command above. On first run, the bundled `SelfSignedMitmManager` writes
a CA keystore and certificate to your home directory (`~/.littleproxy/` or similar — watch the
logs for the path; LittleProxy logs it). Stop the proxy with `Ctrl+C`.

> ⚠️ The `SelfSignedMitmManager` **regenerates the CA every time the process starts** unless its
> keystore is preserved across runs. For a stable CA suitable for school deployment, see
> [Roadmap → Production CA](#roadmap-toward-thesis-deployment).

### 2. Export the CA certificate

Find the generated `.pem` / `.crt` file in the proxy's working directory (or the path it logged).
This is the public part you need to install on the machine.

### 3. Import the CA into the browser trust store

**Firefox (recommended for development — it has its own trust store, isolated from the OS):**

1. `about:preferences#privacy` → scroll to *Certificates* → *View Certificates...*
2. *Authorities* tab → *Import...*
3. Select the `.pem` file.
4. Tick **"Trust this CA to identify websites"**. OK.

**Chrome / Edge (uses the OS trust store on Windows and macOS):**

- **Windows:** Run `certmgr.msc` → *Trusted Root Certification Authorities* → *Certificates* →
  right-click → *All Tasks* → *Import...*. Restart the browser.
- **macOS:** Open *Keychain Access* → *System* keychain → drag the `.pem` in → double-click it
  → *Trust* → set *When using this certificate* to *Always Trust*. Restart the browser.
- **Linux (Ubuntu/Debian):** Copy the cert to `/usr/local/share/ca-certificates/` (rename to
  `.crt`) → `sudo update-ca-certificates`. Chrome on Linux also has its own NSS DB; the simplest
  option is to import via Chrome's *Settings → Privacy and security → Security → Manage device
  certificates*.

### 4. Configure the browser to use the proxy

**Firefox:** *Settings → Network Settings → Manual proxy configuration* → HTTP Proxy
`127.0.0.1` Port `8080`, tick *Also use this proxy for HTTPS*.

**Chrome:** Inherits OS settings. Easiest: launch Chrome with a proxy switch:
```bash
chrome --proxy-server="http://127.0.0.1:8080"
```
Or use a PAC file / OS-level proxy config.

### 5. Disable HTTP/3 (QUIC) — critical

HTTP/3 runs over UDP and **bypasses HTTP proxies entirely**. Without disabling it, traffic to
Google services (and increasingly others) will silently leave the proxy unaware. Your captures
will be incomplete and you won't notice.

- **Firefox:** `about:config` → `network.http.http3.enable` → `false`.
- **Chrome:** `chrome://flags/#enable-quic` → *Disabled*. Restart.

Document this step in your thesis methodology — it materially affects what you do and don't
capture.

---

## Verifying it works

1. Start the proxy.
2. Open `https://chatgpt.com` (or any service in your config) in the configured browser.
3. Send a short test message like *"hello world"*.
4. Watch the proxy log — you should see a line like:
   ```
   18:42:11.337 INFO  s.s.f.a.proxy.CapturingFiltersSource - Captured POST https://chatgpt.com/backend-api/conversation (3421 bytes body)
   ```
5. `cat captures/captures-YYYY-MM-DD.jsonl | head -1 | jq` — you should see the JSON record with
   the body field containing the JSON envelope sent by the ChatGPT web app, with your "hello
   world" prompt somewhere inside it.

If you don't see a capture: see [Troubleshooting](#troubleshooting).

---

## Configuration

See `config/urls.example.yaml`. The only field you'll change regularly is `url_patterns`.

Patterns are substring matches against `host + path` (e.g. `chatgpt.com/backend-api/conversation`).
Keep them specific enough to avoid catching unrelated traffic (analytics, telemetry, asset loads)
but loose enough to survive minor path changes.

**To add a new AI service:** open it with DevTools → Network, send a test prompt, find the
POST request whose body contains your prompt text, take a distinctive substring of its URL.

---

## Output format

One JSON object per line, daily rotated as `captures/captures-YYYY-MM-DD.jsonl`:

```json
{
  "timestamp": "2026-02-14T17:23:08.115Z",
  "host": "chatgpt.com",
  "url": "https://chatgpt.com/backend-api/conversation",
  "method": "POST",
  "contentType": "application/json",
  "body": "{\"action\":\"next\",\"messages\":[{\"id\":\"...\",\"author\":{\"role\":\"user\"},\"content\":{\"content_type\":\"text\",\"parts\":[\"hello world\"]}}]}",
  "captureId": "5a8e1c2f-..."
}
```

JSONL is trivially loadable into pandas (`pd.read_json('...jsonl', lines=True)`), R, jq, or DuckDB.

---

## Architecture

```
+----------+   plaintext   +-------------------------+   real TLS   +-----------------+
| Browser  | ------------> | Java proxy (8080)       | -----------> | chatgpt.com etc |
| (Firefox |   over TLS    |                         |              +-----------------+
| /Chrome) |   that proxy  | LittleProxy             |
+----------+   terminates  |  + SelfSignedMitmManager|
                           |  + CapturingFilters     |
                           +-----------+-------------+
                                       |
                                       v
                              +-----------------+
                              | captures/*.jsonl|
                              +-----------------+
```

Key classes:

| Class | Role |
|---|---|
| `Main` | picocli root command, dispatches subcommands |
| `MonitorCommand` | Starts the proxy, blocks until Ctrl+C |
| `ReportCommand` | Scans the JSONL store and prints a summary |
| `Config` | YAML config loader |
| `ProxyRunner` | Wires LittleProxy + MITM manager + filter source |
| `CapturingFiltersSource` | The MITM filter — matches URLs, captures bodies |
| `JsonlStore` | Append-only daily-rotated JSONL persistence |
| `CapturedRequest` | The persisted record |

---

## Limitations

These are the things you must document in chapter 4 of the thesis, and either work around or
explicitly scope out:

1. **HTTP/3 / QUIC bypasses the proxy.** Must be disabled per browser. See setup §5.
2. **Self-signed CA is regenerated every process start.** Fine for local dev, unusable for
   multi-machine deployment. See [Roadmap](#roadmap-toward-thesis-deployment).
3. **WebSocket prompts not captured.** Some services stream over `wss://`. The proxy sees the
   WebSocket frames after the upgrade, but the current filter only inspects `FullHttpRequest`.
   To add: implement `proxyToServerRequest`/frame-level handling in the filter.
4. **Certificate pinning** is generally not enforced by major browsers for AI service domains
   today, but Chrome's built-in HSTS preload list does enforce it for some Google domains. If a
   service silently refuses to talk through the proxy, suspect pinning.
5. **All HTTPS through the proxy is MITM'd, not just configured hosts.** The proxy *can* decrypt
   any HTTPS. The user's banking, email, healthcare traffic all flow through it in plaintext to
   the proxy process. We don't *store* it (we filter by URL before persisting), but the
   capability is there. This must be in the consent form.
6. **No deduplication of repeated chunked sends.** If the browser retries a request, you'll get
   it twice. Handle in analysis.
7. **Mobile / app-only AI tools are out of scope.** Mobile apps often enforce strict certificate
   pinning and won't accept the proxy's CA.

---

## Troubleshooting

**Nothing gets captured.**
- Confirm browser is actually using the proxy: visit `https://httpbin.org/ip` (which echoes your
  IP) and check the proxy log shows the request. If not, browser proxy is misconfigured.
- HTTPS site shows a certificate warning: CA cert isn't trusted in this browser. Re-import.
- HTTPS site loads but no captures: URL pattern doesn't match. Re-check with DevTools → Network.

**`SelfSignedMitmManager` cannot be resolved.**
- Confirm `littleproxy:2.7.0` is in your dependencies; the class is at
  `org.littleshoot.proxy.extras.SelfSignedMitmManager`.

**Browser shows `ERR_PROXY_CONNECTION_FAILED`.**
- Proxy isn't running, or you set `withAllowLocalOnly(true)` but are connecting from another
  machine. Walking-skeleton-mode is intentionally localhost-only.

**Captures suddenly stop for one service.**
- They changed their endpoint. Re-discover with DevTools, update `url_patterns`.

---

## Roadmap toward thesis deployment

The walking skeleton proves the technical pipeline works. For chapter 5 (pilot + full
deployment) you'll need:

### Stable production CA
Replace `SelfSignedMitmManager` with a manager that loads a pre-generated CA keystore. Generate
once with:
```bash
keytool -genkeypair -alias mitm -keyalg RSA -keysize 4096 -validity 730 \
        -keystore mitm-ca.jks -storepass changeit \
        -dname "CN=AI Prompt Monitor CA (FIIT STU), O=STU Bratislava, OU=DP research"
keytool -exportcert -alias mitm -keystore mitm-ca.jks -storepass changeit \
        -rfc -file mitm-ca.pem
```
Then implement a `MitmManager` that wraps this keystore — see the `ganskef/LittleProxy-mitm`
extension for a working reference implementation (the package is unmaintained but the code is
correct and small enough to vendor in).

Ship `mitm-ca.pem` to every school machine alongside an install script.

### Scoped MITM
Modify `CapturingFiltersSource` to skip MITM for hosts that don't match any URL pattern — let
non-target HTTPS tunnel transparently. This limits the privacy attack surface to only the
research domains and is much easier to defend in front of an ethics committee. Use
`HttpFilters#proxyToServerResolutionStarted` / proxy CONNECT handling, or a custom `MitmManager`
that returns null for non-listed hosts.

### Pseudonymisation at capture time
Add a `deviceHash` field (HMAC-SHA256 of `machine-id + study-secret`, truncated). Never store
raw IPs, hostnames, MAC, or usernames. The study coordinator holds the linking table out of
band.

### Storage hardening
Move from JSONL to SQLite (`org.xerial:sqlite-jdbc`) with a single `captures` table. Add file
encryption at rest (AES-256, key held by the study coordinator).

### Ethics + GDPR
- Informed consent forms (separate forms for students and parents/legal guardians for minors).
- DPIA — Finland mandates this for educational AI tools (see thesis §7); use that as a justification.
- Retention policy: e.g. raw captures deleted within N days of analysis, aggregates retained.
- Ethics committee approval at FIIT — start this early, it can take a month.
- Reference Slijepcevic & Yaylali [6] for an example of how peer-reviewed AI-in-education
  studies handle the consent/logging procedure.

### Behavioural indicators (chapter 5 analysis)
The captures already give you enough to derive the indicators called out in §8 of the handover
document:
- **Inter-prompt interval** = time between consecutive captures from the same device. Short
  intervals indicate the "short memory span" pattern.
- **Prompt length distribution** = `len(body)` parsed for the actual user-text field.
- **Editing/follow-up patterns** = clustering of related prompts.

Add a separate `analyze` subcommand later for these — keep `report` as the simple sanity-check.

---

## License

Same Apache 2.0 as LittleProxy.

---

## Citing in the thesis

The methodological framing (vendor-independent network-level prompt capture as a gap not
addressed by Lee et al. [4], Slijepcevic & Yaylali [6], or Gerlich [5]) is described in the
analysis chat that produced this skeleton. See chapter 4, section "Návrh architektúry".
