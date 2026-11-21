import { afterEach, describe, expect, it, vi } from 'vitest';
import { LiveBizBazaarApi } from '../lib/api/live';

afterEach(() => vi.unstubAllGlobals());

describe('Real backend adapter', () => {
  it('sends browser credentials and CSRF proof on mutations', async () => {
    document.cookie = 'bizbazaar_csrf=proof';
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: 'Session revoked' })));
    vi.stubGlobal('fetch', fetch);
    await new LiveBizBazaarApi().logout();
    expect(fetch.mock.calls[0][1].credentials).toBe('include');
    expect(fetch.mock.calls[0][1].headers['X-CSRF-Token']).toBe('proof');
  });

  it('maps backend import counts and conflicts instead of claiming a direct schema match', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ imported: 2, invalid: 1,
      duplicates: 1, conflicts: 1, issues: [{row: 5, kind: 'CONFLICT', reason: 'Existing ID'}], issues_truncated: false })));
    vi.stubGlobal('fetch', fetch);
    const result = await new LiveBizBazaarApi().importTransactions(new File(['test'], 'test.csv'));
    expect(result.total_rows).toBe(5);
    expect(result.invalid_count).toBe(2);
    expect(result.imported_count).toBe(2);
    expect(result.issues[0].severity).toBe('ERROR');
  });

  it('does not replace missing analytics with mock metrics', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'UNAVAILABLE',
      result: null, limitations: ['Calculations are not implemented'] })));
    vi.stubGlobal('fetch', fetch);
    await expect(new LiveBizBazaarApi().getDashboard()).rejects.toMatchObject({ code: 'ANALYTICS_UNAVAILABLE' });
    expect(fetch.mock.calls[0][0]).toContain('start_date=');
  });

  it('sends event IDs and excludes unsupported customer contact fields', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ event_id: 'txn', transaction_id: 'txn',
      campaign_id: null, decision: 'CAMPAIGN_INACTIVE', reward_id: null, acceptance_sequence: null })));
    vi.stubGlobal('fetch', fetch);
    await new LiveBizBazaarApi().simulatePayment({ transaction_id: 'txn', amount_paise: 10000,
      timestamp: '2026-11-01T10:00:00Z', customer_vpa: 'not-collected@demo' });
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.event_id).toBe('txn');
    expect(body).not.toHaveProperty('customer_vpa');
  });
});
