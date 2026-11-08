from domain_onboarding import DnsRecord, onboard_sending_domain


class FakeClient:
    def __init__(self):
        self.calls = []

    def add_domain(self, domain):
        self.calls.append(("add", domain))
        return {"ok": True}

    def get_domain(self, domain):
        self.calls.append(("get", domain))
        return {"ok": True, "data": {"zone_id": "zone-123"}}

    def upsert_record(self, zone_id, record):
        self.calls.append(("upsert", zone_id, record.record_type))
        return {"ok": True}

    def verify_email_domain(self, domain):
        self.calls.append(("verify", domain))
        return {"ok": True, "data": {"verification": {"status": "verified"}}}


def test_onboarding_uses_zone_id_before_writing_records():
    client = FakeClient()
    status = onboard_sending_domain(client, "acme.test", [DnsRecord("TXT", "acme.test", "v=spf1 ~all")])
    assert status == "verified"
    assert client.calls == [("add", "acme.test"), ("get", "acme.test"), ("upsert", "zone-123", "TXT"), ("verify", "acme.test")]
