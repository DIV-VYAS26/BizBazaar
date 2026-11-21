import React from 'react';
import { headers } from 'next/headers';
import { AppShell } from '@/components/common/AppShell';
import './globals.css';

export const metadata = { title: 'BizBazaar — Merchant workspace', description: 'Sales, credit records, loyalty and growth insights for your own business.' };
export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Dynamic rendering prevents cached HTML from reusing a script nonce.
  await headers();
  return <html lang="en"><body className="min-h-screen flex flex-col bg-slate-50 antialiased selection:bg-emerald-100 selection:text-emerald-900"><AppShell>{children}</AppShell></body></html>;
}
