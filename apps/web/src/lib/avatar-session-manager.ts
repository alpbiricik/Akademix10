import { Room, Track, RoomEvent } from "livekit-client";
import { getAvatarSessionToken, sendAvatarSessionAction } from "@/lib/adapters/sessionAdapter";
import type { LiveAvatarSessionTokenResponse } from "@/lib/contracts/dtos";

export interface AvatarSession {
  room: Room;
  tokenRes: LiveAvatarSessionTokenResponse | null;
  avatarSessionId: string;
  status: "idle" | "connecting" | "streaming" | "error";
  refCount: number;
  disconnectTimeout: NodeJS.Timeout | null;
}

const activeSessions = new Map<string, AvatarSession>();

export async function acquireAvatarSession(
  sessionId: string,
  stateId: string,
  onTrackSubscribed: (track: Track) => void,
  onDisconnected: () => void,
): Promise<AvatarSession> {
  const key = `${sessionId}:${stateId}`;
  const session = activeSessions.get(key);

  if (session) {
    session.refCount++;
    if (session.disconnectTimeout) {
      clearTimeout(session.disconnectTimeout);
      session.disconnectTimeout = null;
    }
    // Reattach event listeners
    session.room.removeAllListeners();
    session.room.on(RoomEvent.TrackSubscribed, onTrackSubscribed);
    session.room.on(RoomEvent.Disconnected, () => {
      session.status = "idle";
      onDisconnected();
    });
    
    // Attach existing tracks
    for (const participant of session.room.remoteParticipants.values()) {
      for (const publication of participant.trackPublications.values()) {
        if (publication.track) {
          onTrackSubscribed(publication.track);
        }
      }
    }
    
    return session;
  }

  // Create new
  const room = new Room({ adaptiveStream: true, dynacast: true });
  room.on(RoomEvent.TrackSubscribed, onTrackSubscribed);
  room.on(RoomEvent.Disconnected, () => {
    const s = activeSessions.get(key);
    if (s) s.status = "idle";
    onDisconnected();
  });

  const newSession: AvatarSession = {
    room,
    tokenRes: null,
    avatarSessionId: "",
    status: "connecting",
    refCount: 1,
    disconnectTimeout: null,
  };
  activeSessions.set(key, newSession);

  try {
    const tokenRes = await getAvatarSessionToken(sessionId, stateId);
    newSession.tokenRes = tokenRes;
    const metadata = (tokenRes.metadata as { livekitUrl?: string; livekitClientToken?: string; avatarSessionId?: string }) || {};
    const livekitUrl = metadata.livekitUrl || "";
    const livekitClientToken = metadata.livekitClientToken || "";
    const avatarSessionId = metadata.avatarSessionId || tokenRes.sessionToken || "";

    if (!livekitUrl || !livekitClientToken) {
      throw new Error("LiveAvatar did not return LiveKit connection details.");
    }

    newSession.avatarSessionId = avatarSessionId;
    await room.connect(livekitUrl, livekitClientToken);
    
    await sendAvatarSessionAction(sessionId, { stateId, avatarSessionId, action: "start" });
    newSession.status = "streaming";
    return newSession;
  } catch (error) {
    activeSessions.delete(key);
    throw error;
  }
}

export function releaseAvatarSession(sessionId: string, stateId: string) {
  const key = `${sessionId}:${stateId}`;
  const session = activeSessions.get(key);
  if (!session) return;

  session.refCount--;
  if (session.refCount <= 0) {
    session.disconnectTimeout = setTimeout(() => {
      activeSessions.delete(key);
      void session.room.disconnect();
      void sendAvatarSessionAction(sessionId, { stateId, avatarSessionId: session.avatarSessionId, action: "stop" });
    }, 1500); // 1.5s grace period for StrictMode
  }
}
