import json
import threading
import unittest
from unittest.mock import MagicMock, patch

from websockets.sync.server import serve

from app.services.live_avatar_provider import HeyGenLiveAvatarProvider


class LiveAvatarTransportTests(unittest.TestCase):
    def test_events_are_drained_between_turns_so_ping_can_complete(self):
        ping_ok = threading.Event()
        release = threading.Event()

        def handler(ws):
            ws.send(json.dumps({"type": "session.state_updated", "state": "connected"}))
            while json.loads(ws.recv())["type"] != "agent.speak_end":
                pass
            # Exceed the client's bounded receive queue before sending a ping.
            for _ in range(80):
                ws.send(json.dumps({"type": "agent.speak_completed"}))
            if ws.ping().wait(3):
                ping_ok.set()
            release.wait(5)

        provider = HeyGenLiveAvatarProvider(api_key="test")
        with serve(handler, "127.0.0.1", 0) as server:
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            url = f"ws://127.0.0.1:{server.socket.getsockname()[1]}"
            try:
                self.assertTrue(provider.send_audio(url, b"\x00\x00" * 24))
                self.assertTrue(ping_ok.wait(4), "Unread events blocked ping/pong")
                self.assertTrue(provider.send_audio(url, b"\x00\x00" * 24))
            finally:
                release.set()
                with provider._ws_pool_lock:
                    ws = provider._ws_pool.pop(url, None)
                if ws is not None:
                    ws.close()
                server.shutdown()
                server_thread.join(3)

    def test_reader_does_not_evict_replacement_connection(self):
        provider = HeyGenLiveAvatarProvider(api_key="test")
        old = MagicMock()
        old.recv.side_effect = OSError("closed")
        replacement = MagicMock()
        with patch.object(provider, "_ws_pool", {"url": replacement}):
            provider._receive_events("url", old)
            self.assertIs(provider._ws_pool["url"], replacement)
            old.close.assert_called_once()

    def test_send_failure_closes_and_evicts_socket(self):
        provider = HeyGenLiveAvatarProvider(api_key="test")
        ws = MagicMock()
        ws.send.side_effect = OSError("closed")
        with patch.object(provider, "_ws_pool", {"url": ws}):
            self.assertFalse(provider.send_audio("url", b"\x00\x00"))
            self.assertNotIn("url", provider._ws_pool)
            ws.close.assert_called_once()

    def test_stop_closes_only_its_owned_socket(self):
        provider = HeyGenLiveAvatarProvider(api_key="test")
        first, second = MagicMock(), MagicMock()
        with patch.object(provider, "_ws_pool", {"url-a": first, "url-b": second}), patch.object(
            provider, "_session_urls", {"session-a": "url-a", "session-b": "url-b"}
        ), patch("app.services.live_avatar_provider.urllib.request.urlopen") as request:
            request.return_value.__enter__.return_value.status = 200
            self.assertTrue(provider.stop_session("session-a"))
            first.close.assert_called_once()
            second.close.assert_not_called()
            self.assertIs(provider._ws_pool["url-b"], second)
            self.assertEqual(provider._session_urls, {"session-b": "url-b"})

    def test_expiry_cleans_only_owned_socket_without_remote_request(self):
        provider = HeyGenLiveAvatarProvider(api_key="test")
        ws, timer = MagicMock(), MagicMock()
        with patch.object(provider, "_ws_pool", {"url": ws}), patch.object(
            provider, "_session_urls", {"session": "url"}
        ), patch.object(provider, "_session_timers", {"session": timer}):
            provider._close_session_socket("session")
            self.assertEqual(provider._ws_pool, {})
            self.assertEqual(provider._session_urls, {})
            self.assertEqual(provider._session_timers, {})
            timer.cancel.assert_called_once()
            ws.close.assert_called_once()

    def test_concurrent_utterances_do_not_interleave(self):
        provider = HeyGenLiveAvatarProvider(api_key="test")
        ws = MagicMock()
        messages = []
        ws.send.side_effect = lambda payload: messages.append(json.loads(payload))
        gate = threading.Barrier(3)
        results = []

        def send():
            gate.wait()
            results.append(provider.send_audio("url", b"\x00" * 9600))

        with patch.object(provider, "_ws_pool", {"url": ws}):
            workers = [threading.Thread(target=send) for _ in range(2)]
            for worker in workers:
                worker.start()
            gate.wait()
            for worker in workers:
                worker.join(3)
                self.assertFalse(worker.is_alive())
        self.assertEqual(results, [True, True])
        self.assertEqual([message["type"] for message in messages], [
            "agent.speak", "agent.speak", "agent.speak_end",
            "agent.speak", "agent.speak", "agent.speak_end",
        ])

    def test_created_session_ownership_survives_provider_instances(self):
        provider = HeyGenLiveAvatarProvider(api_key="test")
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.side_effect = [
            json.dumps({"data": {"session_token": "ephemeral", "session_id": "owned"}}).encode(),
            json.dumps({"data": {"livekit_url": "wss://local", "livekit_client_token": "ephemeral", "ws_url": "owned-url"}}).encode(),
        ]
        with patch("app.services.live_avatar_provider.urllib.request.urlopen", return_value=response), patch(
            "app.services.live_avatar_provider.threading.Timer"
        ) as timer:
            provider.create_session_token("state")
            ws = MagicMock()
            provider._ws_pool["owned-url"] = ws
            another = HeyGenLiveAvatarProvider(api_key="test")
            self.assertTrue(another.stop_session("owned"))
            ws.close.assert_called_once()
            timer.return_value.cancel.assert_called_once()
            self.assertNotIn("owned", provider._session_urls)

    def test_provider_failure_does_not_expose_exception_payload(self):
        from app.services.live_avatar_provider import LiveAvatarProviderError
        provider = HeyGenLiveAvatarProvider(api_key="test")
        with patch("app.services.live_avatar_provider.urllib.request.urlopen", side_effect=TimeoutError("secret-token private-payload")):
            with self.assertRaises(LiveAvatarProviderError) as failure:
                provider.create_session_token("state")
        self.assertNotIn("secret-token", str(failure.exception))
        self.assertNotIn("private-payload", str(failure.exception))
