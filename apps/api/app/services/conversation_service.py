from app.core.config import CONVERSATION_CONTEXT_TTL_SECONDS, CONVERSATION_LANGUAGE, CONVERSATION_PROVIDER, GEMINI_API_KEY, GEMINI_CONVERSATION_MODEL, GEMINI_CONVERSATION_THINKING_LEVEL
from app.schemas.dtos import (
    ConversationConfigDTO,
    ConversationRequestDTO,
    ConversationResultDTO,
    ConversationTurnDTO,
    TrainingSessionDTO,
    TrainingStateDTO,
)
from app.services.conversation_cache import InMemoryConversationCache, conversation_cache
from app.services.conversation_errors import ConversationProviderConfigurationError, ConversationProviderError, ConversationStateError
from app.services.conversation_guardrails import evaluate_input_guardrail, fallback_result, validate_output_guardrail
from app.services.conversation_provider import ConversationProvider, MAX_CONVERSATION_PROVIDER_RETRIES, MAX_CONVERSATION_TURNS
from app.services.gemini_conversation_provider import GeminiConversationProvider


def get_conversation_provider() -> ConversationProvider:
    if CONVERSATION_PROVIDER and CONVERSATION_PROVIDER != "gemini":
        raise ConversationProviderConfigurationError("CONVERSATION_PROVIDER must be gemini.")
    return GeminiConversationProvider(api_key=GEMINI_API_KEY, model=GEMINI_CONVERSATION_MODEL, thinking_level=GEMINI_CONVERSATION_THINKING_LEVEL)


def default_conversation_config(state: TrainingStateDTO) -> ConversationConfigDTO:
    allowed = state.skillTags or ["communication"]
    return ConversationConfigDTO(
        minTurns=1,
        maxTurns=3,
        language=CONVERSATION_LANGUAGE,
        persona="Training scenario counterpart",
        scenario=state.prompt,
        objective=f"Learner practices: {', '.join(allowed)}",
        conversationInstructions="Stay in role. React naturally and ask at most one concise follow-up.",
        allowedTopics=allowed,
        completionGuidance="Complete once the learner has made a relevant response and the turn budget is reached.",
    )


def get_state_conversation_config(state: TrainingStateDTO) -> ConversationConfigDTO:
    config = state.conversationConfig or default_conversation_config(state)
    max_turns = max(1, min(config.maxTurns, MAX_CONVERSATION_TURNS))
    min_turns = max(1, min(config.minTurns, max_turns))
    language = (config.language or CONVERSATION_LANGUAGE).strip().lower() or CONVERSATION_LANGUAGE
    return config.model_copy(update={"minTurns": min_turns, "maxTurns": max_turns, "language": language})


def _cache_key(session_id: str, state_id: str) -> str:
    return f"conversation:{session_id}:{state_id}"


def _load_context(cache: InMemoryConversationCache, session_id: str, state_id: str) -> dict:
    return cache.get(_cache_key(session_id, state_id)) or {"turns": [], "complete": False}


def _save_context(cache: InMemoryConversationCache, session_id: str, state_id: str, payload: dict) -> None:
    cache.put(_cache_key(session_id, state_id), payload, ttl_seconds=CONVERSATION_CONTEXT_TTL_SECONDS)


def reset_conversation_context(session_id: str, state_id: str, cache: InMemoryConversationCache = conversation_cache) -> None:
    cache.delete(_cache_key(session_id, state_id))


def _assistant_expects_learner_reply(text: str) -> bool:
    normalized = text.strip().lower()
    if "?" in normalized:
        return True
    followup_markers = (
        "how would you",
        "what would you",
        "can you",
        "could you",
        "nasil",
        "ne dersin",
        "yanitlar misin",
        "anlatir misin",
        "cevabin",
        "cevap ver",
    )
    return any(marker in normalized for marker in followup_markers)


def start_training_conversation(
    session: TrainingSessionDTO,
    state: TrainingStateDTO,
    provider: ConversationProvider | None = None,
    cache: InMemoryConversationCache = conversation_cache,
) -> ConversationResultDTO:
    # Idempotent opening: return cached result before checking guards
    # so duplicate calls from React rerenders/StrictMode never get 409
    context = _load_context(cache, session.id, state.id)
    if context.get("opening"):
        return ConversationResultDTO.model_validate(context["opening"])

    if state.id in session.completedStateIds:
        raise ConversationStateError("Conversation is already complete for this state.")
    if state.id != session.currentStateId:
        raise ConversationStateError("Conversation state must be the current training state.")
    if not (state.avatarEnabled or state.type in {"avatar", "live_avatar", "roleplay"}):
        raise ConversationStateError("State is not configured for live conversation.")

    config = get_state_conversation_config(state)
    if context.get("complete"):
        raise ConversationStateError("Conversation is already complete for this state.")

    active_provider = provider or get_conversation_provider()
    request = ConversationRequestDTO(
        sessionId=session.id,
        stateId=state.id,
        turnNumber=0,
        language=config.language,
        persona=config.persona,
        scenario=config.scenario,
        objective=config.objective,
        conversationInstructions=config.conversationInstructions,
        allowedTopics=config.allowedTopics,
        completionGuidance=config.completionGuidance,
        sanitizedLearnerTurn="AI_OPENING_TURN: Start this bounded roleplay. Ask the learner one concise opening question in persona.",
        temporaryContext=[],
        minTurns=config.minTurns,
        maxTurns=config.maxTurns,
    )

    last_error: Exception | None = None
    for attempt in range(1, MAX_CONVERSATION_PROVIDER_RETRIES + 2):
        try:
            result = active_provider.continue_conversation(request)
            result.providerMetadata.attemptCount = attempt
            result = validate_output_guardrail(result, config)
            break
        except Exception as error:
            last_error = error
    else:
        raise ConversationProviderError(f"Gemini opening retry limit exhausted: {type(last_error).__name__ if last_error else 'unknown'}")

    result.action = "continue"
    _save_context(
        cache,
        session.id,
        state.id,
        {"turns": context.get("turns", []), "complete": False, "opening": result.model_dump()},
    )
    return result


