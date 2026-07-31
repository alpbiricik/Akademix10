from app.schemas.dtos import StructuredScoringResultDTO

_results: dict[tuple[str, str], StructuredScoringResultDTO] = {}
_query_counts: dict[tuple[str, str], int] = {}


def get_query_count(session_id: str, state_id: str) -> int:
    return _query_counts.get((session_id, state_id), 0)


def increment_query_count(session_id: str, state_id: str) -> int:
    key = (session_id, state_id)
    _query_counts[key] = _query_counts.get(key, 0) + 1
    return _query_counts[key]


def save_scoring_result(result: StructuredScoringResultDTO) -> StructuredScoringResultDTO:
    _results[(result.sessionId, result.stateId)] = result
    return result


def get_scoring_result(session_id: str, state_id: str) -> StructuredScoringResultDTO | None:
    return _results.get((session_id, state_id))


def list_scoring_results() -> list[StructuredScoringResultDTO]:
    return sorted(_results.values(), key=lambda item: (item.sessionId, item.stateId, item.generatedAt, item.answerRef))


def reset_mock_scoring_store() -> None:
    _results.clear()
    _query_counts.clear()
