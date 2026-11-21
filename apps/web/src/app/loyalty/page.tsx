'use client';
import React, { useEffect, useState } from 'react';
import { get, post, LoyaltyBalance, LoyaltySettings, paise } from '@/lib/api/business';
import { buttonClass, Field, inputClass, Notice, Panel, useAction } from '@/components/common/BusinessUI';
import { CustomerPicker } from '@/components/common/CustomerPicker';
export default function Loyalty() {
  const [id, setId] = useState(''); const [balance, setBalance] = useState<LoyaltyBalance | null>(null); const [enabled, setEnabled] = useState(false); const [spend, setSpend] = useState('100'); const [points, setPoints] = useState(1); const [value, setValue] = useState('1'); const [margin, setMargin] = useState('20'); const action = useAction();
  useEffect(() => { setId(new URLSearchParams(window.location.search).get('customer') || ''); void action.run(async () => {
    const row = await get<LoyaltySettings>('/loyalty/settings'); setEnabled(row.enabled ?? false); setSpend(((row.earning_spend_paise ?? 10000) / 100).toFixed(2)); setPoints(row.earning_points ?? 1); setValue(((row.point_value_paise ?? 100) / 100).toFixed(2)); setMargin(((row.minimum_margin_bps ?? 2000) / 100).toFixed(2));
  }); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);
  useEffect(() => { setBalance(null); if (id) void action.run(async () => setBalance(await get<LoyaltyBalance>(`/loyalty/${id}`))); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [id]);
  return <div className="space-y-6"><h1 className="text-3xl font-bold">Loyalty points</h1><Notice text={action.notice} /><Panel title="Merchant policy"><form className="space-y-4" onSubmit={e => { e.preventDefault(); void action.run(async () => {
    await post('/loyalty/settings', { enabled, earning_spend_paise: paise(spend), earning_points: points, point_value_paise: paise(value), minimum_margin_bps: paise(margin) }); action.setNotice('Loyalty policy saved');
  }); }}><label className="flex gap-2"><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />Enable loyalty earning and redemption</label><div className="grid sm:grid-cols-2 gap-4">
    <Field label="Each completed spend (₹)"><input className={inputClass} required value={spend} onChange={e => setSpend(e.target.value)} /></Field><Field label="Points earned per spend unit"><input className={inputClass} type="number" min={1} max={10000} value={points} onChange={e => setPoints(Number(e.target.value))} /></Field><Field label="Redemption value per point (₹)"><input className={inputClass} required value={value} onChange={e => setValue(e.target.value)} /></Field><Field label="Minimum gross margin after redemption (%)"><input className={inputClass} required value={margin} onChange={e => setMargin(e.target.value)} /></Field></div><button className={buttonClass} disabled={action.busy}>Save loyalty policy</button></form>
    <p className="text-sm text-slate-600">Points earn on paid sales with a customer attached. Redemptions require known costs and enough margin. Voids reverse earned and spent points; earlier spending can leave a negative balance that must be earned back.</p></Panel>
    <CustomerPicker value={id} onChange={setId} />{balance && <Panel title="Customer points"><p>Available <strong>{balance.available_points}</strong> · Ledger balance {balance.balance_points}</p><p className="text-sm">Latest 200 point entries are shown.</p>{balance.events.map(row => <p className="border-t py-2" key={row.id}>{row.kind} · {row.points_delta > 0 ? '+' : ''}{row.points_delta} · {new Date(row.created_at).toLocaleString()}</p>)}</Panel>}
  </div>;
}
