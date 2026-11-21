'use client';
import React, { useEffect, useRef, useState } from 'react';
import { get, post, CreditLedgerView, MessageView, money, paise, requestKey } from '@/lib/api/business';
import { buttonClass, Field, inputClass, Notice, Panel, useAction } from '@/components/common/BusinessUI';
import { CustomerPicker } from '@/components/common/CustomerPicker';
export default function Ledger() {
  const [id, setId] = useState(''); const [ledger, setLedger] = useState<CreditLedgerView | null>(null); const [kind, setKind] = useState('charges'); const [amount, setAmount] = useState(''); const [due, setDue] = useState(''); const [note, setNote] = useState(''); const key = useRef(''); const action = useAction();
  useEffect(() => { setId(new URLSearchParams(window.location.search).get('customer') || ''); }, []);
  useEffect(() => { setLedger(null); key.current = ''; if (id) void action.run(async () => setLedger(await get<CreditLedgerView>(`/credit/${id}`))); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [id]);
  return <div className="space-y-6"><h1 className="text-3xl font-bold">Credit ledger</h1><Notice text={action.notice} /><CustomerPicker value={id} onChange={setId} />
    {id && <Panel title="Record credit movement"><form className="grid sm:grid-cols-2 gap-4" onChange={() => { key.current = ''; }} onSubmit={e => { e.preventDefault(); if (!key.current) key.current = requestKey(); void action.run(async () => {
      await post(`/credit/${id}/${kind}`, { request_key: key.current, amount_paise: paise(amount), due_date: kind === 'charges' ? due : null, note }); key.current = ''; setLedger(await get<CreditLedgerView>(`/credit/${id}`)); setAmount(''); action.setNotice('Credit movement recorded');
    }); }}><Field label="Movement"><select className={inputClass} value={kind} onChange={e => setKind(e.target.value)}><option value="charges">New credit charge</option><option value="repayments">Repayment received</option></select></Field><Field label="Amount (₹)"><input className={inputClass} required inputMode="decimal" value={amount} onChange={e => setAmount(e.target.value)} /></Field>
      {kind === 'charges' && <Field label="Due date"><input className={inputClass} type="date" required value={due} onChange={e => setDue(e.target.value)} /></Field>}<Field label="Note"><input className={inputClass} maxLength={300} value={note} onChange={e => setNote(e.target.value)} /></Field><button className={buttonClass} disabled={action.busy}>Record movement</button></form>
      <p className="text-sm text-slate-600">Charges record debt. Only repayments add to recorded collections. Corrections append reversals.</p></Panel>}
    {ledger && <Panel title={ledger.customer.name}><p>Outstanding <strong>{money(ledger.balance_paise)}</strong> · Overdue {money(ledger.overdue_paise)}</p>{ledger.events.slice().reverse().map(row => <article className="border-t py-3 space-y-2" key={row.id}><p>{row.kind} · {money(row.delta_paise)} · {row.acknowledgement}</p><p className="text-sm">{row.due_date && `Due ${row.due_date} · `}{row.note}</p>{row.kind !== 'REVERSAL' && !ledger.events.some(event => event.reverses_id === row.id) && <button className="underline text-sm" disabled={action.busy} onClick={() => { const reason = window.prompt('Reason for reversal'); if (reason?.trim()) void action.run(async () => { await post(`/credit/events/${row.id}/reverse`, { request_key: `reverse-${row.id}`, note: reason }); setLedger(await get<CreditLedgerView>(`/credit/${id}`)); }); }}>Reverse entry</button>}</article>)}</Panel>}
    <button className={buttonClass} disabled={action.busy} onClick={() => void action.run(async () => action.setNotice((await post<MessageView>('/credit/reminders/queue')).message))}>Queue due reminders</button>
  </div>;
}
