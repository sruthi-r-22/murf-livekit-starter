'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Sprout, Bug, Calendar, Mic, Sparkles, AlertTriangle } from 'lucide-react';

interface WelcomeViewProps {
  startButtonText?: string;
  onStartCall: () => void;
}

export const WelcomeView = React.forwardRef<HTMLDivElement, WelcomeViewProps>(
  ({ startButtonText, onStartCall }, ref) => {
    const [lang, setLang] = useState<'HI' | 'EN'>('HI');
    const [selectedPrompt, setSelectedPrompt] = useState<string>('');
    const [micPermissionError, setMicPermissionError] = useState(false);

    useEffect(() => {
      if (navigator.mediaDevices?.getUserMedia) {
        navigator.mediaDevices
          .getUserMedia({ audio: true })
          .then((stream) => {
            stream.getTracks().forEach((track) => track.stop());
            setMicPermissionError(false);
          })
          .catch((err) => {
            if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
              setMicPermissionError(true);
            }
          });
      }
    }, []);

    const handleStart = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((track) => track.stop());
        setMicPermissionError(false);
        onStartCall();
      } catch {
        setMicPermissionError(true);
      }
    };

    return (
      <div 
        ref={ref} 
        className="min-h-screen bg-stone-50/80 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px] flex flex-col justify-between p-6 font-sans border-t-4 border-emerald-600"
      >
        {/* Top Header */}
        <header className="flex justify-between items-center w-full pt-1 px-2">
          <div className="flex items-center gap-3">
            <a
              target="_blank"
              rel="noopener noreferrer"
              href="https://livekit.io"
              className="bg-emerald-700 hover:bg-emerald-800 text-white size-9 rounded-lg flex items-center justify-center font-bold text-sm shadow-sm transition-transform hover:scale-105"
            >
              FM
            </a>

            <div>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight leading-none uppercase">
                Farm Memory
              </h2>
              <p className="text-sm font-bold text-emerald-800 mt-1">
                {lang === 'HI' ? 'आपकी खेती का डिजिटल साथी' : 'Your Digital Agricultural Companion'}
              </p>
            </div>
          </div>

          {/* Cleanly aligned Language Selector */}
          <button
            type="button"
            onClick={() => setLang(lang === 'HI' ? 'EN' : 'HI')}
            className="text-sm font-bold text-slate-800 bg-white hover:bg-slate-100 border border-slate-300 px-4 py-2 rounded-full shadow-sm transition-all cursor-pointer mr-2"
          >
            {lang === 'HI' ? (
              <span><strong className="text-emerald-700 text-base">हिन्दी</strong> | English</span>
            ) : (
              <span>हिन्दी | <strong className="text-emerald-700 text-base">English</strong></span>
            )}
          </button>
        </header>

        {/* Hero Card */}
        <main className="max-w-lg mx-auto w-full my-auto">
          <div className="bg-white/95 backdrop-blur-sm border border-slate-200/80 rounded-2xl p-8 shadow-md text-center relative">
            <div className="w-14 h-14 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-7 h-7" />
            </div>

            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Farm Memory Voice Agent
            </h1>
            
            <p className="text-slate-700 font-bold text-base sm:text-lg mt-3 leading-relaxed">
              {lang === 'HI'
                ? 'फसल, कीट नियंत्रण और खेती से जुड़े सवालों में आपका डिजिटल साथी।'
                : 'Real-time voice consultation for crops, pest management, and farming schedules.'}
            </p>

            {micPermissionError && (
              <div className="mt-6 p-3 bg-amber-50 border border-amber-200 rounded-xl text-left">
                <div className="flex items-center gap-2 text-amber-800 font-bold text-sm">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                  <span>माइक्रोफोन एक्सेस की आवश्यकता है / Microphone access required</span>
                </div>
              </div>
            )}

            <div className="mt-8 flex flex-col items-center gap-3">
              {/* Main Call Button dynamically switches text based on language */}
              <Button
                size="lg"
                onClick={handleStart}
                className="w-full h-14 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl font-bold text-lg shadow-lg transition-all active:scale-95 flex items-center justify-center gap-2.5 cursor-pointer"
              >
                <Mic className="w-5 h-5" />
                <span>
                  {startButtonText || (lang === 'HI' ? 'बात शुरू करें' : 'Start Talking')}
                </span>
              </Button>

              <div className="flex items-center gap-2 text-sm font-bold text-slate-600 mt-2">
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse"></span>
                <span>{lang === 'HI' ? 'वॉइस असिस्टेंट ऑनलाइन है' : 'Voice System Online'}</span>
              </div>
            </div>

            {selectedPrompt && (
              <div className="mt-6 p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-800 text-left">
                <span className="font-bold text-slate-900">सवाल / Query:</span> "{selectedPrompt}"
              </div>
            )}
          </div>
        </main>

        {/* Bottom Quick Prompts */}
        <footer className="max-w-2xl mx-auto w-full grid grid-cols-1 sm:grid-cols-3 gap-3 text-center pb-2">
          <button
            type="button"
            onClick={() => setSelectedPrompt('मेरी टमाटर की फसल की पत्तियाँ पीली हो रही हैं')}
            className="bg-white hover:bg-emerald-50/50 p-3.5 rounded-xl border border-slate-200 shadow-sm text-sm font-bold text-slate-900 flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Sprout className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{lang === 'HI' ? 'फसल स्वास्थ्य (Crop Health)' : 'Crop Health'}</span>
          </button>

          <button
            type="button"
            onClick={() => setSelectedPrompt('कीट नियंत्रण के लिए कौन सी दवा डालें?')}
            className="bg-white hover:bg-amber-50/50 p-3.5 rounded-xl border border-slate-200 shadow-sm text-sm font-bold text-slate-900 flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Bug className="w-5 h-5 text-amber-600 shrink-0" />
            <span>{lang === 'HI' ? 'कीट नियंत्रण (Pest Control)' : 'Pest Control'}</span>
          </button>

          <button
            type="button"
            onClick={() => setSelectedPrompt('गेहूं की सिंचाई का सही समय क्या है?')}
            className="bg-white hover:bg-blue-50/50 p-3.5 rounded-xl border border-slate-200 shadow-sm text-sm font-bold text-slate-900 flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <Calendar className="w-5 h-5 text-blue-600 shrink-0" />
            <span>{lang === 'HI' ? 'सिंचाई समय (Farm Schedule)' : 'Farm Schedule'}</span>
          </button>
        </footer>
      </div>
    );
  }
);

WelcomeView.displayName = 'WelcomeView';