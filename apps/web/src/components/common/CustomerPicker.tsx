'use client';
import React, { useEffect, useState } from 'react';
import { get, CustomerView, Page_CustomerView_ } from '@/lib/api/business';
import { Field, inputClass } from './BusinessUI';
export function CustomerPicker({ value, onChange, optional = false }: { value: string; onChange: (id: string) => void; optional?: boolean }) {
  const [people, setPeople] = useState<CustomerView[]>([]); const [offset, setOffset] = useState(0); const [total, setTotal] = useState(0); const [error, setError] = useState('');
  useEffect(() => { void get<Page_CustomerView_>(`/customers?limit=100&offset=${offset}`).then(page => { setPeople(previous => offset ? [...previous, ...page.items] : page.items); setTotal(page.total); }).catch(error => setError(error.message)); }, [offset]);
  return <div><Field label="Customer"><select className={inputClass} required={!optional} value={value} onChange={e => onChange(e.target.value)}><option value="">{optional ? 'No customer' : 'Select customer'}</option>{people.map(person => <option value={person.id} key={person.id}>{person.name} · {person.email || 'No email'}</option>)}</select></Field>
    {people.length < total && <button type="button" className="underline text-sm" onClick={() => setOffset(offset + 100)}>Load more customers</button>}{error && <p role="alert">{error}</p>}</div>;
}
