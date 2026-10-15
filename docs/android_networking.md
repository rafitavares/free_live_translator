# Android, `.local`, Bonjour/mDNS, and guest Wi‑Fi

The app prefers a friendly local hostname such as:

```text
http://church-cap.local:8080/
```

This is provided by Bonjour/mDNS on macOS. It works well on many Apple devices, but some Android phones and some guest Wi‑Fi networks do not reliably resolve `.local` names in a browser.

## Why an Android phone may not open the QR code

Common causes:

- The phone/router does not resolve `.local` hostnames consistently.
- Android Private DNS is bypassing local DNS behaviour.
- Guest Wi‑Fi has client isolation enabled.
- The router blocks multicast/mDNS between wired and wireless networks.
- The caption Mac is on the staff LAN while phones are on a separated guest LAN.

## Built-in fallback

The operator page shows two QR codes:

1. **Hostname QR** — preferred when configured; otherwise retained and labelled as requiring DNS/mDNS setup.
2. **Android / guest Wi‑Fi fallback QR** — the direct LAN IP address and port.

Use the IP fallback if Android cannot open the `.local` address.

On Linux without configured local DNS/mDNS, Church Cap keeps the hostname QR available for later setup, labels it accordingly, and marks the direct-IP QR as the recommended connection. If the IP cannot be opened either, check the Linux host firewall and router guest/client isolation.

## Best production options

For a reliable church installation, the most practical options are:

- Set a DHCP reservation for the caption Mac, e.g. `192.168.1.50`.
- Configure the router/firewall so guest Wi‑Fi can reach only `192.168.1.50:8080` or `:8443`.
- If the router supports it, create a local DNS record such as `captions.church.lan -> 192.168.1.50`.
- Keep the IP fallback QR available for Android users.

For a more polished install, router-managed DNS is often more reliable than relying on `.local` alone.
