'use client';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { get, post, AuthOptions, CustomerView, Page_CustomerView_ } from '@/lib/api/business';
import { buttonClass, Field, inputClass, LocalInbox, Notice, Panel, useAction } from '@/components/common/BusinessUI';

export default function Customers() {
  const [rows, setRows] = useState<CustomerView[]>([]); const [offset, setOffset] = useState(0); const [total, setTotal] = useState(0);
  const [name, setName] = useState(''); const [email, setEmail] = useState(''); const [consent, setConsent] = useState(false); const [editing, setEditing] = useState<CustomerView | null>(null); const [preview, setPreview] = useState(false);
  const action = useAction();
  async function load(start = offset) { const page = await get<Page_CustomerView_>(`/customers?limit=20&offset=${start}`); setRows(page.items); setTotal(page.total); setOffset(start); }
  useEffect(() => { void action.run(async () => { await load(0); setPreview((await get<AuthOptions>('/auth/options')).local_inbox_enabled); }); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);
  return <div className="space-y-6"><h1 className="text-3xl font-bold">Customers</h1><Notice text={action.notice} />
    <Panel title={editing ? 'Edit customer' : 'Add customer'}><form className="space-y-4" onSubmit={e => { e.preventDefault(); void action.run(async () => {
      await post(editing ? `/customers/${editing.id}` : '/customers', { name, email: email || null, request_marketing_consent: consent }); setEditing(null); setName(''); setEmail(''); setConsent(false); await load(); action.setNotice('Customer saved. Any requested consent invitation is queued.');
    }); }}><Field label="Customer name"><input className={inputClass} required maxLength={120} value={name} onChange={e => setName(e.target.value)} /></Field>
      <Field label="Customer email (optional)"><input className={inputClass} type="email" value={email} onChange={e => setEmail(e.target.value)} /></Field>
      <label className="flex gap-2"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />Invite customer to confirm marketing consent</label>
      <p className="text-sm text-slate-600">The customer must confirm their own consent. Changing an email revokes prior consent and private links.</p>
      <button className={buttonClass} disabled={action.busy}>{editing ? 'Save customer' : 'Add customer'}</button>
    </form></Panel>
    <Panel title="Customer list">{rows.map(row => <article key={row.id} className="border-t py-3 space-y-2"><h3 className="font-medium">{row.name}</h3><p>{row.email || 'No email'} · Marketing {row.marketing_opt_in ? 'Opted in' : 'Not opted in'}</p>
      <div className="flex flex-wrap gap-4 text-sm"><Link className="underline" href={`/ledger?customer=${row.id}`}>Open credit ledger</Link><Link className="underline" href={`/loyalty?customer=${row.id}`}>View points</Link>
        <button className="underline" onClick={() => { setEditing(row); setName(row.name); setEmail(row.email || ''); setConsent(false); }}>Edit customer</button>
        {row.email && <>{['portal-link', 'consent-link', 'marketing-revoke'].map(operation => <button key={operation} disabled={action.busy} className="underline" onClick={() => void action.run(async () => { await post(`/customers/${row.id}/${operation}`); await load(); action.setNotice(operation === 'marketing-revoke' ? 'Marketing consent revoked' : 'Private link queued'); })}>{({ 'portal-link': 'Queue credit portal link', 'consent-link': 'Queue consent invitation', 'marketing-revoke': 'Revoke marketing' } as Record<string, string>)[operation]}</button>)}</>}
      </div></article>)}<div className="flex gap-4"><button disabled={!offset || action.busy} onClick={() => void action.run(() => load(offset - 20))}>Previous</button><span>{total} customers</span><button disabled={offset + 20 >= total || action.busy} onClick={() => void action.run(() => load(offset + 20))}>Next</button></div></Panel>
    {preview && <LocalInbox />}
  </div>;
}
