from typing import Protocol

from app.schemas.dtos import ConversationRequestDTO, ConversationResultDTO

MAX_CONVERSATION_TURNS = 3
MAX_CONVERSATION_INPUT_CHARS = 2000
MAX_CONVERSATION_OUTPUT_CHARS = 700
MAX_CONVERSATION_PROVIDER_RETRIES = 1
CONVERSATION_PROVIDER_TIMEOUT_SECONDS = 30


class ConversationProvider(Protocol):
    provider_name: str

    def continue_conversation(self, request: ConversationRequestDTO) -> ConversationResultDTO:
        ...
