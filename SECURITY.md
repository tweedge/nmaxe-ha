# Security Policy

Please report vulnerabilities privately through GitHub Security Advisories:

https://github.com/tweedge/nmaxe-hacs/security/advisories/new

Do not include pool passwords, payout keys you want kept private, or full miner API responses in public issues. Diagnostics from the integration redact password-like fields, but review anything you attach before posting it.

## Scope

This integration only reads local AxeOS endpoints over plain HTTP. It does not expose a remote service, store credentials, or write miner settings. The miner's own unauthenticated API and network exposure remain the responsibility of the device owner.
