'use client';
import React, { useState } from 'react';
import type { DevEmailView } from '@/lib/api/business';
import { get } from '@/lib/api/business';

export const buttonClass = 'rounded-lg bg-emerald-700 px-4 py-2 text-white disabled:opacity-50';
export const inputClass = 'w-full rounded-lg border border-slate-300 bg-white p-2';
export function Field({ label, children }: { label: string; children: React.ReactElement<{ id?: string }> }) {
  const id = React.useId();
  return <div className="block space-y-1 text-sm font-medium"><label htmlFor={id}>{label}</label>{React.cloneElement(children, { id })}</div>;
}
export function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl border bg-white p-5 space-y-4"><h2 className="text-xl font-semibold">{title}</h2>{children}</section>;
}
export function Notice({ text }: { text: string }) {
  return text ? <p role="status" className="rounded-lg bg-slate-100 p-3 text-sm whitespace-pre-wrap">{text}</p> : null;
}
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  async function run(work: () => Promise<void>) {
    setBusy(true); setNotice('');
    try { await work(); } catch (error) { setNotice(error instanceof Error ? error.message : 'Request failed'); }
    finally { setBusy(false); }
  }
  return { busy, notice, setNotice, run };
}
export function LocalInbox() {
  const [email, setEmail] = useState('');
  const [messages, setMessages] = useState<DevEmailView[]>([]);
  const action = useAction();
  return <Panel title="Local email preview"><p className="text-sm text-slate-600">Development only. Messages stay on this computer; no email has been sent.</p>
    <form className="flex gap-2" onSubmit={event => { event.preventDefault(); void action.run(async () => {
      setMessages(await get<DevEmailView[]>(`/auth/dev-inbox?email=${encodeURIComponent(email)}`));
    }); }}><Field label="Preview email address"><input className={inputClass} type="email" required value={email} onChange={e => setEmail(e.target.value)} /></Field>
      <button className={buttonClass} disabled={action.busy}>Load preview</button></form>
    <Notice text={action.notice} />
    {messages.map(row => { const url = row.body.match(/https?:\/\/[^\s]+/)?.[0];
      const trusted = url && new URL(url).origin === window.location.origin;
      return <article className="border-t pt-3 space-y-2" key={row.id}><h3 className="font-medium">{row.subject} · {row.status}</h3>
        <p className="text-sm whitespace-pre-wrap break-all">{row.body.replace(/https?:\/\/[^\s]+/g, '[private link below]')}</p>
        {trusted && <a className="text-emerald-800 underline" href={url}>Open private link</a>}</article>; })}
  </Panel>;
}
