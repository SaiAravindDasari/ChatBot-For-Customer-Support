import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SlotFiller:
    def __init__(self):
        self.dialog_flows: Dict[str, Any] = {}
        data_path = Path(__file__).parent.parent / 'data' / 'dialog_flows.json'
        try:
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "flows" in data:
                        self.dialog_flows = data["flows"]
                    elif isinstance(data, dict):
                        self.dialog_flows = data
                    logger.info(f"Loaded {len(self.dialog_flows)} dialog flows")
            else:
                logger.warning(f"Dialog flows file not found: {data_path}")
        except Exception as e:
            logger.error(f"Error loading dialog flows: {e}")

    def get_flow(self, intent: str) -> Optional[Dict[str, Any]]:
        return self.dialog_flows.get(intent)

    def get_required_slots(self, intent: str) -> List[str]:
        flow = self.get_flow(intent)
        if not flow:
            return []
        raw_slots = flow.get("required_slots", [])
        if isinstance(raw_slots, list):
            return [s.get("name") if isinstance(s, dict) else s for s in raw_slots]
        elif isinstance(raw_slots, dict):
            return list(raw_slots.keys())
        return []

    def get_missing_slots(self, intent: str, filled_slots: Dict[str, Any]) -> List[str]:
        required = self.get_required_slots(intent)
        return [slot for slot in required if not filled_slots.get(slot)]

    def get_slot_prompt(self, intent: str, slot_name: str, is_retry: bool = False) -> str:
        flow = self.get_flow(intent)
        if not flow:
            return f"Could you please provide your {slot_name}?"
        raw_slots = flow.get("required_slots", [])
        if isinstance(raw_slots, list):
            for s in raw_slots:
                if isinstance(s, dict) and s.get("name") == slot_name:
                    if is_retry and s.get("reprompt"):
                        return s.get("reprompt")
                    return s.get("prompt", f"Please provide your {slot_name}.")
        elif isinstance(raw_slots, dict):
            s_info = raw_slots.get(slot_name, {})
            prompts = s_info.get("prompts", [f"Please provide your {slot_name}."])
            return prompts[0] if prompts else f"Please provide your {slot_name}."
        return f"Could you please provide your {slot_name}?"

    def try_fill_slots(self, intent: str, entities: Dict[str, Any], filled_slots: Dict[str, Any]) -> Dict[str, Any]:
        updated_slots = filled_slots.copy()
        required = self.get_required_slots(intent)
        
        # Normalize entity keys for matching
        norm_entities = {}
        for k, v in entities.items():
            val = v[0] if isinstance(v, list) and len(v) > 0 else v
            if val:
                norm_entities[k.lower()] = str(val)
                norm_entities[k.upper()] = str(val)
                norm_entities[k] = str(val)

        for slot in required:
            slot_l = slot.lower()
            if not updated_slots.get(slot):
                # Try direct match
                if slot in norm_entities:
                    updated_slots[slot] = norm_entities[slot]
                elif slot_l in norm_entities:
                    updated_slots[slot] = norm_entities[slot_l]
                # Special slot mappings
                elif "order" in slot_l and ("order_id" in norm_entities or "ORDER_ID" in norm_entities):
                    updated_slots[slot] = norm_entities.get("order_id") or norm_entities.get("ORDER_ID")
                elif "email" in slot_l and ("email" in norm_entities or "EMAIL" in norm_entities):
                    updated_slots[slot] = norm_entities.get("email") or norm_entities.get("EMAIL")
                elif "phone" in slot_l and ("phone" in norm_entities or "PHONE" in norm_entities):
                    updated_slots[slot] = norm_entities.get("phone") or norm_entities.get("PHONE")

        return updated_slots

    def all_slots_filled(self, intent: str, filled_slots: Dict[str, Any]) -> bool:
        missing = self.get_missing_slots(intent, filled_slots)
        return len(missing) == 0

    def get_success_message(self, intent: str, filled_slots: Dict[str, Any]) -> Optional[str]:
        flow = self.get_flow(intent)
        if not flow:
            return None
        msg_template = flow.get("success_message")
        if not msg_template:
            return None
        try:
            return msg_template.format(**filled_slots)
        except Exception:
            return msg_template

    def get_follow_up(self, intent: str) -> str:
        flow = self.get_flow(intent)
        if flow and "follow_up" in flow:
            return flow["follow_up"]
        return "Is there anything else I can help you with today?"

    def get_action(self, intent: str) -> str:
        flow = self.get_flow(intent)
        if flow and "action" in flow:
            return flow["action"]
        return f"execute_{intent}"

    def needs_slot_filling(self, intent: str) -> bool:
        return len(self.get_required_slots(intent)) > 0
