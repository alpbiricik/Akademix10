import re

from pydantic import ValidationError

from app.schemas.dtos import (
    ConversationConfigDTO,
    ConversationGuardrailResultDTO,
    ConversationResultDTO,
    ProviderMetadataDTO,
)
from app.services.conversation_provider import MAX_CONVERSATION_INPUT_CHARS, MAX_CONVERSATION_OUTPUT_CHARS

FALLBACK_TEXT = "Bu senaryodaki gorusmeye devam edelim. Mevcut rolde kalarak nasil yanit verirdin?"

_PROMPT_INJECTION_PATTERNS = [
    r"\bignore\b.*\b(previous|all|instructions?)\b",
    r"\bforget\b.*\b(training|role|instructions?)\b",
    r"\boverride\b.*\b(instructions?|rules?|role)\b",
    r"\byou are not\b",
    r"\bact as\b.*\b(assistant|developer|system|different)\b",
]

_INSTRUCTION_EXTRACTION_PATTERNS = [
    r"\bsystem prompt\b",
    r"\bdeveloper instructions?\b",
    r"\bhidden instructions?\b",
    r"\bshow\b.*\b(prompt|instructions?)\b",
    r"\breveal\b.*\b(prompt|instructions?)\b",
]

_RUBRIC_EXTRACTION_PATTERNS = [
    r"\brubric\b",
    r"\banswer key\b",
    r"\b100 points?\b",
    r"\bfull score\b",
    r"\bscoring\b.*\b(criteria|weights?|internals?)\b",
]

_UNSAFE_PATTERNS = [
    r"\bself[- ]?harm\b",
    r"\bsuicide\b",
    r"\bkill\b",
    r"\bexplosive\b",
]

_OFF_TOPIC_PATTERNS = [
    r"\b(write|generate|debug)\b.*\b(code|python|javascript|sql)\b",
    r"\b(recipe|weather|sports?|movie|song|lyrics?)\b",
    r"\btranslate\b.*\b(this|text|paragraph)\b",
    r"\b(make|tell)\b.*\b(joke|poem)\b",
]


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _topic_text(config: ConversationConfigDTO) -> str:
    return " ".join([config.scenario, config.objective, config.persona, *config.allowedTopics]).lower()


def _word_tokens(text: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[^\W\d_]{4,}", text, flags=re.UNICODE)}


def evaluate_input_guardrail(learner_text: str, config: ConversationConfigDTO) -> ConversationGuardrailResultDTO:
    normalized = " ".join(learner_text.split())
    if not normalized or len(normalized) > MAX_CONVERSATION_INPUT_CHARS:
        return ConversationGuardrailResultDTO(decision="block", reasonCode="state_violation", safeText="", message=FALLBACK_TEXT)
    if _matches(_UNSAFE_PATTERNS, normalized):
        return ConversationGuardrailResultDTO(decision="block", reasonCode="unsafe_content", safeText="", message=FALLBACK_TEXT)
    if _matches(_INSTRUCTION_EXTRACTION_PATTERNS, normalized):
        return ConversationGuardrailResultDTO(decision="block", reasonCode="instruction_extraction", safeText="", message=FALLBACK_TEXT)
    if _matches(_RUBRIC_EXTRACTION_PATTERNS, normalized):
        return ConversationGuardrailResultDTO(decision="block", reasonCode="rubric_extraction", safeText="", message=FALLBACK_TEXT)
    if _matches(_PROMPT_INJECTION_PATTERNS, normalized):
        return ConversationGuardrailResultDTO(decision="block", reasonCode="prompt_injection", safeText="", message=FALLBACK_TEXT)
    if _matches(_OFF_TOPIC_PATTERNS, normalized):
        return ConversationGuardrailResultDTO(decision="redirect", reasonCode="off_topic", safeText="", message=FALLBACK_TEXT)

    topic_words = _word_tokens(_topic_text(config))
    learner_words = _word_tokens(normalized)
    if topic_words and learner_words and topic_words.isdisjoint(learner_words) and normalized.endswith("?"):
        return ConversationGuardrailResultDTO(decision="redirect", reasonCode="off_topic", safeText="", message=FALLBACK_TEXT)

    return ConversationGuardrailResultDTO(decision="allow", reasonCode="in_scope", safeText=normalized)


def _contains_leakage(text: str) -> bool:
    return _matches(_INSTRUCTION_EXTRACTION_PATTERNS + _RUBRIC_EXTRACTION_PATTERNS, text)


def validate_output_guardrail(result: ConversationResultDTO, config: ConversationConfigDTO) -> ConversationResultDTO:
    if result.action not in {"continue", "complete"}:
        raise ValueError("Invalid conversation action.")
    text = " ".join(result.assistantText.split())
    if not text:
        raise ValueError("Conversation output is empty.")
    if len(text) > MAX_CONVERSATION_OUTPUT_CHARS:
        raise ValueError("Conversation output is too long.")
    if _contains_leakage(text):
        raise ValueError("Conversation output exposed protected instructions or rubric details.")
    if config.persona and re.search(r"\bas an ai\b|\bi am your coach\b|\bi cannot play\b", text, flags=re.IGNORECASE):
        raise ValueError("Conversation output escaped the configured persona.")
    return result.model_copy(update={"assistantText": text})


def fallback_result(provider: str = "guardrail", model: str = "deterministic-fallback") -> ConversationResultDTO:
    return ConversationResultDTO(
        assistantText=FALLBACK_TEXT,
        action="complete",
        reasonCode="safe_fallback",
        providerMetadata=ProviderMetadataDTO(provider=provider, model=model, fallbackUsed=True),
    )


def parse_provider_payload(payload: object, provider: str, model: str) -> ConversationResultDTO:
    try:
        if isinstance(payload, ConversationResultDTO):
            return payload
        if isinstance(payload, dict):
            metadata = payload.get("providerMetadata") or ProviderMetadataDTO(provider=provider, model=model).model_dump()
            return ConversationResultDTO(
                assistantText=payload.get("assistantText", ""),
                action=payload.get("action", "continue"),
                reasonCode=payload.get("reasonCode"),
                providerMetadata=ProviderMetadataDTO.model_validate(metadata),
            )
        return ConversationResultDTO.model_validate(payload)
    except (ValidationError, TypeError, ValueError) as error:
        raise ValueError("Malformed conversation provider response.") from error
