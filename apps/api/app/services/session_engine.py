from datetime import datetime, timezone

from app.schemas.dtos import FeedbackDimensionDTO, SessionAnswerDTO, SessionFeedbackDTO, SkillScoreDTO, StructuredScoringResultDTO, TrainingSessionDTO, TrainingStateDTO


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_current_state(session: TrainingSessionDTO, states: list[TrainingStateDTO]) -> TrainingStateDTO | None:
    return next((state for state in states if state.id == session.currentStateId), states[0] if states else None)


def get_next_state(session: TrainingSessionDTO, states: list[TrainingStateDTO]) -> TrainingStateDTO | None:
    current = get_current_state(session, states)
    if not current:
        return None
    index = states.index(current)
    return states[index + 1] if index + 1 < len(states) else None


def get_previous_state(session: TrainingSessionDTO, states: list[TrainingStateDTO]) -> TrainingStateDTO | None:
    current = get_current_state(session, states)
    if not current:
        return None
    index = states.index(current)
    return states[index - 1] if index > 0 else None


def complete_current_state(session: TrainingSessionDTO, states: list[TrainingStateDTO]) -> TrainingSessionDTO:
    current = get_current_state(session, states)
    if not current:
        return session
    if current.id not in session.completedStateIds:
        session.completedStateIds.append(current.id)
    session.status = "completed" if len(session.completedStateIds) >= len(states) else "in_progress"
    session.completedAt = now_iso() if session.status == "completed" else session.completedAt
    session.updatedAt = now_iso()
    return session


def submit_answer(session: TrainingSessionDTO, state_id: str, answer_text: str) -> TrainingSessionDTO:
    session.answers = [answer for answer in session.answers if answer.stateId != state_id]
    session.answers.append(SessionAnswerDTO(stateId=state_id, answerText=answer_text, submittedAt=now_iso()))
    session.updatedAt = now_iso()
    return session


def feedback_from_scoring_result(result: StructuredScoringResultDTO) -> SessionFeedbackDTO:
    return SessionFeedbackDTO(
        id=f"feedback-{result.stateId}",
        stateId=result.stateId,
        overallScore=result.overallScore,
        dimensions=[FeedbackDimensionDTO(label=score.name, score=int(round(score.score))) for score in result.dimensionScores],
        feedbackText=result.conciseLearnerFeedback,
        improvementSuggestion=" ".join(result.improvementAreas[:2]) or "Continue practicing this behavior.",
        nextAction=result.recommendedNextAction,
        createdAt=result.generatedAt,
    )


def apply_scoring_result(session: TrainingSessionDTO, result: StructuredScoringResultDTO) -> TrainingSessionDTO:
    feedback = feedback_from_scoring_result(result)
    session.feedback = [item for item in session.feedback if item.stateId != feedback.stateId]
    session.feedback.append(feedback)
    impacts = {impact.skill: impact for impact in result.skillImpacts}
    existing = {score.skill: score for score in session.skillScores}
    skills = sorted(set(existing) | set(impacts))
    session.skillScores = [
        SkillScoreDTO(
            skill=skill,
            score=impacts[skill].score if skill in impacts and impacts[skill].score is not None else existing[skill].score,
            delta=(existing[skill].delta if skill in existing else 0) + (impacts[skill].delta if skill in impacts else 0),
        )
        for skill in skills
    ]
    session.updatedAt = result.generatedAt
    return session
