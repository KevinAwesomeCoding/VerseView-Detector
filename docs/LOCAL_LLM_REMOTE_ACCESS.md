# Using the home model host from another VerseView computer

One Windows PC runs Ollama and the models. Every other computer runs the normal
VerseView desktop app and points its **Local Ollama Endpoint** at that PC.

```
Remote VerseView desktop app  (Windows / Intel Mac)
        │  HTTPS + service-token headers
        ▼
Cloudflare Access            ← authenticates the request
        │
Cloudflare Tunnel            ← outbound-only connection from the model host
        ▼
Home Windows PC
        │  http://127.0.0.1:11434
        ▼
Ollama + installed models
```

Nothing is opened on the router and port `11434` stays bound to loopback on the
model host. `cloudflared` runs on that same machine and dials **out** to
Cloudflare, so there is no inbound port to forward and no LAN exposure.

---

## What the app already does

The app is protocol-ready for this today. Advanced Settings → **Local LLM
(Ollama)** has:

| Field | Purpose |
|---|---|
| **Local Ollama Endpoint** | One endpoint shared by every Local LLM role. `http://127.0.0.1:11434` on the model host; your HTTPS hostname on every other computer. |
| **Auth Token** (optional) | Sent as `Authorization: Bearer <token>`. Leave blank for a local endpoint. |
| **Extra Headers** (optional) | Any additional headers, as a JSON object. This is where Cloudflare Access service tokens go. |

Both credential fields are masked in the UI, are blank by default, and their
**values are never written to the log or shown in an error message** — only
header *names* are ever printed.

A plain `http://127.0.0.1:11434` endpoint works with both fields empty. No
authentication settings are required for the model host itself.

---

## Which Cloudflare Access mode a desktop app needs

**Service tokens.** This is the only correct option here, and it is worth being
precise about why.

Cloudflare Access normally authenticates a *person*: the browser is redirected to
your identity provider, the user logs in, and Cloudflare sets a session cookie.
VerseView is not a browser — it cannot complete an interactive login, cannot hold
that cookie, and must run unattended during a service. An unauthenticated request
from the app is answered with a `302` to the Cloudflare login page, which the app
now reports as *"the request is not authenticated for this endpoint"* rather than
as a model failure.

A **service token** is Cloudflare's machine-to-machine credential for exactly
this case. It is a Client ID / Client Secret pair sent as two request headers:

```
CF-Access-Client-Id:     <id>.access
CF-Access-Client-Secret: <secret>
```

Paste them into **Extra Headers** as a JSON object, exactly like this:

```json
{"CF-Access-Client-Id": "<id>.access", "CF-Access-Client-Secret": "<secret>"}
```

Leave **Auth Token** blank — Cloudflare Access does not use a bearer token. The
Auth Token field exists for a different front door (a reverse proxy or API
gateway that expects `Authorization: Bearer …`); it is there so you are not
locked into Cloudflare.

Two things to get right in the Cloudflare dashboard, because a service token
sent to a policy that does not accept it is rejected the same way as no token
at all:

1. Create the token under **Access → Service Auth → Service Tokens**. The secret
   is shown **once**; copy it then.
2. In the Access application's policy, add a policy whose **action is
   `Service Auth`** and whose rule includes that service token. A normal *Allow*
   policy built on emails or groups will not admit a service token.

Service tokens expire (1 year by default) and must be rotated. When one expires
the app will report a not-authenticated error, not a silent failure.

---

## Setting up the model host (one time)

Two separate things, and the order matters:

- the **Tunnel** is plumbing — it makes the home PC reachable;
- **Access** is the lock — it decides who may use it.

A tunnel on its own is a public Ollama server. Build both before you use the
hostname from anywhere.

### Prerequisite: a domain

Cloudflare Tunnel needs a real domain on a Cloudflare account before it can
publish a stable hostname. Quick tunnels — the throwaway `*.trycloudflare.com`
URLs — are documented as testing-only and **cannot be protected by Access**, so
they are not an option here.

**If you do not own a domain**, register one inside Cloudflare itself:
dash.cloudflare.com → **Domain Registration → Register Domains**. Cloudflare
Registrar sells at wholesale cost with no renewal markup, and a domain bought
there is put on Cloudflare nameservers automatically — which removes the
nameserver-change step and the wait that goes with it.

The name is infrastructure, not branding. Nobody sees it but you. A short
`.xyz`/`.net`/`.com` is fine; the dashboard shows the price before you pay.

**If you already own one elsewhere**, add it at dash.cloudflare.com →
**Add a site** (free plan), then change the nameservers at your registrar to the
two Cloudflare provides, and wait for the domain to read **Active**.

**If it must be free**, <https://domain.digitalplat.org/> issues `.dpdns.org`
names (GitHub sign-in; `dpdns.org` is on the Public Suffix List, so Cloudflare
treats it as a real zone on the free plan). Its whole model is delegation — you
paste Cloudflare's nameservers into its panel and everything below works
unchanged. The trade-off is that a free registry carries no contract: when
Freenom collapsed in 2024 it took ~12.6 million domains with it. Fine for
evaluating this; think twice before a Sunday service depends on it.

