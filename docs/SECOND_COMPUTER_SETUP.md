# Connecting a second computer to the Ollama bridge

Quick walkthrough for pointing another Windows PC or an Intel Mac at the home
model host, once [LOCAL_LLM_REMOTE_ACCESS.md](LOCAL_LLM_REMOTE_ACCESS.md) has
been set up on that host. This machine's endpoint is:

```
https://ollama.verseviewllm.dpdns.org
```

The service token (`CF-Access-Client-Id` / `CF-Access-Client-Secret`) is not
recorded in this repo — it's a shared secret, not configuration. Get the pair
from whoever set up the tunnel and keep it out of anything that isn't the
Extra Headers field below.

---

## Before you start

- The endpoint address above (same on every remote computer, never changes).
- The service token pair, as one JSON object:
  ```json
  {"CF-Access-Client-Id": "…", "CF-Access-Client-Secret": "…"}
  ```
- VerseView installed on the remote computer.

Treat the token like a password. Anyone holding both header values can call
the home Ollama through the tunnel — send it over something private.

---

## Windows

1. Open VerseView → **Settings** → scroll to **Options** → expand →
   scroll to **Advanced Settings** → expand → scroll to
   **Local LLM (Ollama)**.
2. Check **Use Local LLM** if it isn't already.
3. **Local Ollama Endpoint** → `https://ollama.verseviewllm.dpdns.org`
4. **Extra Headers** → paste the token JSON above. Leave **Auth Token** blank.
5. Click **Test Connection** → expect
   `Local LLM test OK — Connected to https://ollama.verseviewllm.dpdns.org`.

## Intel Mac

The `.app` release is ad-hoc signed but not notarized, so Gatekeeper
quarantines and translocates it on first launch — that shows up as the app
crashing or refusing to open. The **Raw Executable** folder in the same
release zip is the identical program without that layer:

```bash
cd ~/Downloads/"VerseView-Mac-Intel-Release"/"VerseView Detector (Raw Executable)"
./"VerseView Detector"
```

Adjust the first path if you unzipped somewhere other than Downloads. Keep
that Terminal window open — closing it quits the app.

Once it's running, the settings path and the remaining steps are identical to
Windows above (steps 1–5).

If you'd rather run the `.app` itself: move it into `/Applications` first
(launching straight from Downloads triggers App Translocation), then in
Terminal:

```bash
xattr -cr "/Applications/VerseView Detector.app"
```

Right-click → **Open** the first time, rather than double-clicking, to accept
the "unidentified developer" prompt.

---

## If Test Connection doesn't say OK

| Symptom | Meaning | Fix |
|---|---|---|
| `HTTP 403 — did not authenticate` | The header values didn't match what Access expects. | Re-copy the JSON exactly — no missing quote, no trailing space, both keys present. |
| `Timed out after 20s` | Access let it through, but Ollama took a while to answer. | Usually a cold model load on the host. Try again — it should be quick the second time. |
| Mac: `.app` quits instantly / "damaged" | Gatekeeper quarantine on an ad-hoc-signed, unnotarized build. | Use the Raw Executable (above), or `xattr -cr` the `.app` after moving it to `/Applications`. |
