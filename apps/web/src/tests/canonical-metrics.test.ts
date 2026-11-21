import { describe, it, expect, beforeEach } from 'vitest';
import { MockBizBazaarApi, CANONICAL_TRANSACTIONS } from '../lib/api/mock';
import { formatPaiseToINR } from '../lib/utils';

describe('Canonical Verification Fixture Metrics', () => {
  let api: MockBizBazaarApi;

  beforeEach(() => {
    api = new MockBizBazaarApi();
    api.resetState();
  });

  it('renders exact canonical numbers: ₹8,500.00 net collections, 6 count, ₹1,416.67 average', async () => {
    const dashboard = await api.getDashboard();

    // 1. Net recorded collections must be exactly 850,000 paise (₹8,500.00)
    expect(dashboard.net_recorded_collections_paise).toBe(850000);
    expect(formatPaiseToINR(dashboard.net_recorded_collections_paise)).toBe('₹8,500.00');

    // 2. Successful payment count must be 6
    expect(dashboard.successful_count).toBe(6);

    // 3. Pending, failed, and refunded counts
    expect(dashboard.pending_count).toBe(1);
    expect(dashboard.failed_count).toBe(1);
    expect(dashboard.refunded_count).toBe(1);

    // 4. Average must be 850,000 / 6 = 141,667 paise (₹1,416.67 half-up)
    expect(dashboard.average_paise).toBe(141667);
    expect(formatPaiseToINR(dashboard.average_paise)).toBe('₹1,416.67');
  });

  it('verifies that pending, failed, and refunded payments do not contribute to recorded collections', async () => {
    const successfulTxns = CANONICAL_TRANSACTIONS.filter((t) => t.status === 'SUCCESS');
    const totalSuccessfulPaise = successfulTxns.reduce((sum, t) => sum + t.amount_paise, 0);

    expect(successfulTxns.length).toBe(6);
    expect(totalSuccessfulPaise).toBe(850000);

    // Pending: TXN007 ₹700 (70,000 paise)
    const pendingTxn = CANONICAL_TRANSACTIONS.find((t) => t.status === 'PENDING');
    expect(pendingTxn?.amount_paise).toBe(70000);

    // Failed: TXN008 ₹300 (30,000 paise)
    const failedTxn = CANONICAL_TRANSACTIONS.find((t) => t.status === 'FAILED');
    expect(failedTxn?.amount_paise).toBe(30000);

    // Refunded: TXN009 ₹400 (40,000 paise)
    const refundedTxn = CANONICAL_TRANSACTIONS.find((t) => t.status === 'REFUNDED');
    expect(refundedTxn?.amount_paise).toBe(40000);
  });

  it('verifies that fifth successful payment reaches/crosses ₹8,000 milestone in server acceptance order', () => {
    const successfulTxns = CANONICAL_TRANSACTIONS.filter((t) => t.status === 'SUCCESS');
    let cumulative = 0;
    const cumulativeHistory: { id: string; cumulative: number }[] = [];

    for (const txn of successfulTxns) {
      cumulative += txn.amount_paise;
      cumulativeHistory.push({ id: txn.transaction_id, cumulative });
    }

    // Cumulative progression:
    // TXN001: 100,000 (₹1,000)
    // TXN002: 250,000 (₹2,500)
    // TXN003: 450,000 (₹4,500)
    // TXN004: 700,000 (₹7,000)
    // TXN005: 800,000 (₹8,000) -> reaches ₹8,000 threshold exactly!
    // TXN006: 850,000 (₹8,500)
    expect(cumulativeHistory[0].cumulative).toBe(100000);
    expect(cumulativeHistory[1].cumulative).toBe(250000);
    expect(cumulativeHistory[2].cumulative).toBe(450000);
    expect(cumulativeHistory[3].cumulative).toBe(700000);
    expect(cumulativeHistory[4].id).toBe('TXN005');
    expect(cumulativeHistory[4].cumulative).toBe(800000);
    expect(cumulativeHistory[5].cumulative).toBe(850000);
  });

  it('correctly handles forecast data sufficiency rule', async () => {
    const forecast = await api.getForecast();
    // In canonical fixture, only 1 date is present, so status must be INSUFFICIENT_DATA
    expect(forecast.status).toBe('INSUFFICIENT_DATA');
    expect(forecast.message).toContain('At least 28 complete days');
    expect(forecast.projected_next_week_collections_paise).toBeNull();
  });
});
