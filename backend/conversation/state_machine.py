from enum import Enum
import logging
from .context import ConversationContext

logger = logging.getLogger(__name__)

class DialogState(Enum):
    GREETING = "GREETING"
    INTENT_DETECTED = "INTENT_DETECTED"
    SLOT_FILLING = "SLOT_FILLING"
    ACTION_EXECUTION = "ACTION_EXECUTION"
    FOLLOW_UP = "FOLLOW_UP"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"

class DialogStateMachine:
    def __init__(self):
        self.state = DialogState.GREETING
        self.transition_counter = 0
        self.max_slot_retries = 3
        self.current_slot_retries = 0

    def transition(self, event: str, context: ConversationContext) -> DialogState:
        known_events = {
            'escalate', 'manual_escalate', 'user_message', 'new_question',
            'slots_needed', 'slots_complete', 'slot_filled', 'max_retries',
            'force_execution', 'response_sent', 'satisfied'
        }
        if event not in known_events:
            logger.debug("DialogStateMachine encountered non-standard event: %s", event)

        if event in ('escalate', 'manual_escalate'):
            self.state = DialogState.ESCALATED
            context.escalated = True
            return self.state

        if self.state == DialogState.GREETING:
            if event in ('user_message', 'new_question'):
                self.state = DialogState.INTENT_DETECTED
        elif self.state == DialogState.INTENT_DETECTED:
            if event == 'slots_needed':
                self.state = DialogState.SLOT_FILLING
            elif event in ('slots_complete', 'user_message'):
                self.state = DialogState.ACTION_EXECUTION
        elif self.state == DialogState.SLOT_FILLING:
            if event == 'slot_filled':
                self.current_slot_retries = 0
            elif event in ('slots_complete', 'max_retries', 'force_execution'):
                self.state = DialogState.ACTION_EXECUTION
                self.current_slot_retries = 0
        elif self.state == DialogState.ACTION_EXECUTION:
            if event == 'response_sent':
                self.state = DialogState.FOLLOW_UP
        elif self.state in (DialogState.FOLLOW_UP, DialogState.RESOLVED, DialogState.ESCALATED):
            if event in ('user_message', 'new_question', 'slots_complete', 'slots_needed'):
                self.state = DialogState.INTENT_DETECTED
            elif event == 'satisfied':
                self.state = DialogState.RESOLVED
                context.resolved = True

        self.transition_counter += 1
        return self.state

    def get_state(self) -> DialogState:
        return self.state

    def reset(self) -> None:
        self.state = DialogState.GREETING
        self.transition_counter = 0
        self.current_slot_retries = 0

    def is_terminal(self) -> bool:
        return self.state in (DialogState.RESOLVED, DialogState.ESCALATED)
