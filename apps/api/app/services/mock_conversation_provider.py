from app.schemas.dtos import ConversationRequestDTO, ConversationResultDTO, ProviderMetadataDTO


class MockConversationProvider:
    provider_name = "mock"
    model = "mock-conversation-v1"

    def continue_conversation(self, request: ConversationRequestDTO) -> ConversationResultDTO:
        should_complete = request.turnNumber >= request.maxTurns or (
            request.turnNumber >= request.minTurns and any(word in request.sanitizedLearnerTurn.lower() for word in {"next", "commit", "meeting", "plan", "takip"})
        )
        if should_complete:
            text = "Anladim. Bu yanitla gorusmeyi kapatabiliriz; net bir sonraki adim ve sakin bir ton kurdun."
            action = "complete"
        else:
            focus = request.allowedTopics[0] if request.allowedTopics else "senaryo"
            text = f"{request.persona}: Bunu duyuyorum. {focus} acisindan bir sonraki cumleni nasil kurardin?"
            action = "continue"
        return ConversationResultDTO(
            assistantText=text,
            action=action,
            reasonCode="mock_turn_boundary",
            providerMetadata=ProviderMetadataDTO(provider=self.provider_name, model=self.model),
        )
