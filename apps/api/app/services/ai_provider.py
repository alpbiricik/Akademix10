from typing import Protocol

from app.schemas.dtos import ProviderRequestDTO, ProviderScoringResponseDTO

MAX_QUERIES_PER_STATE = 3
MAX_PROVIDER_RETRIES = 2
PROVIDER_TIMEOUT_SECONDS = 8
MIN_ANSWER_CHARS = 2
MAX_ANSWER_CHARS = 5000


class ScoringProvider(Protocol):
    provider_name: str

    def score(self, request: ProviderRequestDTO) -> ProviderScoringResponseDTO:
        ...
