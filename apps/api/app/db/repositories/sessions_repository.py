from app.schemas.dtos import TrainingSessionDTO
from app.services import mock_store, session_engine


class SessionsRepository:
    """Session persistence boundary backed by mock_store for Phase 2G."""

    def get_session(self, session_id: str):
        return mock_store.sessions.get(session_id)

    def create_session(self, session_id: str = "demo-session-1") -> TrainingSessionDTO:
        mock_store.sessions[session_id] = mock_store.clone_session(session_id)
        return mock_store.sessions[session_id]

    def update_current_state(self, session_id: str, action: str):
        session = self.get_session(session_id)
        if not session:
            return None
        if action == "next":
            state = session_engine.get_next_state(session, mock_store.training_states)
            if state:
                session.currentStateId = state.id
        elif action == "previous":
            state = session_engine.get_previous_state(session, mock_store.training_states)
            if state:
                session.currentStateId = state.id
        else:
            session = session_engine.complete_current_state(session, mock_store.training_states)
        mock_store.sessions[session_id] = session
        return session

    def save_answer(self, session_id: str, state_id: str, answer_text: str):
        session = self.get_session(session_id)
        if not session:
            return None
        session = session_engine.submit_answer(session, state_id, answer_text)
        mock_store.sessions[session_id] = session
        return session

    def save_feedback(self, session_id: str, feedback):
        session = self.get_session(session_id)
        if not session:
            return None
        session.feedback = [item for item in session.feedback if item.stateId != feedback.stateId] + [feedback]
        mock_store.sessions[session_id] = session
        return session

    def complete_state(self, session_id: str):
        return self.update_current_state(session_id, "complete")

    def complete_session(self, session_id: str):
        session = self.get_session(session_id)
        if not session:
            return None
        session.completedStateIds = [state.id for state in mock_store.training_states]
        session.status = "completed"
        mock_store.sessions[session_id] = session
        return session
