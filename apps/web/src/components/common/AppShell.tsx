'use client';
import React, { useState } from 'react';
import { usePathname } from 'next/navigation';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { DisclaimerBanner } from './DisclaimerBanner';
export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  if (pathname === '/customer') return <><header className="bg-white border-b p-5 font-bold">BizBazaar · Private customer record</header><main className="p-5 max-w-3xl w-full mx-auto">{children}</main></>;
  return <><DisclaimerBanner /><Navbar onToggleSidebar={() => setOpen(value => !value)} /><div className="flex-1 flex overflow-hidden"><Sidebar isOpen={open} onClose={() => setOpen(false)} /><main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">{children}</main></div></>;
}
