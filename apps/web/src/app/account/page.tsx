'use client';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { get, post, AuthOptions, MessageView } from '@/lib/api/business';
import { setApiMode } from '@/lib/api/client';
import { buttonClass, Field, inputClass, LocalInbox, Notice, Panel, useAction } from '@/components/common/BusinessUI';

export default function AccountPage() {
  const [flow, setFlow] = useState('login');
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [options, setOptions] = useState<AuthOptions | null>(null);
  const action = useAction();
  useEffect(() => {
    const readLink = () => {
      const params = new URLSearchParams(window.location.hash.slice(1));
      if (params.has('token')) { setToken(params.get('token') || ''); setFlow(params.get('flow') || 'verify');
        window.history.replaceState(null, '', window.location.pathname); }
    };
    readLink(); window.addEventListener('hashchange', readLink);
    void get<AuthOptions>('/auth/options').then(setOptions).catch(() => {});
    return () => window.removeEventListener('hashchange', readLink);
  }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    await action.run(async () => {
      if (flow === 'login') { await post('/auth/login', { email, password }); setPassword(''); setApiMode('live'); window.location.assign('/dashboard'); return; }
      const path = { register: '/auth/register', forgot: '/auth/forgot-password', resend: '/auth/resend-verification', verify: '/auth/verify', reset: '/auth/reset-password' }[flow];
      if (!path) return;
      const payload = flow === 'register' ? { email, password, merchant_name: name } : flow === 'verify' ? { token } : flow === 'reset' ? { token, password } : { email };
      const result = await post<MessageView>(path, payload);
      action.setNotice(result.message); setPassword('');
      if (flow === 'verify' || flow === 'reset') { setToken(''); setFlow('login'); }
    });
  }
  return <div className="max-w-2xl space-y-6"><h1 className="text-3xl font-bold">Merchant account</h1>
    <Panel title={flow === 'login' ? 'Sign in' : flow === 'register' ? 'Create your shop account' : flow === 'verify' ? 'Verify email' : flow === 'reset' ? 'Set a new password' : 'Account recovery'}>
      <div className="flex flex-wrap gap-3 text-sm">{['login', ...(options?.registration_enabled ? ['register'] : []), 'forgot', 'resend'].map(mode => <button key={mode} className="underline" onClick={() => { setFlow(mode); action.setNotice(''); }}>{({ login: 'Sign in', register: 'Register', forgot: 'Forgot password', resend: 'Resend verification' } as Record<string, string>)[mode]}</button>)}</div>
      <form onSubmit={submit} className="space-y-4">
        {flow === 'register' && <Field label="Shop name"><input className={inputClass} required maxLength={120} value={name} onChange={e => setName(e.target.value)} /></Field>}
        {!['verify', 'reset'].includes(flow) && <Field label="Email"><input className={inputClass} type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} /></Field>}
        {['login', 'register', 'reset'].includes(flow) && <Field label="Password"><input className={inputClass} type="password" autoComplete={flow === 'login' ? 'current-password' : 'new-password'} required minLength={flow === 'login' ? 1 : 12} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} /></Field>}
        {flow === 'verify' && <p>Confirm this single-use email verification link.</p>}
        <button className={buttonClass} disabled={action.busy || (['verify', 'reset'].includes(flow) && !token)}>{flow === 'login' ? 'Sign in' : flow === 'register' ? 'Create account' : flow === 'verify' ? 'Verify email' : flow === 'reset' ? 'Save new password' : 'Send instructions'}</button>
      </form><Notice text={action.notice} />
      {options?.demo_enabled && <Link className="block underline text-sm" href="/connect">Use a local demo credential</Link>}
    </Panel>
    {options?.local_inbox_enabled && <LocalInbox />}
  </div>;
}
