'use client';
import React, { useEffect, useRef, useState } from 'react';
import { get, post, BasketLine, Page_SaleView_, SaleView, Page_OfferView_, OfferView, money, requestKey } from '@/lib/api/business';
import { buttonClass, Field, inputClass, Notice, Panel, useAction } from '@/components/common/BusinessUI';
import { BasketEditor } from '@/components/common/BasketEditor';
import { CustomerPicker } from '@/components/common/CustomerPicker';
export default function Sales() {
  const [lines, setLines] = useState<BasketLine[]>([{ product_id: '', quantity: 1 }]); const [customer, setCustomer] = useState(''); const [method, setMethod] = useState('CASH'); const [due, setDue] = useState(''); const [offer, setOffer] = useState(''); const [points, setPoints] = useState(0);
  const [rows, setRows] = useState<SaleView[]>([]); const [offers, setOffers] = useState<OfferView[]>([]); const [offset, setOffset] = useState(0); const [total, setTotal] = useState(0); const key = useRef(''); const action = useAction();
  async function load(start = offset) { const page = await get<Page_SaleView_>(`/sales?limit=20&offset=${start}`); setRows(page.items); setTotal(page.total); setOffset(start); }
  useEffect(() => { void action.run(async () => { await load(0); setOffers((await get<Page_OfferView_>('/offers?limit=100')).items.filter(row => row.status === 'ACTIVE')); }); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);
  return <div className="space-y-6"><h1 className="text-3xl font-bold">Record sales</h1><Notice text={action.notice} /><Panel title="New sale"><form className="space-y-4" onChange={() => { key.current = ''; }} onSubmit={e => { e.preventDefault(); if (!key.current) key.current = requestKey(); void action.run(async () => {
    const result = await post<SaleView>('/sales', { request_key: key.current, lines, customer_id: customer || null, payment_method: method, due_date: method === 'CREDIT' ? due : null, offer_id: offer || null, redeem_points: method === 'CREDIT' ? 0 : points }); key.current = ''; await load(); action.setNotice(`Sale recorded: ${money(result.total_paise)}. Gross profit: ${money(result.profit_paise)}.`);
  }); }}><BasketEditor lines={lines} onChange={value => { setLines(value); key.current = ''; }} /><CustomerPicker value={customer} onChange={value => { setCustomer(value); key.current = ''; }} optional />
    <div className="grid sm:grid-cols-2 gap-4"><Field label="Payment method"><select className={inputClass} value={method} onChange={e => setMethod(e.target.value)}><option value="CASH">Cash received</option><option value="OTHER">Other payment received</option><option value="CREDIT">Customer credit (unpaid)</option></select></Field>
      {method === 'CREDIT' && <Field label="Credit due date"><input className={inputClass} type="date" required value={due} onChange={e => setDue(e.target.value)} /></Field>}
      <Field label="Approved offer"><select className={inputClass} value={offer} onChange={e => setOffer(e.target.value)}><option value="">No offer</option>{offers.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></Field>
      {method !== 'CREDIT' && <Field label="Loyalty points to redeem"><input className={inputClass} type="number" min={0} max={1000000} value={points} onChange={e => setPoints(Number(e.target.value))} /></Field>}</div>
    <p className="text-sm text-slate-600">The server calculates the final amount, checks stock and offer limits, and saves the price and cost used for this sale. This records a payment you already received.</p>
    <button className={buttonClass} disabled={action.busy}>Record sale</button></form></Panel>
    <Panel title="Sales history">{rows.map(row => <article key={row.id} className="border-t py-3 space-y-2"><p className="font-medium">{money(row.total_paise)} · {row.payment_method} · {row.status}</p><p className="text-sm">Discount {money(row.discount_paise)} · Cost {money(row.cost_paise)} · Gross profit {money(row.profit_paise)} · {new Date(row.created_at).toLocaleString()}</p>{row.status === 'RECORDED' && <button className="underline text-sm" disabled={action.busy} onClick={() => { const reason = window.prompt('Reason for voiding and restocking this sale'); if (reason?.trim()) void action.run(async () => { await post(`/sales/${row.id}/void`, { request_key: `void-${row.id}`, note: reason }); await load(); }); }}>Void and restock sale</button>}</article>)}
      <div className="flex gap-4"><button disabled={!offset || action.busy} onClick={() => void action.run(() => load(offset - 20))}>Previous</button><span>{total} sales</span><button disabled={offset + 20 >= total || action.busy} onClick={() => void action.run(() => load(offset + 20))}>Next</button></div></Panel>
  </div>;
}
