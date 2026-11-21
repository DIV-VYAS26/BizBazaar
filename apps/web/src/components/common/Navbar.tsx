'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { liveBizBazaarApi } from '@/lib/api/live';
import { getApiMode, setApiMode, subscribeApiMode, bizbazaarApi } from '@/lib/api/client';
import { Button } from '@/components/ui/Button';
import { Store, RefreshCw, Radio, Clock, Menu } from 'lucide-react';
import { MerchantSession } from '@/lib/generated/types';

interface NavbarProps {
  onToggleSidebar?: () => void;
}

export function Navbar({ onToggleSidebar }: NavbarProps) {
  const [mode, setMode] = useState<'mock' | 'live'>('mock');
  const [session, setSession] = useState<MerchantSession | null>(null);
  const [isResetting, setIsResetting] = useState(false);

  useEffect(() => {
    setMode(getApiMode());
    return subscribeApiMode((newMode) => setMode(newMode));
  }, []);

  useEffect(() => {
    setSession(null);
    bizbazaarApi.getSession().then(setSession).catch(() => {});
  }, [mode]);

  const handleToggleMode = () => {
    const nextMode = mode === 'mock' ? 'live' : 'mock';
    setApiMode(nextMode);
    window.location.reload();
  };

  const handleResetData = async () => {
    setIsResetting(true);
    bizbazaarApi.resetState?.();
    setTimeout(() => {
      setIsResetting(false);
      window.location.reload();
    }, 400);
  };

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200">
      <div className="flex items-center justify-between px-4 sm:px-6 h-16">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            className="md:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors"
            aria-label="Toggle navigation"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-sm font-bold text-lg">
              B
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 tracking-tight">BizBazaar</span>
                <span className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">v1.0</span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block">Merchant AI Growth Copilot</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          {mode === 'live' && !session && <Link href="/account" className="text-sm underline">Sign in</Link>}
          {mode === 'live' && session && <button className="text-sm underline" onClick={async () => {
            await liveBizBazaarApi.logout();
            window.location.assign(session.demo_mode ? '/connect' : '/account');
          }}>Sign out</button>}
          {session && (
            <div className="hidden lg:flex items-center gap-2.5 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5">
              <Store className="w-4 h-4 text-emerald-600" />
              <div className="text-xs">
                <span className="font-semibold text-slate-800">{session.merchant_name}</span>
                <span className="text-slate-400 ml-1.5 font-mono">({session.merchant_id})</span>
              </div>
              <div className="w-px h-3.5 bg-slate-200 mx-1" />
              <div className="flex items-center gap-1 text-[11px] text-slate-500">
                <Clock className="w-3 h-3 text-slate-400" />
                <span>{session.timezone}</span>
              </div>
            </div>
          )}

          {/* API Mode Selector */}
          {process.env.NEXT_PUBLIC_DEMO_MODE !== 'false' && <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-medium">
            <button
              onClick={() => {
                if (mode !== 'mock') handleToggleMode();
              }}
              className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                mode === 'mock'
                  ? 'bg-white text-emerald-700 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Radio className={`w-3 h-3 ${mode === 'mock' ? 'text-emerald-500' : 'text-slate-400'}`} />
              Mock
            </button>
            <button
              onClick={() => {
                if (mode !== 'live') handleToggleMode();
              }}
              className={`px-2.5 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                mode === 'live'
                  ? 'bg-white text-blue-700 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Radio className={`w-3 h-3 ${mode === 'live' ? 'text-blue-500' : 'text-slate-400'}`} />
              Live API
            </button>
          </div>}

          {/* Reset Canonical Fixture */}
          {mode === 'mock' && <Button
            variant="outline"
            size="sm"
            onClick={handleResetData}
            isLoading={isResetting}
            title="Reset to canonical verification fixture"
            className="hidden sm:inline-flex text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
            <span>Reset Demo</span>
          </Button>}
        </div>
      </div>
    </header>
  );
}
