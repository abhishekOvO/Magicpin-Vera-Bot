"""
Vera AI Assistant API Server.

Implements all 5 required endpoints according to the Magicpin Testing Brief:
- GET  /v1/healthz
- GET  /v1/metadata
- POST /v1/context
- POST /v1/tick
- POST /v1/reply
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from core.context_store import ContextStore
from core.composer import CompositionEngine
from core.reply_handler import ReplyHandler

app = FastAPI(title="Magicpin Vera AI Assistant API", version="1.0.0")

START_TIME = time.time()
store = ContextStore()
engine = CompositionEngine()
reply_handler = ReplyHandler()


# --- Pydantic Schemas ---

class ContextPushModel(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: Optional[str] = None


class TickRequestModel(BaseModel):
    now: str
    available_triggers: List[str] = Field(default_factory=list)


class ReplyRequestModel(BaseModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str = "merchant"
    message: str
    received_at: Optional[str] = None
    turn_number: int = 1


# --- API Endpoints ---

@app.get("/")
async def root():
    return {
        "message": "Welcome to Magicpin Vera AI Assistant API",
        "healthz": "/v1/healthz",
        "metadata": "/v1/metadata",
        "docs": "/docs"
    }


@app.get("/v1/healthz")
async def healthz():
    """Liveness probe returning server status and context counts."""
    uptime = int(time.time() - START_TIME)
    counts = store.get_counts()
    return {
        "status": "ok",
        "uptime_seconds": uptime,
        "contexts_loaded": counts
    }


@app.get("/v1/metadata")
async def metadata():
    """Bot identity and model metadata endpoint."""
    return {
        "team_name": "Team Magicpin Vera Architect",
        "team_members": ["AI System Architect"],
        "model": "Hybrid Deterministic + Policy Composition Engine",
        "approach": "Deterministic 4-context composition with category voice policies, auto-reply detection state machine, and intent-transition routing",
        "contact_email": "vera-team@magicpin.in",
        "version": "1.0.0",
        "submitted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }


@app.post("/v1/context")
async def push_context(data: ContextPushModel):
    """Idempotent context push endpoint."""
    if data.scope not in ["category", "merchant", "customer", "trigger"]:
        raise HTTPException(status_code=400, detail={"accepted": False, "reason": "invalid_scope"})

    res = store.push_context(data.scope, data.context_id, data.version, data.payload)
    if not res["accepted"]:
        return {
            "accepted": False,
            "reason": res.get("reason", "stale_version"),
            "current_version": res.get("current_version", data.version)
        }
    return res


@app.post("/v1/tick")
async def tick(data: TickRequestModel):
    """Periodic tick endpoint. Processes active triggers and returns outbound actions."""
    actions = []
    
    # Process available triggers (up to 20 actions per tick)
    for trg_id in data.available_triggers:
        if len(actions) >= 20:
            break

        trg = store.get_context("trigger", trg_id)
        if not trg:
            continue

        merchant_id = trg.get("merchant_id")
        if not merchant_id:
            continue

        merchant = store.get_context("merchant", merchant_id)
        if not merchant:
            continue

        cat_slug = merchant.get("category_slug") or trg.get("payload", {}).get("category")
        category = store.get_context("category", cat_slug) or {}

        customer_id = trg.get("customer_id")
        customer = store.get_context("customer", customer_id) if customer_id else None

        # Compose message
        composed = engine.compose(category, merchant, trg, customer)
        
        conv_id = f"conv_{merchant_id}_{trg_id}"
        owner_name = merchant.get("identity", {}).get("owner_first_name") or merchant.get("identity", {}).get("name", "")

        actions.append({
            "conversation_id": conv_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": composed["send_as"],
            "trigger_id": trg_id,
            "template_name": "vera_outbound_v1",
            "template_params": [owner_name, composed["body"][:30]],
            "body": composed["body"],
            "cta": composed["cta"],
            "suppression_key": composed["suppression_key"],
            "rationale": composed["rationale"]
        })

    return {"actions": actions}


@app.post("/v1/reply")
async def reply(data: ReplyRequestModel):
    """Sync reply endpoint. Analyzes merchant/customer message and returns next turn action."""
    merchant_ctx = store.get_context("merchant", data.merchant_id) if data.merchant_id else None
    cat_slug = merchant_ctx.get("category_slug") if merchant_ctx else None
    category_ctx = store.get_context("category", cat_slug) if cat_slug else None

    result = reply_handler.handle_reply(
        conversation_id=data.conversation_id,
        merchant_id=data.merchant_id,
        customer_id=data.customer_id,
        from_role=data.from_role,
        message=data.message,
        received_at=data.received_at or datetime.now(timezone.utc).isoformat(),
        turn_number=data.turn_number,
        merchant_ctx=merchant_ctx,
        category_ctx=category_ctx
    )
    return result


# Global composition helper for direct Python calls / test pair generation
def compose(category: dict, merchant: dict, trigger: dict, customer: dict | None = None) -> dict:
    """Standalone Python API matching Section 7.1 of Challenge Brief."""
    return engine.compose(category, merchant, trigger, customer)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
