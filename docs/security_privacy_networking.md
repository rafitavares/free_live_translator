# Security, privacy, HTTPS, and local networking

Church Cap is designed to be local-first: audio is captured on the church computer, captions are served on the local network, and guests only need a browser.

## Operator login

The public caption pages are open so visitors can scan a QR code and read captions. The operator controls are protected by a password.

On first startup, Church Cap opens `/setup` so the operator can create a local password. The password is stored as a salted hash in the per-user data folder, not in the project folder. `OPERATOR_PASSWORD` and `SESSION_SECRET` in `.env` are optional legacy/development overrides; for normal church use, prefer the first-run setup page.

v0.7.4 gives setup, login, Service Leader pairing, operator forms, and state-changing operator API calls a same-origin request token. This prevents another website open in the browser from silently submitting control changes to a locally running Church Cap instance. Operator session cookies are `HttpOnly` and `SameSite=Strict`; HTTPS deployments also receive the `Secure` cookie flag.

Authentication forms accept either the matching short-lived token or browser-verified same-origin evidence. This keeps a login form left open during an upgrade usable and accounts for the appliance proxy presenting a different internal address. Forwarded browser addresses and `Sec-Fetch-Site` are handled explicitly; an explicit cross-site request remains blocked. A failed page-security check happens before password verification and does not mean the password has changed or needs resetting.

Password failures are throttled in memory by source and login flow. The first five attempts are immediate; continued failures pause that login flow for 2, 4, 8, 16, then at most 30 seconds. A successful login clears the entry, old entries expire, and restarting Church Cap clears all pauses. When a pause applies, the page explains why it happened, how long to wait, and that captions and connected viewers are not affected. This is deliberately bounded so an accidental lockout cannot disable a live service for a long period.

On macOS and Linux, Church Cap applies owner-only `0600` permissions to the primary and backup operator-authentication files whenever they are loaded or saved. Windows keeps the files in the signed-in user's application-data folder and uses the account's inherited Windows permissions. Filesystems that cannot retain the requested POSIX mode do not stop Church Cap from starting; the authenticated Operator security panel shows a permission warning instead.

Protected pages/routes include:

```text
/operator
/transcript.txt
/transcript.vtt
/transcript.srt
/transcript.json
/api/start
/api/stop
/api/clear
/api/audio-devices
/api/audio-device
/api/privacy
/api/profanity-filter
/api/translation
/api/sensitive-on
/api/sensitive-off
```

The restricted `/service-leader` role uses a separate session and dedicated `/service-leader/api/*` routes. It is not accepted by operator dependencies and cannot be used on the protected routes above.

Audience caption pages remain open:

```text
/
/display
/obs
/qr.png
/qr-ip.png
/api/languages
/api/client-ui/{language}
/ws/captions
/ws/translation-audio
```

The public `/health` response is deliberately limited to readiness, caption-service status, and the Church Cap version needed by the updater. `/api/languages` exposes only the language availability and request information required by audience devices. Model paths, audio-device information, internal URLs, translation scheduler details, and operator security configuration remain available only through authenticated Operator status and diagnostics.

`/ws/translation-audio` is an opt-in audience stream for a selected translated language. It is separate from the caption socket, accepts only installed manifest-approved languages, and does not grant Operator access. Audio is generated only while listeners are subscribed, held in memory for delivery, and not written to the transcript cache, logs, diagnostics, or service report. The browser stops queued playback when the listener selects **Stop audio**, changes language, leaves the page, or falls too far behind. Sensitive mode clears server queues and prevents in-flight speech from being delivered.

