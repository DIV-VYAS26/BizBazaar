import { liveBizBazaarApi } from './live';
export type * from '../generated/backend';

export const get = <T,>(path: string) => liveBizBazaarApi.request<T>(path);
export const post = <T,>(path: string, body?: unknown, headers?: Record<string, string>) =>
  liveBizBazaarApi.request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers },
    body: body === undefined ? undefined : JSON.stringify(body) });

export function paise(value: string): number {
  if (!/^\d+(\.\d{1,2})?$/.test(value)) throw new Error('Enter a positive rupee amount with at most two decimal places');
  const [whole, fraction = ''] = value.split('.');
  const result = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  if (!Number.isSafeInteger(result) || result > 1_000_000_000_000) throw new Error('Amount is too large');
  return result;
}
export const money = (value: number | null | undefined) => value == null ? 'Unknown' : new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', minimumFractionDigits: 2,
}).format(value / 100);
export const requestKey = () => crypto.randomUUID();
