class ScoringError(Exception):
    code = "scoring_error"


class InvalidRubricError(ScoringError):
    code = "invalid_rubric"


class InvalidProviderOutputError(ScoringError):
    code = "invalid_provider_output"


class ProviderRetryExhaustedError(ScoringError):
    code = "provider_retry_exhausted"


class AnswerGuardrailError(ScoringError):
    code = "answer_guardrail"


class MaxQueriesPerStateError(ScoringError):
    code = "max_queries_per_state"