All HTTP pages receive `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and a conservative browser `Permissions-Policy`. The policy disables unused camera, location, payment, and USB features but deliberately does not deny microphone access, preserving compatibility with current and future local audio/diagnostic launch paths. Authentication pages continue to block framing and caching. A full Content Security Policy is not enforced yet because Church Cap's current inline operator scripts, Room Display, and OBS paths need a dedicated compatibility migration first.

## Sensitive moment mode

Use **Blank / pause captions** before private prayer, pastoral details, safeguarding disclosures, testimony, or anything that should not be displayed or retained.

When enabled:

- new captions are not shown to viewers
- new captions are not saved to transcript history
- audience screens show a private-moment message

Use **Resume captions** when the public service continues.

## Transcript retention

The operator page lets you choose whether transcript history is saved and how long to keep it. Current options include:

- do not retain history
- 30 minutes
- 2 hours
- 1 day
- 7 days

For privacy, avoid storing audio by default. Church Cap does not store audio. When transcript saving is enabled, caption text is retained for the configured window in a small local transcript cache under the per-user data folder. The cache is encrypted at rest when the `cryptography` dependency is installed and records the retention window that applied when it was saved. A fresh app start begins with an empty visible session transcript, then prunes the saved cache on startup using the saved retention window. Current-session transcript export shows a privacy warning because exported files may contain names, pastoral details, prayer requests, testimony, or other sensitive information. Full transcript export remains operator-controlled, while the restricted Service Leader page can export TXT/VTT for appliance support after a separate warning. Sensitive moment mode suppresses transcript retention and export for that period, flushes the live transcription buffer, and includes a short buffered-audio drain window after captions resume. Clearing the transcript or setting retention to **Do not retain history** deletes the retained transcript cache.

On macOS, runtime settings and operator auth are stored under:

```text
~/Library/Application Support/Church Cap/data/
```

On Windows, they are stored under:

```text
%APPDATA%\Church Cap\data\
```

On Linux, they are stored under:

```text
${XDG_DATA_HOME:-~/.local/share}/church-cap/data/
```

Older project-local files from `data/` are migrated there when needed. Transcript retention is enforced when captions are written, when settings change, and when the app starts; if every retained caption is older than the retention window saved with that cache, the transcript cache is deleted. The operator page includes **Open transcript folder**, which opens this per-user data folder in Finder on macOS, File Explorer on Windows, or the configured desktop file manager on Linux when used from the Church Cap computer.

## HTTPS / local certificate

For local testing, plain HTTP is easiest:

```text
http://192.168.1.50:8080
```

For HTTPS, you need a certificate trusted by the devices using it. There are two practical routes.

### Option A: mkcert for testing

`mkcert` creates local development certificates. It is useful for testing on your own devices, but you still need to install/trust its local CA on each device that will access captions.

```bash
brew install mkcert nss
mkcert -install
mkdir -p certs
mkcert -cert-file certs/church-cap.local.crt -key-file certs/church-cap.local.key church-cap.local localhost 127.0.0.1
./scripts/run-dev-https.sh
```

Then open:

```text
https://church-cap.local:8443
```

### Option B: self-signed certificate

You can generate a self-signed certificate:

```bash
./scripts/generate-local-cert.sh
./scripts/run-dev-https.sh
```

Browsers will warn unless the certificate is trusted on that device. This is acceptable for development, but not ideal for visitors.

## Service leader pairing

The operator login page and the authenticated **Service Leader** operator section can create a one-use QR for a trusted service leader. Pairing generation is restricted to the Church Cap computer. The login flow keeps the operator password on that computer; the signed-in flow does not ask for it again. The QR secret expires after 90 seconds, works once, and is exchanged for a restricted session lasting no more than four hours with a two-hour idle timeout.

Generating a replacement invalidates the previous unused QR but does not revoke established sessions. The operator can separately cancel an unused QR or disconnect all paired devices.

The restricted session can control caption start/stop, sensitive blank/resume, audio input while stopped, caption-health viewing, translated-caption availability in Automatic or Manual mode, and incoming audience language-request acceptance or rejection. It can also view active translation-slot use and per-language viewer demand, share the audience QR through a temporary phone-download QR, and perform warned exports for the current-session transcript and redacted support logs. Language-request mutations require the restricted session's own same-origin token and reuse the same bounded translation configuration actions as the Operator page. It cannot alter performance settings, install translation models, change account/privacy settings, run updates, or use full operator APIs. Its caption preview observes the public caption stream without being counted as an audience viewer. See `docs/service_leader_controls.md`.

When secure operator mode is enabled, the operator listener must be reachable on the LAN for `/service-leader`, but middleware blocks remote access to every other operator path. Restrict the operator port to a trusted staff/AV subnet at the host firewall or router where practical.

## Local hostname: `church-cap.local`

There are several ways to make `church-cap.local` work.

Linux does not assume that its computer name is published through mDNS. Without an explicit `CAPTION_LOCAL_HOSTNAME` or `PUBLIC_BASE_URL`, Church Cap keeps the hostname QR visible but marks it as requiring setup and recommends the direct-IP QR. Configure Avahi/mDNS or router DNS before advertising a Linux `.local` hostname.

### Easiest for Mac/iPhone networks: mDNS / Bonjour

Many Apple devices can resolve `.local` hostnames via Bonjour. Set the Mac mini computer name to something like `caption`, then try:

```text
http://church-cap.local:8080
```

### Router/DNS reservation

On the church router:

1. Reserve a fixed IP for the caption computer.
2. Add a local DNS record such as `church-cap.local` or `captions.church.lan` pointing to that IP.
3. Set `PUBLIC_BASE_URL` in `.env`, for example:

```env
PUBLIC_BASE_URL=http://church-cap.local:8080
```

If using HTTPS:

```env
PUBLIC_BASE_URL=https://church-cap.local:8443
```

## Network isolation / guest Wi-Fi rules

A good church setup is:

```text
Caption Mac mini: wired Ethernet on trusted AV/admin network
Audience phones: church guest Wi-Fi
Firewall rule: guest Wi-Fi may access caption server port 8080/8443 only
Firewall rule: guest Wi-Fi cannot access other internal devices
Operator/admin device: trusted network, or same device running the app
```

Minimum rule:

```text
Allow guest Wi-Fi → caption server IP → TCP 8080 or 8443
Block guest Wi-Fi → other LAN devices
```

On Linux, `setup-linux.sh` detects active `firewalld` or UFW and offers to add the viewer-port rule after explicit confirmation. It opens only the configured viewer TCP port, normally 8080, and does not open operator port 9090. Router and wireless-client isolation remain separate controls.

Do not expose the caption server directly to the public internet unless you have reviewed authentication, HTTPS, logging, transcript retention, and cloud/security implications.

## Suggested local deployment defaults

```env
PUBLIC_BASE_URL=http://church-cap.local:8080
TRANSCRIPT_SAVING_ENABLED=true
TRANSCRIPT_RETENTION_MINUTES=120
TRANSLATION_ENABLED=false
```

During sensitive moments, press **Blank / pause captions**.
