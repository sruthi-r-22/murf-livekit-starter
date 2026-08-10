'use client';

import { useState, useCallback } from 'react';
import {
  LiveKitRoom,
  RoomAudioRenderer,
} from '@livekit/components-react';

import { WelcomeView } from '@/components/app/welcome-view';
import { ActiveSessionView } from '@/components/app/active-session-view';

export function App() {
  const [token, setToken] = useState<string | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleStartCall = useCallback(async () => {
    setIsConnecting(true);

    try {
      const res = await fetch('/api/token', {
        method: 'POST',
      });

      if (!res.ok) {
        const errorText = await res.text();

        throw new Error(
          `API error (${res.status}): ${errorText || res.statusText}`
        );
      }

      const data = await res.json();

      setToken(data.accessToken);
      setUrl(data.url);
    } catch (error) {
      console.error('Failed to fetch connection token:', error);
    } finally {
      setIsConnecting(false);
    }
  }, []);

  const handleDisconnect = useCallback(() => {
    setToken(null);
    setUrl(null);
  }, []);

  return (
    <main className="min-h-screen bg-emerald-950/5 relative overflow-hidden">
      {!token ? (
        <WelcomeView
          startButtonText={
            isConnecting ? 'Connecting...' : 'Start Talking'
          }
          onStartCall={handleStartCall}
        />
      ) : (
        <LiveKitRoom
          serverUrl={url || undefined}
          token={token}
          connect={true}
          audio={true}
          video={false}
          onDisconnected={handleDisconnect}
          data-lk-theme="default"
        >
          {/* This plays the Farm Memory agent's voice */}
          <RoomAudioRenderer />

          <ActiveSessionView
            onDisconnect={handleDisconnect}
          />
        </LiveKitRoom>
      )}
    </main>
  );
}