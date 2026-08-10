'use client';

import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { WelcomeView } from '@/components/app/welcome-view';
import { ActiveSessionView } from '@/components/app/active-session-view';

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start, disconnect } = useSessionContext();

  return (
    <div className="w-full min-h-screen bg-slate-50">
      {!isConnected ? (
        <WelcomeView
          startButtonText={appConfig.startButtonText || "START TALKING"}
          onStartCall={start}
        />
      ) : (
        <ActiveSessionView onDisconnect={disconnect} />
      )}
    </div>
  );
}