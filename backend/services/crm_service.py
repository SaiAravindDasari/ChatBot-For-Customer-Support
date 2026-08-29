"""
CRM & Helpdesk Integration Service for QueryDesk.
Formats and exports conversations to Zendesk, Jira Service Management, and Freshdesk formats,
and dispatches signed HMAC-SHA256 webhooks to external enterprise endpoints.
"""

import hmac
import hashlib
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

class CRMService:
    def __init__(self):
        self.registered_webhooks: List[Dict[str, Any]] = [
            {
                "id": "wh-default-01",
                "name": "Enterprise Helpdesk Webhook",
                "url": "https://httpbin.org/post",
                "events": ["ticket.escalated", "ticket.resolved"],
                "active": True,
                "secret": "querydesk-wh-secret-key"
            }
        ]

    def export_zendesk_ticket(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        priority: str = "normal",
        language: str = "en",
        requester_email: str = "customer@example.com"
    ) -> Dict[str, Any]:
        """Format ticket for Zendesk Support REST API v2."""
        z_priority = "urgent" if priority.lower() in ("high", "critical") else "normal"
        
        # Build comment thread
        formatted_comments = []
        for m in messages:
            sender = m.get("role", "user").title()
            content = m.get("content", "")
            formatted_comments.append(f"[{sender}]: {content}")
            
        full_body = "\n".join(formatted_comments) if formatted_comments else "No message history."
        subject = f"QueryDesk Escalation: Session {session_id[:12]}"
        
        return {
            "ticket": {
                "subject": subject,
                "requester": {"email": requester_email, "name": f"Customer {session_id[:6]}"},
                "comment": {"body": full_body, "public": True},
                "priority": z_priority,
                "tags": ["querydesk_ai", "automated_escalation", f"lang_{language}"],
                "custom_fields": [
                    {"id": 360012345678, "value": session_id}
                ]
            }
        }

    def export_jira_issue(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        priority: str = "Medium",
        project_key: str = "SUP"
    ) -> Dict[str, Any]:
        """Format issue for Atlassian Jira Cloud REST API v3."""
        jira_prio = "High" if priority.lower() in ("high", "critical") else "Medium"
        description_lines = [f"*Session ID:* {session_id}\n*Conversation History:*"]
        for m in messages:
            description_lines.append(f"- *{m.get('role', 'user')}*: {m.get('content', '')}")
            
        return {
            "fields": {
                "project": {"key": project_key},
                "summary": f"QueryDesk Support Case: {session_id[:8]}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "\n".join(description_lines)}]
                        }
                    ]
                },
                "issuetype": {"name": "Support"},
                "priority": {"name": jira_prio},
                "labels": ["ai-chatbot", "querydesk", "escalation"]
            }
        }

    def export_freshdesk_ticket(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        priority: str = "Medium",
        email: str = "customer@example.com"
    ) -> Dict[str, Any]:
        """Format ticket for Freshdesk Tickets API."""
        fd_prio = 3 if priority.lower() in ("high", "critical") else 2 # 1: Low, 2: Med, 3: High, 4: Urgent
        formatted = "<br>".join([f"<b>{m.get('role')}:</b> {m.get('content')}" for m in messages])
        
        return {
            "subject": f"QueryDesk Escalation: {session_id[:10]}",
            "description": formatted or "Empty transcript",
            "email": email,
            "priority": fd_prio,
            "status": 2, # Open
            "source": 7, # Chat
            "tags": ["querydesk_ai", "escalated"]
        }

    def sign_webhook_payload(self, payload_bytes: bytes, secret: str) -> str:
        """Sign payload using HMAC-SHA256."""
        return "sha256=" + hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()

    async def dispatch_event(self, event_type: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dispatch event payload to all active registered webhooks."""
        results = []
        payload_dict = {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "timestamp": int(time.time()),
            "data": data
        }
        payload_json = json.dumps(payload_dict)
        payload_bytes = payload_json.encode('utf-8')

        for hook in self.registered_webhooks:
            if not hook.get("active") or event_type not in hook.get("events", []):
                continue
                
            secret = hook.get("secret", "default-secret")
            signature = self.sign_webhook_payload(payload_bytes, secret)
            headers = {
                "Content-Type": "application/json",
                "X-QueryDesk-Signature": signature,
                "X-QueryDesk-Event": event_type
            }

            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.post(hook["url"], content=payload_bytes, headers=headers)
                    results.append({
                        "webhook_id": hook["id"],
                        "url": hook["url"],
                        "status": "delivered",
                        "status_code": resp.status_code
                    })
            except Exception as e:
                logger.warning(f"Failed to dispatch webhook {hook['url']}: {e}")
                results.append({
                    "webhook_id": hook["id"],
                    "url": hook["url"],
                    "status": "failed",
                    "error": str(e)
                })

        return results

    def add_webhook(self, name: str, url: str, events: List[str], secret: Optional[str] = None) -> Dict[str, Any]:
        """Register a new webhook destination."""
        hook = {
            "id": f"wh-{uuid.uuid4().hex[:8]}",
            "name": name,
            "url": url,
            "events": events or ["ticket.escalated"],
            "active": True,
            "secret": secret or uuid.uuid4().hex
        }
        self.registered_webhooks.append(hook)
        return hook
