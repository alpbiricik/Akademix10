from hashlib import sha256

from app.schemas.dtos import DimensionScoreDTO, GuardrailFlagDTO, ProviderMetadataDTO, ProviderRequestDTO, ProviderScoringResponseDTO


class MockScoringProvider:
    provider_name = "mock"

    def score(self, request: ProviderRequestDTO) -> ProviderScoringResponseDTO:
        normalized = " ".join(request.answerText.lower().split())
        digest = sha256(f"{request.sessionId}|{request.stateId}|{normalized}".encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)
        answer_len = len(normalized)
        length_bonus = 10 if answer_len > 180 else 6 if answer_len > 80 else 2
        discovery_bonus = 4 if any(word in normalized for word in ["why", "what", "how", "neden", "nasıl", "?"]) else 0
        empathy_bonus = 4 if any(word in normalized for word in ["understand", "concern", "haklı", "anlıyorum", "empathy"]) else 0

        scores: list[DimensionScoreDTO] = []
        for index, dimension in enumerate(request.rubric.dimensions):
            jitter = ((seed >> (index * 4)) & 0xF) % 7
            raw = 64 + length_bonus + discovery_bonus + jitter
            if dimension.id == "empathy":
                raw += empathy_bonus
            if dimension.id == "confidence":
                raw += 2
            score = max(dimension.minScore, min(dimension.maxScore, raw))
            scores.append(
                DimensionScoreDTO(
                    dimensionId=dimension.id,
                    name=dimension.name,
                    score=round(score, 2),
                    rationale=f"Mock score based on answer specificity for {dimension.name.lower()}.",
                )
            )

        flags = []
        if "ignore previous" in normalized or "system prompt" in normalized:
            flags.append(GuardrailFlagDTO(code="prompt_injection_pattern", message="Answer text contains instruction-like content.", severity="warning"))

        return ProviderScoringResponseDTO(
            dimensionScores=scores,
            conciseLearnerFeedback="Clear practice response with a useful direction for the customer conversation.",
            strengths=["Acknowledges the scenario.", "Moves toward a practical next step."],
            improvementAreas=["Add one sharper discovery question.", "Tie the recommendation to a measurable outcome."],
            recommendedNextAction="complete_state",
            guardrailFlags=flags,
            providerMetadata=ProviderMetadataDTO(provider=self.provider_name, model="deterministic-mock-v1", attemptCount=1, fallbackUsed=False),
        )
