'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  ReceiptText,
  LineChart,
  Sparkles,
  Zap,
  FileSpreadsheet,
  X,
} from 'lucide-react';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  const navItems = [
    ...[
      ['Products', '/products', 'Prices, costs and stock'],
      ['Customers', '/customers', 'Contacts and consent'],
      ['Sales', '/sales', 'Paid and credit sales'],
      ['Credit ledger', '/ledger', 'Charges and repayments'],
      ['Profit-aware offers', '/offers', 'Compare costs and margins'],
      ['Loyalty', '/loyalty', 'Points and redemption'],
      ['Retention', '/retention', 'Consent-based follow-ups'],
      ['Settings', '/settings', 'Coverage and campaign defaults'],
    ].map(([name, href, description]) => ({ name, href, description, icon: ReceiptText })),
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: LayoutDashboard,
      description: 'Recorded collections & health',
    },
    {
      name: 'Transactions',
      href: '/transactions',
      icon: ReceiptText,
      description: 'CSV import & status audit',
    },
    {
      name: 'Analytics & Forecast',
      href: '/analytics',
      icon: LineChart,
      description: 'Observed trends & projections',
    },
    {
      name: 'Campaigns',
      href: '/campaigns',
      icon: Sparkles,
      description: 'AI drafts & merchant approval',
    },
    {
      name: 'Payment Simulator',
      href: '/campaigns/simulate',
      icon: Zap,
      description: 'Simulate accepted transactions',
    },
    {
      name: 'Reports & Summary',
      href: '/reports',
      icon: FileSpreadsheet,
      description: 'Rewards & voice briefing',
    },
  ].filter(item => process.env.NEXT_PUBLIC_DEMO_MODE !== 'false' || item.href !== '/campaigns/simulate');

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs md:hidden"
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 text-slate-100 flex flex-col transition-transform duration-300 ease-in-out md:translate-x-0 md:static md:z-30 shrink-0 border-r border-slate-800',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex items-center justify-between p-4 border-b border-slate-800 md:hidden">
          <span className="font-semibold text-sm">Navigation</span>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4">
          <div className="px-3 py-2 bg-slate-800/80 rounded-xl border border-slate-700/60 mb-2">
            <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">Active Store</p>
            <p className="text-sm font-medium text-slate-200 mt-0.5 truncate">BizBazaar workspace</p>
            <p className="text-[11px] text-slate-400">Session identity appears in the top bar</p>
          </div>
        </div>

        <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  'flex items-start gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group',
                  isActive
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                )}
              >
                <Icon
                  className={cn(
                    'w-5 h-5 shrink-0 mt-0.5 transition-colors',
                    isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
                  )}
                />
                <div className="flex flex-col">
                  <span>{item.name}</span>
                  <span
                    className={cn(
                      'text-[11px] font-normal leading-tight mt-0.5',
                      isActive ? 'text-emerald-100' : 'text-slate-400'
                    )}
                  >
                    {item.description}
                  </span>
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800">
          <div className="bg-slate-800/40 rounded-lg p-3 text-xs text-slate-400 space-y-1">
            <div className="flex items-center justify-between text-slate-300 font-medium">
              <span>Currency</span>
              <span className="font-mono text-emerald-400">INR (Paise)</span>
            </div>
            <div className="flex items-center justify-between text-slate-300 font-medium">
              <span>Timezone</span>
              <span className="font-mono text-slate-300">Asia/Kolkata</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
