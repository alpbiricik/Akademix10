from app.db.supabase_rest import SupabaseUserClient
from app.schemas.dtos import (StructuredScoringResultDTO, SkillImpactDTO, DimensionScoreDTO, GuardrailFlagDTO, ProviderMetadataDTO, TokenCostMetadataDTO)


def read_scoring_results(client: SupabaseUserClient, session_id: str) -> list[StructuredScoringResultDTO]:
    feedback_rows = client.select("session_feedback", f"select=*&session_id=eq.{session_id}&order=created_at.asc")
    if not feedback_rows:
        return []
    skill_rows = client.select("skill_scores", f"select=*&session_id=eq.{session_id}")
    skills_by_state: dict[str, list[SkillImpactDTO]] = {}
    for row in skill_rows:
        state_id = row.get("state_id")
        if not state_id:
            continue
        skills_by_state.setdefault(state_id, []).append(
            SkillImpactDTO(
                skill=row.get("skill", ""),
                score=row.get("score"),
                delta=row.get("delta", 0),
                sourceDimensionIds=[],
            )
        )

    results: list[StructuredScoringResultDTO] = []
    for row in feedback_rows:
        metadata = row.get("metadata") or {}
        dimensions = [
            DimensionScoreDTO(
                dimensionId=str(item.get("label", "")).lower().replace(" ", "_") or "dimension",
                name=item.get("label", ""),
                score=item.get("score", 0),
                rationale="",
            )
            for item in row.get("dimensions") or []
        ]
        guardrails = [
            GuardrailFlagDTO(
                code=item.get("code", ""),
                message=item.get("message", ""),
                severity=item.get("severity", "info"),
            )
            for item in metadata.get("guardrailFlags") or []
        ]
        results.append(
            StructuredScoringResultDTO(
                schemaVersion=metadata.get("schemaVersion", "1.0"),
                sessionId=session_id,
                stateId=row["state_id"],
                answerRef=f"{session_id}:{row['state_id']}:final",
                rubricId=metadata.get("rubricId", ""),
                rubricVersion=metadata.get("rubricVersion", ""),
                overallScore=row.get("overall_score", 0),
                dimensionScores=dimensions,
                conciseLearnerFeedback=row.get("feedback_text", ""),
                strengths=[],
                improvementAreas=[row.get("improvement_suggestion", "")] if row.get("improvement_suggestion") else [],
                recommendedNextAction=row.get("next_action") if row.get("next_action") in {"continue", "retry_state", "review_feedback", "complete_state"} else "complete_state",
                skillImpacts=skills_by_state.get(row["state_id"], []),
                guardrailFlags=guardrails,
                providerMetadata=ProviderMetadataDTO(
                    provider=row.get("provider") or "unknown",
                    model=row.get("model_name") or "unknown",
                ),
                tokenCostMetadata=TokenCostMetadataDTO(),
                generatedAt=row.get("created_at") or "",
            )
        )
    return results
