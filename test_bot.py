"""
Comprehensive Test Suite for Vera AI Bot Server.
Tests context push, tick, reply, warmup, auto-reply detection, intent transition, and hostile handling.
"""

import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8080"


def post_json(path, data):
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(path):
    with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_suite():
    print("--- Running Vera AI Bot Test Suite ---")
    
    # 1. Healthz & Metadata
    health = get_json("/v1/healthz")
    print(f"Healthz: {health}")
    assert health["status"] == "ok"

    meta = get_json("/v1/metadata")
    print(f"Metadata Team: {meta.get('team_name')}")
    assert "team_name" in meta

    # 2. Context Push (Idempotency and Versioning)
    cat_payload = {
        "slug": "dentists",
        "offer_catalog": [{"title": "Dental Cleaning @ ₹299"}],
        "voice": {"tone": "peer_clinical", "taboos": ["cure", "guaranteed"]}
    }
    push_v5 = post_json("/v1/context", {
        "scope": "category",
        "context_id": "dentists",
        "version": 5,
        "payload": cat_payload
    })
    print(f"Push v5: {push_v5}")
    assert push_v5["accepted"] is True

    # Re-posting same version is idempotent
    push_v5_repeat = post_json("/v1/context", {
        "scope": "category",
        "context_id": "dentists",
        "version": 5,
        "payload": cat_payload
    })
    print(f"Push v5 repeat (idempotent): {push_v5_repeat}")
    assert push_v5_repeat["accepted"] is True

    # Posting lower version (version 1 when stored is 5) is rejected as stale
    push_v1_stale = post_json("/v1/context", {
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": cat_payload
    })
    print(f"Push v1 stale (lower version): {push_v1_stale}")
    assert push_v1_stale["accepted"] is False
    assert push_v1_stale["reason"] == "stale_version"

    # Push merchant
    merchant_payload = {
        "merchant_id": "m_001_drmeera",
        "category_slug": "dentists",
        "identity": {"name": "Dr. Meera's Dental Clinic", "city": "Delhi", "locality": "Lajpat Nagar", "owner_first_name": "Meera"},
        "subscription": {"status": "active", "plan": "Pro"},
        "performance": {"views": 2410, "calls": 18, "ctr": 0.021},
        "offers": [{"id": "o1", "title": "Dental Cleaning @ ₹299", "status": "active"}]
    }
    post_json("/v1/context", {
        "scope": "merchant",
        "context_id": "m_001_drmeera",
        "version": 1,
        "payload": merchant_payload
    })

    # Push trigger
    trg_payload = {
        "id": "trg_digest_01",
        "scope": "merchant",
        "kind": "research_digest",
        "merchant_id": "m_001_drmeera",
        "payload": {"top_item": {"title": "3-mo fluoride recall cuts caries 38% better", "source": "JIDA Oct 2026, p.14", "trial_n": 2100}}
    }
    post_json("/v1/context", {
        "scope": "trigger",
        "context_id": "trg_digest_01",
        "version": 1,
        "payload": trg_payload
    })

    # 3. Tick Test
    tick_res = post_json("/v1/tick", {
        "now": "2026-04-26T10:00:00Z",
        "available_triggers": ["trg_digest_01"]
    })
    print(f"Tick actions returned: {len(tick_res.get('actions', []))}")
    assert len(tick_res["actions"]) == 1
    action = tick_res["actions"][0]
    print(f"Action Body: {action['body']}")
    print(f"Action CTA: {action['cta']}")
    print(f"Action Send As: {action['send_as']}")

    ts = int(time.time() * 1000)

    # 4. Auto-Reply Detection Test
    auto_reply_msg = "Thank you for contacting us! Our team will respond shortly."
    reply1 = post_json("/v1/reply", {
        "conversation_id": f"conv_auto_test_{ts}",
        "merchant_id": "m_001_drmeera",
        "from_role": "merchant",
        "message": auto_reply_msg,
        "turn_number": 1
    })
    print(f"Auto-Reply Turn 1 action: {reply1['action']}")
    
    reply2 = post_json("/v1/reply", {
        "conversation_id": f"conv_auto_test_{ts}",
        "merchant_id": "m_001_drmeera",
        "from_role": "merchant",
        "message": auto_reply_msg,
        "turn_number": 2
    })
    print(f"Auto-Reply Turn 2 action: {reply2['action']}")
    assert reply2["action"] == "end"

    # 5. Intent Transition Test
    intent_reply = post_json("/v1/reply", {
        "conversation_id": f"conv_intent_test_{ts}",
        "merchant_id": "m_001_drmeera",
        "from_role": "merchant",
        "message": "Ok lets do it. Whats next?",
        "turn_number": 2
    })
    print(f"Intent Transition Action: {intent_reply['action']}")
    print(f"Intent Body: {intent_reply['body']}")
    assert intent_reply["action"] == "send"
    assert "done" in intent_reply["body"].lower() or "proceed" in intent_reply["body"].lower() or "here is" in intent_reply["body"].lower()

    # 6. Hostile Handling Test
    hostile_reply = post_json("/v1/reply", {
        "conversation_id": f"conv_hostile_test_{ts}",
        "merchant_id": "m_001_drmeera",
        "from_role": "merchant",
        "message": "Stop messaging me. This is useless spam.",
        "turn_number": 2
    })
    print(f"Hostile Action: {hostile_reply['action']}")
    assert hostile_reply["action"] == "end"

    print("\n[PASS] All 6 test suite scenarios passed successfully!")


if __name__ == "__main__":
    test_suite()
