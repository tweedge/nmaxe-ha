# nmaxe-ha

[![Validate](https://github.com/tweedge/nmaxe-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/tweedge/nmaxe-ha/actions/workflows/validate.yml)
[![Tests](https://github.com/tweedge/nmaxe-ha/actions/workflows/tests.yml/badge.svg)](https://github.com/tweedge/nmaxe-ha/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/tweedge/nmaxe-ha)](https://github.com/tweedge/nmaxe-ha)
[![Written By](https://img.shields.io/badge/written%20by-some%20nerd-red.svg)](https://chris.partridge.tech)
[![Follow author on Bluesky](https://img.shields.io/bluesky/followers/tweedge.net)](https://bsky.app/profile/tweedge.net)
[![Follow author on Mastodon](https://img.shields.io/mastodon/follow/108210086817505115?domain=https%3A%2F%2Fcybersecurity.theater)](https://cybersecurity.theater/@tweedge)

A read-only Home Assistant integration for NMAxe-family miners running [AxeOS firmware](https://github.com/NMminer1024/ESP-Miner-NMAxe). It polls the miner's local API and exposes hashrate, power, temperatures, blocks, shares, pool status, payout username, fans, Wi-Fi, and system health.

The integration never changes miner settings. It only performs HTTP GETs against the local device.

## Installation

### HACS

1. Install [HACS](https://hacs.xyz/) if you have not already.
2. Open **HACS → Integrations**.
3. Open the three-dot menu → **Custom repositories**.
4. Add `https://github.com/tweedge/nmaxe-ha` with category **Integration**.
5. Search for **NMAxe**, install it, and restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration → NMAxe**.
7. Enter the miner's IP address or hostname, for example `192.168.1.42` or `nmaxe.local`.

### Manual

```bash
git clone https://github.com/tweedge/nmaxe-ha.git /tmp/nmaxe-ha
mkdir -p /config/custom_components
cp -r /tmp/nmaxe-ha/custom_components/nmaxe /config/custom_components/
```

Restart Home Assistant, then add the integration as described above.

A static IP or hostname for the miner is strongly recommended. If its address changes, use **Reconfigure** on the integration entry rather than removing and re-adding it.

## Features

- Hashrate, efficiency (J/TH), power, input voltage/current
- ASIC and VCORE temperatures, frequency, requested/actual core voltage
- Blocks found, shares accepted/rejected/submitted, acceptance rate, and compact best/network/pool/last difficulty
- Active pool, pool username (your public payout key/worker), primary/fallback pools, active pool source
- Pool-connected and benchmark-mode binary sensors
- Fan speed/RPM, Wi-Fi RSSI/SSID, free heap, uptime, firmware version
- Diagnostics download with secret-like fields redacted
- Configurable polling intervals, with pool settings read much less often than status
- Only core entities enabled by default; every other sensor is available but disabled

Difficulty sensors use compact SI suffixes such as `88.55 T`; the numeric value remains available as the `raw_value` attribute.

### Enabled by default

The default dashboard stays focused on high-level device health and mining speed:

- Blocks found
- Efficiency
- Hashrate
- Miner state
- Pool connected
- Power
- Share acceptance rate

All other sensors are still created and available, but disabled by default. Enable the ones you need from the device's entity list.

Technical telemetry such as input voltage/current, ASIC frequency, temperatures, core voltages, fan speeds, and uptime are categorized as **Diagnostic**.

## Options

- **Status update interval**: seconds between `/api/system/info` reads. Default `60`, minimum `15`, maximum `3600`.
- **Pool settings refresh interval**: seconds between `/api/setting/mining` reads. Default `600`. Set to `0` to disable that request; primary/fallback pool and pool-source sensors then show `unknown`.

The default intervals are intentionally conservative for the ESP32 since it's not a particularly fast device. There is no websocket or streaming connection.

AxeOS does not expose the raw stratum socket state, so **Pool connected** means the miner reports `running` and has an active pool URL.

## Security

This integration is designed not to introduce substantial *new* security risks into your environment. AxeOS itself does not (as of writing) require any password to modify settings or implement authentication, meaning it would be trivial for an attacker on your local network to change your settings (ex. mine on their behalf) or brick your device (ex. upload junk firmware). In addition, it does not support HTTPS, just HTTP. I really wouldn't recommend exposing AxeOS to the internet, and I've got it on a locked-down, separate subnet (which my HomeAssistant instance can see) for safety.

That said, to interface with the NMAxe miner, this code performs the following:

- Only unauthenticated HTTP `GET` requests are made. There are no write, reboot, pause, or configuration endpoints implemented in this repo.
- `/api/system/info` contains the pool password. The parser keeps only the pool URL and username; the password is discarded before data reaches the coordinator, entities, diagnostics, or logs.
- `/api/setting/mining` also contains pool passwords. It is read at most once per pool refresh interval, and only URL/username fields are retained.
- Diagnostics recursively redact passwords, tokens, API keys, pool usernames/payout addresses, and Wi-Fi SSIDs.
- Responses are capped at 64 KiB, redirects are not followed, requests time out after 10 seconds, and only plain `http://` hosts without paths or credentials are accepted.
- No cloud service, telemetry, or external dependency is used.

## Troubleshooting

- **Cannot connect**: confirm the IP/hostname, that the AxeOS web UI loads, and that Home Assistant can reach port 80 on the miner.
- **Invalid device**: the device did not return the expected nested AxeOS response. This integration targets firmware with the v3 `/api/system/info` shape (tested against v3.2.01).
- **Unsupported device**: only NMAxe and NMQAxe-family models are accepted.
- **Pool sensors show unknown**: pool settings polling is disabled, or the firmware did not return the settings endpoint. Set a non-zero pool refresh interval.
- **Address changed**: use **Reconfigure** and enter the new IP/hostname.

## Development

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
pytest
pip install -r requirements_lint.txt
ruff check .
ruff format --check .
```

To regenerate the icons and logo:

```bash
pip install -r requirements_assets.txt
python scripts/generate_assets.py
```

The generator writes light and dark logo variants plus the icon and 2x assets. Edit the constants at the top of `scripts/generate_assets.py` to adjust sizes, padding, text, and colors.

CI runs hassfest, HACS validation, Ruff, pytest, CodeQL, dependency review, and zizmor on every push and pull request.

## License

MIT. THis project is not affiliated with NMTech, NMminer, or the NMAxe project. The pickaxe glyph used in assets is from Material Design Icons (Apache-2.0).
