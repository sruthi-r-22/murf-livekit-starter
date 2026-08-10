'use client';

import { useVoiceAssistant, useRoomContext } from '@livekit/components-react';
import { Button } from '@/components/ui/button';
import { PhoneOff, Mic, Volume2, RotateCcw } from 'lucide-react';

interface ActiveSessionViewProps {
  onDisconnect: () => void;
}

export const ActiveSessionView = ({ onDisconnect }: ActiveSessionViewProps) => {
  const { state, audioTrack } = useVoiceAssistant();
  const room = useRoomContext();

  const handleEndCall = () => {
    room.disconnect();
    onDisconnect();
  };

  return (
    <div className="min-h-screen bg-stone-50/80 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px] flex flex-col justify-between p-6 font-sans">
      {/* Header */}
      <header className="flex justify-center items-center pt-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🌱</span>
          <h2 className="text-base font-bold text-slate-900 tracking-wider uppercase">
            Farm Memory
          </h2>
        </div>
      </header>

      {/* Main Active Screen */}
      <main className="max-w-md mx-auto w-full my-auto">
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm text-center flex flex-col items-center">
          
          {/* CONNECTING STATE */}
          {(state === 'connecting' || state === 'initializing') && (
            <>
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-50 border border-amber-200 rounded-full text-amber-800 text-xs font-bold tracking-wider uppercase mb-6">
                <span className="w-2 h-2 bg-amber-500 rounded-full animate-ping"></span>
                Connecting
              </div>
              <div className="w-20 h-20 bg-amber-50 rounded-full flex items-center justify-center text-amber-600 text-2xl font-bold mb-4 animate-pulse">
                • • •
              </div>
              <p className="text-slate-600 text-sm font-semibold">Connecting to Farm Memory...</p>
            </>
          )}

          {/* LISTENING STATE */}
          {state === 'listening' && (
            <>
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 border border-emerald-200 rounded-full text-emerald-800 text-xs font-bold tracking-wider uppercase mb-6">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                Listening
              </div>
              <div className="w-20 h-20 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mb-4 shadow-inner">
                <Mic className="w-8 h-8 animate-bounce" />
              </div>
              <p className="text-slate-800 text-base font-semibold">I'm listening to you...</p>
            </>
          )}

          {/* SPEAKING STATE */}
          {state === 'speaking' && (
            <>
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 border border-blue-200 rounded-full text-blue-800 text-xs font-bold tracking-wider uppercase mb-6">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                Speaking
              </div>
              <div className="w-20 h-20 bg-blue-50 border border-blue-100 text-blue-700 rounded-full flex items-center justify-center mb-4">
                <Volume2 className="w-8 h-8 animate-pulse" />
              </div>
              <p className="text-slate-800 text-base font-semibold">Farm Memory is speaking...</p>
            </>
          )}

          {/* DISCONNECTED / ENDED STATE */}
          {state === 'disconnected' && (
            <>
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 border border-slate-200 rounded-full text-slate-700 text-xs font-bold tracking-wider uppercase mb-6">
                <span className="w-2 h-2 bg-slate-400 rounded-full"></span>
                Call Ended
              </div>
              <p className="text-slate-600 text-sm font-semibold mb-6">Conversation ended</p>
              <Button
                onClick={handleEndCall}
                className="bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl px-6 py-2.5 text-sm font-semibold flex items-center gap-2"
              >
                <RotateCcw className="w-4 h-4" />
                Start Again
              </Button>
            </>
          )}

          {/* END CALL BUTTON */}
          {state !== 'disconnected' && (
            <div className="mt-8 w-full">
              <Button
                variant="destructive"
                onClick={handleEndCall}
                className="w-full h-11 bg-red-600 hover:bg-red-700 text-white rounded-xl font-semibold text-sm flex items-center justify-center gap-2 cursor-pointer shadow-sm"
              >
                <PhoneOff className="w-4 h-4" />
                <span>End Call</span>
              </Button>
            </div>
          )}
        </div>
      </main>

      <footer className="text-center text-xs text-slate-400 font-mono pb-2">
        Farm Memory Voice Intelligence System
      </footer>
    </div>
  );
};