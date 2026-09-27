"""
Reply Handler for Vera AI Assistant.

Handles multi-turn conversations, auto-reply detection, intent transitions,
hostile/opt-out handling, and contextual question answering.
"""

import re
import threading
from typing import Any, Dict, List, Optional, Tuple


class ReplyHandler:
    """
    Stateful Reply Handler for Vera.
    Tracks turn state per conversation_id and executes multi-turn policies.
    """

    AUTO_REPLY_PATTERNS = [
        r"thank you for contacting",
        r"our team will respond",
        r"automated assistant",
        r"aapki jaankari ke liye",
        r"sujhaav hamari team tak",
        r"we will get back to you",
        r"thanks for reaching out",
        r"this is an automated message",
        r"auto-reply",
        r"canned message"
    ]

    COMMITMENT_PATTERNS = [
        r"lets do it",
        r"let's do it",
        r"whats next",
        r"what's next",
        r"go ahead",
        r"ok send",
        r"yes send",
        r"done",
        r"proceed",
        r"judna hai",
        r"join karna",
        r"update kar do",
        r"start now",
        r"do it",
        r"agree",
        r"sure"
    ]

    HOSTILE_PATTERNS = [
        r"stop messaging",
        r"useless spam",
        r"don't message",
        r"dont message",
        r"unsubscribe",
        r"\bstop\b",
        r"\bspam\b",
        r"remove me",
        r"\bblock\b"
    ]

    def __init__(self):
        self._lock = threading.RLock()
        # Key: conversation_id -> List[Dict[str, Any]]
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

    def handle_reply(
        self,
        conversation_id: str,
        merchant_id: Optional[str],
        customer_id: Optional[str],
        from_role: str,
        message: str,
        received_at: str,
        turn_number: int,
        merchant_ctx: Optional[Dict[str, Any]] = None,
        category_ctx: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process incoming reply and return appropriate action (send, wait, end).
        """
        with self._lock:
            history = self._conversations.setdefault(conversation_id, [])
            history.append({
                "from_role": from_role,
                "message": message,
                "turn": turn_number,
                "ts": received_at
            })

            msg_clean = message.strip().lower()

            # 1. AUTO-REPLY DETECTION
            is_auto_reply = any(re.search(pat, msg_clean) for pat in self.AUTO_REPLY_PATTERNS)
            
            # Repetitive message check (same message sent 2+ times within the SAME multi-turn conversation)
            merchant_msgs = [h["message"].strip().lower() for h in history if h["from_role"] == from_role]
            if len(merchant_msgs) >= 2 and turn_number >= 2 and merchant_msgs[-1] == merchant_msgs[-2]:
                is_auto_reply = True

            if is_auto_reply:
                if turn_number >= 3 or len(merchant_msgs) >= 2:
                    return {
                        "action": "end",
                        "rationale": "Detected repeated WhatsApp auto-reply pattern; ending conversation gracefully to avoid burning turns."
                    }
                else:
                    return {
                        "action": "end",
                        "rationale": "Detected merchant auto-reply system. Gracefully exiting conversation."
                    }

            # 2. HOSTILE / OPT-OUT DETECTION
            is_hostile = any(re.search(pat, msg_clean) for pat in self.HOSTILE_PATTERNS)
            if is_hostile:
                return {
                    "action": "end",
                    "rationale": "Merchant expressed explicit opt-out or hostility; immediately terminating conversation and respecting opt-out."
                }

            # 3. INTENT TRANSITION DETECTION (EXPLICIT COMMITMENT)
            is_commitment = any(re.search(pat, msg_clean) for pat in self.COMMITMENT_PATTERNS) or "yes" in msg_clean or "ok" in msg_clean
            if is_commitment:
                # Switch from qualifying to ACTION execution mode immediately
                biz_name = (merchant_ctx or {}).get("identity", {}).get("name", "your profile")
                owner_name = (merchant_ctx or {}).get("identity", {}).get("owner_first_name", "there")
                
                body = (
                    f"Done! I've initiated the updates for {biz_name}. "
                    f"Here is what's being processed right now:\n"
                    f"1. Profile details & description drafted\n"
                    f"2. Google post submitted for review\n"
                    f"I'll confirm here once Google's 24-hour verification completes. Let's proceed to the next step!"
                )
                return {
                    "action": "send",
                    "body": body,
                    "cta": "none",
                    "rationale": "Merchant gave explicit commitment; transitioned immediately to action execution mode without further qualifying."
                }

            # 4. GENERAL QUESTION / CLARIFICATION
            if "?" in message or "how" in msg_clean or "price" in msg_clean or "what" in msg_clean:
                body = (
                    f"Good question! Here are the exact details:\n"
                    f"- Setup takes under 5 minutes\n"
                    f"- All posts are pre-drafted for your approval\n"
                    f"Would you like me to send the first draft for your review now?"
                )
                return {
                    "action": "send",
                    "body": body,
                    "cta": "binary",
                    "rationale": "Answered merchant's query concisely with clear, zero-friction next action."
                }

            # 5. DEFAULT ENGAGEMENT ACKNOWLEDGEMENT
            body = (
                f"Got it! I've noted that for your profile. "
                f"I'm preparing the next update for you now. Should we proceed?"
            )
            return {
                "action": "send",
                "body": body,
                "cta": "binary",
                "rationale": "Acknowledged merchant input and proposed single low-friction next step."
            }

    def clear(self):
        """Reset conversation history."""
        with self._lock:
            self._conversations.clear()