def continue_training_conversation(
    session: TrainingSessionDTO,
    state: TrainingStateDTO,
    learner_text: str,
    provider: ConversationProvider | None = None,
    cache: InMemoryConversationCache = conversation_cache,
) -> tuple[ConversationResultDTO, int, bool, object]:
    if state.id in session.completedStateIds:
        raise ConversationStateError("Conversation is already complete for this state.")
    if state.id != session.currentStateId:
        raise ConversationStateError("Conversation state must be the current training state.")
    if not (state.avatarEnabled or state.type in {"avatar", "live_avatar", "roleplay"}):
        raise ConversationStateError("State is not configured for live conversation.")

    config = get_state_conversation_config(state)
    context = _load_context(cache, session.id, state.id)
    if context.get("complete"):
        raise ConversationStateError("Conversation is already complete for this state.")

    previous_turns = [ConversationTurnDTO.model_validate(turn) for turn in context.get("turns", [])]
    opening = ConversationResultDTO.model_validate(context["opening"]) if context.get("opening") else None
    turn_number = len(previous_turns) + 1
    if turn_number > config.maxTurns:
        result = fallback_result()
        _save_context(cache, session.id, state.id, {"turns": [turn.model_dump() for turn in previous_turns], "complete": True})
        return result, turn_number, True, evaluate_input_guardrail(learner_text, config)

    input_guardrail = evaluate_input_guardrail(learner_text, config)
    if input_guardrail.decision == "block":
        result = fallback_result()
        return result, turn_number, False, input_guardrail
    if input_guardrail.decision == "redirect":
        result = ConversationResultDTO(
            assistantText=input_guardrail.message or fallback_result().assistantText,
            action="continue",
            reasonCode=input_guardrail.reasonCode,
            providerMetadata=fallback_result(provider="guardrail", model="input-redirect").providerMetadata,
        )
        return result, turn_number, False, input_guardrail

    active_provider = provider or get_conversation_provider()
    request = ConversationRequestDTO(
        sessionId=session.id,
        stateId=state.id,
        turnNumber=turn_number,
        language=config.language,
        persona=config.persona,
        scenario=config.scenario,
        objective=config.objective,
        conversationInstructions=config.conversationInstructions,
        allowedTopics=config.allowedTopics,
        completionGuidance=config.completionGuidance,
        sanitizedLearnerTurn=input_guardrail.safeText,
        temporaryContext=([ConversationTurnDTO(turnNumber=0, learnerText="", assistantText=opening.assistantText)] if opening else []) + previous_turns,
        minTurns=config.minTurns,
        maxTurns=config.maxTurns,
    )

    last_error: Exception | None = None
    for attempt in range(1, MAX_CONVERSATION_PROVIDER_RETRIES + 2):
        try:
            result = active_provider.continue_conversation(request)
            result.providerMetadata.attemptCount = attempt
            result = validate_output_guardrail(result, config)
            break
        except Exception as error:
            last_error = error
    else:
        raise ConversationProviderError(f"Gemini conversation retry limit exhausted: {type(last_error).__name__ if last_error else 'unknown'}")

    if result.providerMetadata.fallbackUsed:
        result.action = "complete"
    elif turn_number >= config.maxTurns:
        result.action = "complete"
    elif result.action == "complete" and _assistant_expects_learner_reply(result.assistantText):
        result.action = "continue"
    if not result.providerMetadata.fallbackUsed and turn_number < config.minTurns and result.action == "complete":
        result.action = "continue"

    new_turn = ConversationTurnDTO(turnNumber=turn_number, learnerText=input_guardrail.safeText, assistantText=result.assistantText)
    complete = result.action == "complete"
    payload = {"turns": [turn.model_dump() for turn in previous_turns + [new_turn]], "complete": complete}
    if opening:
        payload["opening"] = opening.model_dump()
    _save_context(cache, session.id, state.id, payload)
    return result, turn_number, complete, input_guardrail
