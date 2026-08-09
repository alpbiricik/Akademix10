class ConversationError(Exception):
    code = "conversation_error"


class ConversationGuardrailError(ConversationError):
    code = "conversation_guardrail_blocked"


class ConversationStateError(ConversationError):
    code = "conversation_state_error"


class ConversationProviderConfigurationError(ConversationError):
    code = "conversation_provider_not_configured"


class ConversationProviderError(ConversationError):
    code = "conversation_provider_error"


class InvalidConversationProviderOutputError(ConversationError):
    code = "invalid_conversation_provider_output"


class ConversationProviderRetryExhaustedError(ConversationError):
    code = "conversation_provider_retry_exhausted"
