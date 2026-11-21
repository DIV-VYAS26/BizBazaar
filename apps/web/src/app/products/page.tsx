'use client';
import React, { useEffect, useState } from 'react';
import { get, post, ProductView, ProductCreate, Page_ProductView_, money, paise } from '@/lib/api/business';
import { buttonClass, Field, inputClass, Notice, Panel, useAction } from '@/components/common/BusinessUI';

export default function Products() {
  const [rows, setRows] = useState<ProductView[]>([]); const [offset, setOffset] = useState(0); const [total, setTotal] = useState(0);
  const [editing, setEditing] = useState<ProductView | null>(null);
  const [sku, setSku] = useState(''); const [name, setName] = useState(''); const [price, setPrice] = useState(''); const [cost, setCost] = useState(''); const [stock, setStock] = useState(''); const [active, setActive] = useState(true);
  const action = useAction();
  async function load(start = offset) { const page = await get<Page_ProductView_>(`/products?limit=20&offset=${start}`); setRows(page.items); setTotal(page.total); setOffset(start); }
  useEffect(() => { void action.run(() => load(0)); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);
  function edit(row: ProductView | null) { setEditing(row); setSku(row?.sku || ''); setName(row?.name || ''); setPrice(row ? (row.selling_price_paise / 100).toFixed(2) : ''); setCost(row?.unit_cost_paise != null ? (row.unit_cost_paise / 100).toFixed(2) : ''); setStock(row?.stock_quantity?.toString() || ''); setActive(row?.active ?? true); }
  return <div className="space-y-6"><h1 className="text-3xl font-bold">Products and stock</h1><Notice text={action.notice} />
    <Panel title={editing ? 'Edit product' : 'Add product'}><form className="grid sm:grid-cols-2 gap-4" onSubmit={e => { e.preventDefault(); void action.run(async () => {
      const payload: ProductCreate = { sku, name, selling_price_paise: paise(price), unit_cost_paise: cost === '' ? null : paise(cost), stock_quantity: stock === '' ? null : Number(stock), active };
      await post(editing ? `/products/${editing.id}` : '/products', editing ? { ...payload, version: editing.version } : payload); edit(null); await load(); action.setNotice('Product saved');
    }); }}>
      <Field label="SKU"><input className={inputClass} required maxLength={100} value={sku} onChange={e => setSku(e.target.value)} /></Field>
      <Field label="Product name"><input className={inputClass} required maxLength={120} value={name} onChange={e => setName(e.target.value)} /></Field>
      <Field label="Selling price (₹)"><input className={inputClass} inputMode="decimal" required value={price} onChange={e => setPrice(e.target.value)} /></Field>
      <Field label="Unit cost (₹, blank if unknown)"><input className={inputClass} inputMode="decimal" value={cost} onChange={e => setCost(e.target.value)} /></Field>
      <Field label="Stock units (blank if untracked)"><input className={inputClass} type="number" min={0} max={1000000} step={1} value={stock} onChange={e => setStock(e.target.value)} /></Field>
      <label className="flex items-center gap-2"><input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />Available for sales</label>
      <div className="flex gap-3"><button className={buttonClass} disabled={action.busy}>{editing ? 'Save product' : 'Add product'}</button>{editing && <button type="button" className="underline" onClick={() => edit(null)}>Cancel edit</button>}</div>
    </form><p className="text-sm text-slate-600">Costs remain unknown when left blank. Editing price or cost does not change earlier sales; reviewed offers must be recreated after product edits.</p></Panel>
    <Panel title="Catalog">{rows.map(row => <article className="flex flex-wrap justify-between gap-2 border-t py-3" key={row.id}><div><strong>{row.name}</strong> · {row.sku}<p className="text-sm">Price {money(row.selling_price_paise)} · Cost {money(row.unit_cost_paise)} · Stock {row.stock_quantity ?? 'Untracked'} · {row.active ? 'Available' : 'Inactive'}</p></div><button className="underline" onClick={() => edit(row)}>Edit {row.name}</button></article>)}
      <div className="flex gap-4"><button disabled={offset === 0 || action.busy} onClick={() => void action.run(() => load(Math.max(0, offset - 20)))}>Previous</button><span>{total} products</span><button disabled={offset + 20 >= total || action.busy} onClick={() => void action.run(() => load(offset + 20))}>Next</button></div>
    </Panel></div>;
}