Either way you also need a Zero Trust account at
<https://one.dash.cloudflare.com> — free for up to 50 users.

### 1. Leave Ollama alone

It should keep listening on `127.0.0.1:11434`. Do **not** set
`OLLAMA_HOST=0.0.0.0` — `cloudflared` runs on the *same machine* and reaches
Ollama over loopback. Keeping it on loopback is what makes this safer than a LAN
setup. (Plenty of tutorials tell you to set `0.0.0.0`; those assume the connector
runs elsewhere. It does not here.)

If `ollama serve` reports *"Only one usage of each socket address … is normally
permitted"*, Ollama is already running correctly — the port is taken by Ollama
itself. Do not start a second server.

### 2. Create the tunnel

Zero Trust dashboard → **Networking → Tunnels → Create a tunnel** →
**Cloudflared**. Name it (e.g. `home-models`), then copy the **Windows** install
command it shows and run it in an Administrator PowerShell on the model host.
That command installs `cloudflared`, registers it as a Windows service so it
survives reboots, and connects it to your account. Wait for the connector to show
as **Healthy**.

This is the "remotely managed" tunnel: its configuration lives in the dashboard,
so there is no `config.yml` to maintain on the PC.

### 3. Publish the hostname

On the tunnel's **Routes** tab → **Add route → Published application**:

| Field | Value |
|---|---|
| Subdomain | `ollama` |
| Domain | your domain |
| Service type | `HTTP` |
| Service URL | `localhost:11434` |

Cloudflare creates the DNS record for you.

**At this moment `https://ollama.example.com` is a public, unauthenticated
Ollama.** Go straight to step 4.

#### If Ollama answers 403 through the tunnel

Ollama rejects requests whose `Host` header it does not recognise, as protection
against DNS rebinding. If you get a 403 that comes from Ollama rather than from
Cloudflare, open the route's **Additional application settings → HTTP Settings**
and set **HTTP Host Header** to `localhost:11434`. That makes the connector
present the header Ollama expects while it stays on loopback.

### 4. Put Access in front of it

Zero Trust → **Access controls → Applications → Create new application** →
**Self-hosted and private** → **Add public hostname**. Select the same
subdomain + domain you just published.

Access applications are **deny by default**: nothing gets through until a policy
matches. Never use a **Bypass** policy here — it switches the lock off.

### 5. Create a service token

Zero Trust → **Access controls → Service credentials → Service Tokens** →
**Create Service Token**. Name it (e.g. `verseview-desktop`) and choose a
duration — one year (`8760h`) is the usual choice.

The **Client Secret is shown once**. Copy both values now.

### 6. Add a Service Auth policy

Back in the Access application, add a policy with:

- **Action: `Service Auth`** — this is the part people miss. With any other
  action Access ignores the token and prompts for an identity-provider login,
  which a desktop app cannot complete.
- **Include → Service Token →** the token you just created.

If you also want to open the endpoint in a browser yourself, add a *second*
policy with action **Allow** and an Include rule for your own email. The two
coexist: humans log in, VerseView presents its token.

---

## Configuring a remote VerseView computer

In Advanced Settings → Local LLM (Ollama):

1. **Local Ollama Endpoint** → `https://ollama.example.com`
   No port. `https://` implies 443, which is what the tunnel listens on; the app
   deliberately does **not** append `11434` to an HTTPS endpoint.
2. **Extra Headers** → the service-token JSON above.
3. **Auth Token** → leave blank.
4. Model names must match what is installed **on the model host** — the remote
   computer holds no models of its own.
5. Click **Test Connection**. On success it reports the endpoint, the model, the
   header names it sent, and the round-trip time.

Everything else — per-role routing, suggested models, custom overrides, the
"If Local LLM fails" policy — behaves identically to the model host.

---

## Prove the lock actually works

Do this before a service, not during one. From any machine:

```bash
curl -si https://ollama.example.com/api/tags | head -1
```

Expect `HTTP/2 302` (bounced to the Access login page) or a `403`. If you get
`HTTP/2 200` and a list of your models, **Access is not protecting the hostname**
— recheck steps 4 and 6.

Then confirm the credential works:

```bash
curl -s https://ollama.example.com/api/tags -H "CF-Access-Client-Id: <id>.access" -H "CF-Access-Client-Secret: <secret>"
```

That should return your model list. Same two headers VerseView sends.

---

## Keeping it working

- **The service token expires.** When it does, VerseView reports a
  not-authenticated error rather than failing silently. Create a new token,
  add it to the Service Auth policy, and update Extra Headers on each remote
  computer.
- **Treat the Client Secret like a password.** Anyone holding it can use your
  models. It is stored in each remote machine's settings file, the same way API
  keys already are.
- **The model host must be awake.** Sleep or hibernate takes the tunnel down;
  remote clients then fall back to cloud (or skip, per your failure policy).

---

## Security note

This design is only as safe as the policy in front of the endpoint. Until
Cloudflare Access is configured **and** a `Service Auth` policy is enforcing the
service token, an HTTPS hostname pointed at your tunnel is an open Ollama server
that happens to have a TLS certificate. The app's bearer-token and header support
lets it authenticate to whatever you put there; it cannot, on its own, make the
endpoint private.
