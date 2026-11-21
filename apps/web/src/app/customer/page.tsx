'use client';
import React, { useEffect, useState } from 'react';
import { liveBizBazaarApi } from '@/lib/api/live';
import { post, CreditLedgerView, MessageView, money } from '@/lib/api/business';
import { buttonClass, Notice, Panel, useAction } from '@/components/common/BusinessUI';

export default function CustomerPortal() {
  const [flow, setFlow] = useState(''); const [token, setToken] = useState('');
  const [ledger, setLedger] = useState<CreditLedgerView | null>(null);
  const action = useAction();
  useEffect(() => {
    const readLink = () => {
      const params = new URLSearchParams(window.location.hash.slice(1));
      const raw = params.get('token') || ''; const mode = params.get('flow') || '';
      if (!raw) return;
      setToken(raw); setFlow(mode); window.history.replaceState(null, '', window.location.pathname);
      if (mode === 'portal') void action.run(async () => setLedger(await liveBizBazaarApi.request<CreditLedgerView>('/portal', { headers: { Authorization: `Bearer ${raw}` } })));
    };
    readLink(); window.addEventListener('hashchange', readLink);
    return () => window.removeEventListener('hashchange', readLink);
    // A private link is read once into memory and cleared from browser history.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return <div className="max-w-3xl space-y-5"><h1 className="text-3xl font-bold">Your customer record</h1>
    <Notice text={action.notice} />
    {!token && <p>Open the private link provided by your merchant. After a refresh, reopen that link.</p>}
    {token && ['consent', 'unsubscribe'].includes(flow) && <Panel title="Marketing preference">
      <p>{flow === 'consent' ? 'Allow this merchant to send marketing messages to your email? You can unsubscribe later.' : 'Stop marketing messages from this merchant?'}</p>
      <button className={buttonClass} disabled={action.busy} onClick={() => void action.run(async () => {
        const result = await post<MessageView>('/public/consent', { token, decision: flow === 'consent' ? 'OPT_IN' : 'OPT_OUT' });
        action.setNotice(result.message); setToken('');
      })}>{flow === 'consent' ? 'Confirm marketing opt-in' : 'Unsubscribe'}</button>
    </Panel>}
    {ledger && <Panel title={ledger.customer.name}><p>Outstanding: <strong>{money(ledger.balance_paise)}</strong> · Overdue: {money(ledger.overdue_paise)}</p>
      <p className="text-sm">This is your merchant’s record. Acknowledgement confirms you reviewed a charge; it does not make a payment.</p>
      {ledger.events.map(row => <article key={row.id} className="border-t py-3 space-y-2"><p>{row.kind} · {money(row.delta_paise)} · {row.acknowledgement}</p><p>{row.note}</p>
        {row.kind === 'CHARGE' && row.acknowledgement === 'PENDING' && <div className="flex gap-2">{(['ACKNOWLEDGED', 'DISPUTED'] as const).map(decision => <button key={decision} className={buttonClass} disabled={action.busy} onClick={() => void action.run(async () => {
          setLedger(await post<CreditLedgerView>('/portal/acknowledge', { event_id: row.id, decision }, { Authorization: `Bearer ${token}` }));
        })}>{decision === 'ACKNOWLEDGED' ? 'Acknowledge charge' : 'Dispute charge'}</button>)}</div>}
      </article>)}
    </Panel>}
  </div>;
}
