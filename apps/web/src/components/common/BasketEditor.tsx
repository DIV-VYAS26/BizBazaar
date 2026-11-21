'use client';
import React, { useEffect, useState } from 'react';
import { get, BasketLine, ProductView, Page_ProductView_, money } from '@/lib/api/business';
import { inputClass } from './BusinessUI';
export function BasketEditor({ lines, onChange }: { lines: BasketLine[]; onChange: (lines: BasketLine[]) => void }) {
  const [products, setProducts] = useState<ProductView[]>([]); const [offset, setOffset] = useState(0); const [total, setTotal] = useState(0); const [error, setError] = useState('');
  useEffect(() => { void get<Page_ProductView_>(`/products?limit=100&offset=${offset}`).then(page => { setProducts(previous => offset ? [...previous, ...page.items] : page.items); setTotal(page.total); }).catch(error => setError(error.message)); }, [offset]);
  const update = (index: number, change: Partial<BasketLine>) => onChange(lines.map((line, at) => at === index ? { ...line, ...change } : line));
  return <fieldset className="space-y-3"><legend className="font-medium">Sale basket</legend>{lines.map((line, index) => <div className="flex gap-2" key={index}>
    <select aria-label={`Product ${index + 1}`} required className={inputClass} value={line.product_id} onChange={e => update(index, { product_id: e.target.value })}><option value="">Select product</option>{products.filter(row => row.active).map(row => <option key={row.id} value={row.id}>{row.name} · {money(row.selling_price_paise)} · Stock {row.stock_quantity ?? 'Untracked'}</option>)}</select>
    <input aria-label={`Quantity ${index + 1}`} className="w-24 border rounded-lg p-2" type="number" min={1} max={10000} required value={line.quantity} onChange={e => update(index, { quantity: Number(e.target.value) })} />
    <button type="button" aria-label={`Remove product ${index + 1}`} disabled={lines.length === 1} onClick={() => onChange(lines.filter((_, at) => at !== index))}>Remove</button></div>)}
    <button type="button" className="underline text-sm" disabled={lines.length >= 100} onClick={() => onChange([...lines, { product_id: '', quantity: 1 }])}>Add basket line</button>
    {products.length < total && <button type="button" className="underline text-sm ml-4" onClick={() => setOffset(offset + 100)}>Load more products</button>}{error && <p role="alert">{error}</p>}
  </fieldset>;
}
