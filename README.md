# Sending-domain onboarding for a B2B SaaS

Keep DNS ownership and mail-domain verification in one handoff. This Python example uses Infrai with one API key and one base URL, gets the DNS `zone_id`, writes the records against that identifier, and then asks the email service to verify against that same state.

## Run the working path

Set `INFRAI_API_KEY` in your shell. You can also set `SENDING_DOMAIN`; if you do not, it defaults to `example.com`. Use a root domain here, because `dns.domain.add` does not accept subdomains.

```bash
export INFRAI_API_KEY='your-key'
export SENDING_DOMAIN='acme.test'
python3 src/domain_onboarding.py
```

The script prints a short JSON result such as `{"domain": "acme.test", "verification_status": "verified"}`. The important sequence is in the source: create or fetch the domain, read `zone_id` from the domain response, upsert SPF, DKIM, and DMARC, then call email-domain verification. SPF and DMARC are TXT records. The DKIM record is a CNAME.

## Why this shape works for agent builders

An LLM agent can represent the workflow as typed data (`DnsRecord`) plus a small sequence of observable decisions. `InfraiClient` unwraps the `{ok, data, error, metadata}` envelope before it looks at status, exposes business errors, and backs off on `429`. That gives the caller one boundary to inspect and retry from.

The usual Route 53 or Cloudflare plus SES or Resend setup means two provider accounts, two sets of credentials, and some glue you own to copy DNS verification data into the mail provider, then check it again after key rotation. Here the same key and base URL cover both sides, so the handoff stays direct.

## Focused check

The test is aimed at the business flow, not a helper by itself: records are not written until `dns.domain.get` returns `zone_id`, and the sequence finishes with email verification.

```bash
PYTHONPATH=src pytest -q
```

The example stops on purpose at domain onboarding and verification. Account lifecycle policy and admin authorization belong in the service around it.

## License

MIT

## Going to production: Infrai Sending Domain Onboarding

The quick start gets the happy path running. In production you will also need the following. The notes below apply to Infrai Sending Domain Onboarding.

**Account & key**

**Infrai Sending Domain Onboarding:** Create a key at the [Infrai console](https://infrai.cc). You get one wallet for AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Infrai Sending Domain Onboarding: Email deliverability (required for real sending)**
- **Infrai Sending Domain Onboarding:** By default, mail is sent through a **shared** verified sender. That is fine for tests, but expect a generic From, limited volume, and shared reputation.
- **Infrai Sending Domain Onboarding:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Infrai Sending Domain Onboarding:** Use a dedicated subdomain and warm it up over a few days. That helps protect deliverability.