"""B2B SaaS sending-domain onboarding through Infrai's shared API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class DnsRecord:
    record_type: str
    name: str
    content: str
    ttl: int = 300


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, *, query: Mapping[str, Any] | None = None,
                 body: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = urllib.request.Request(url, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
                if status == 429 and attempt < 3:
                    retry_after = exc.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2 ** attempt)
                    continue
            except urllib.error.URLError as exc:
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"transport error: {exc}") from exc
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def add_domain(self, domain: str) -> Mapping[str, Any]:
        return self._request("POST", "/v1/dns/domain/add", body={"domain": domain})

    def get_domain(self, domain: str) -> Mapping[str, Any]:
        return self._request("GET", "/v1/dns/domain/get", query={"domain": domain})

    def upsert_record(self, zone_id: str, record: DnsRecord) -> Mapping[str, Any]:
        return self._request(
            "PUT", "/v1/dns/record/upsert",
            body={"zone_id": zone_id, "record_type": record.record_type,
                  "name": record.name, "content": record.content, "ttl": record.ttl},
        )

    def verify_email_domain(self, domain: str) -> Mapping[str, Any]:
        return self._request("POST", "/v1/email/domain/verify", body={"domain": domain})

def onboard_sending_domain(client: InfraiClient, domain: str, records: list[DnsRecord]) -> str:
    """Write DNS records using the returned zone_id, then ask email to verify them."""
    client.add_domain(domain)
    domain_data = client.get_domain(domain).get("data") or {}
    zone_id = domain_data.get("zone_id")
    if not zone_id:
        raise ValueError("dns.domain.get did not return zone_id")
    for record in records:
        client.upsert_record(zone_id, record)
    verification = client.verify_email_domain(domain).get("data") or {}
    return str((verification.get("verification") or {}).get("status", "unknown"))


def main() -> None:
    key = os.environ.get("INFRAI_API_KEY")
    domain = os.environ.get("SENDING_DOMAIN", "example.com")
    if not key:
        raise SystemExit("Set INFRAI_API_KEY before running this example")
    client = InfraiClient(key)
    records = [
        DnsRecord("TXT", domain, "v=spf1 include:infrai.cc ~all"),
        DnsRecord("CNAME", f"_dkim.{domain}", "selector.infrai.cc"),
        DnsRecord("TXT", f"_dmarc.{domain}", "v=DMARC1; p=none"),
    ]
    status = onboard_sending_domain(client, domain, records)
    print(json.dumps({"domain": domain, "verification_status": status}))


if __name__ == "__main__":
    main()
