import pytest
import asyncio

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.live_avatar_service import ActiveAvatarSessionStore, stop_avatar_session
from app.schemas.dtos import TrainingSessionDTO, TrainingStateDTO
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_avatar_lifecycle():
    store = ActiveAvatarSessionStore()
    session_id = 'test_session_1'
    state_id = 'state_1'
    avatar_id = 'avatar_1'
    key = store._key(session_id, state_id)
    
    store.register_start(session_id, state_id, avatar_id)
    assert store._sessions[key]['openCount'] == 1
    
    store.register_start(session_id, state_id, avatar_id)
    assert store._sessions[key]['openCount'] == 2
    
    store.register_stop(session_id, state_id)
    assert store._sessions[key]['openCount'] == 1
    
    store.register_stop(session_id, state_id)
    assert key not in store._sessions

def test_stop_avatar_session_does_not_stop_provider_early():
    store = ActiveAvatarSessionStore()
    session = MagicMock()
    session.id = "sess-1"
    state = MagicMock()
    state.id = "state-1"
    state.avatarEnabled = True
    
    store.register_start(session.id, state.id, "avatar-1")
    store.register_start(session.id, state.id, "avatar-1")
    
    mock_provider = MagicMock()
    mock_provider.provider_name = "mock"
    mock_provider.avatar_id = "mock"
    
    stop_avatar_session(session, state, "avatar-1", provider=mock_provider, store=store)
    mock_provider.stop_session.assert_not_called()
    
    stop_avatar_session(session, state, "avatar-1", provider=mock_provider, store=store)
    mock_provider.stop_session.assert_called_once_with("avatar-1")
