import { describe, it, expect, beforeEach } from 'vitest';
import { MockBizBazaarApi } from '../lib/api/mock';

describe('Campaign Lifecycle and Deterministic Reward Rules', () => {
  let api: MockBizBazaarApi;

  beforeEach(() => {
    api = new MockBizBazaarApi();
    api.resetState();
  });

  it('enforces two-step merchant approval then activation', async () => {
    // 1. Create Draft
    const draft = await api.createCampaign({
      name: 'Test Promotion',
      type: 'NTH_PAYMENT',
      rule_parameters: { n: 5 },
      reward_cost_paise: 5000,
      budget_cap_paise: 20000,
      starts_at: '2026-11-01T00:00:00Z',
      ends_at: '2026-11-30T23:59:59Z',
    });

    expect(draft.status).toBe('DRAFT');

    // 2. Attempting to activate directly from DRAFT must fail
    await expect(api.activateCampaign(draft.id)).rejects.toThrow(/Must be APPROVED first/);

    // 3. Approve draft
    const approved = await api.approveCampaign(draft.id);
    expect(approved.status).toBe('APPROVED');

    // 4. Activating when another campaign is active must fail
    // (canonical active campaign 'cmp_canonical_01' is currently active)
    await expect(api.activateCampaign(draft.id)).rejects.toThrow(/Another campaign is currently ACTIVE/);

    // 5. Complete existing active campaign
    await api.completeCampaign('cmp_canonical_01');

    // 6. Now activation succeeds
    const activated = await api.activateCampaign(draft.id);
    expect(activated.status).toBe('ACTIVE');
  });

  it('evaluates N=3 payment rule, caps budget, and skips when cap reached', async () => {
    // End canonical campaign and create fresh N=3 with ₹100 reward & ₹100 cap
    await api.completeCampaign('cmp_canonical_01');

    const freshCmp = await api.createCampaign({
      name: 'Fresh N=3 Campaign',
      type: 'NTH_PAYMENT',
      rule_parameters: { n: 3 },
      reward_cost_paise: 10000, // ₹100
      budget_cap_paise: 10000, // ₹100 total budget
      starts_at: '2026-11-01T00:00:00Z',
      ends_at: '2026-11-30T23:59:59Z',
    });

    await api.approveCampaign(freshCmp.id);
    await api.activateCampaign(freshCmp.id);

    // Event 1 (TXN_A) -> Counter 1 -> NOT_QUALIFIED
    const res1 = await api.simulatePayment({
      transaction_id: 'TXN_A',
      amount_paise: 100000,
      timestamp: '2026-11-01T10:00:00Z',
    });
    expect(res1.decision).toBe('NOT_QUALIFIED');
    expect(res1.current_counter).toBe(1);
    expect(res1.reward_issued_paise).toBe(0);
    expect(res1.remaining_budget_paise).toBe(10000);

    // Event 2 (TXN_B) -> Counter 2 -> NOT_QUALIFIED
    const res2 = await api.simulatePayment({
      transaction_id: 'TXN_B',
      amount_paise: 150000,
      timestamp: '2026-11-01T11:00:00Z',
    });
    expect(res2.decision).toBe('NOT_QUALIFIED');
    expect(res2.current_counter).toBe(2);

    // Event 3 (TXN_C) -> Counter 3 -> ISSUED! (3 is divisible by 3)
    const res3 = await api.simulatePayment({
      transaction_id: 'TXN_C',
      amount_paise: 200000,
      timestamp: '2026-11-01T12:00:00Z',
    });
    expect(res3.decision).toBe('ISSUED');
    expect(res3.current_counter).toBe(3);
    expect(res3.reward_issued_paise).toBe(10000); // ₹100
    expect(res3.remaining_budget_paise).toBe(0); // Budget cap now fully consumed

    // Event 4 (TXN_D) -> Counter 4 -> NOT_QUALIFIED
    const res4 = await api.simulatePayment({
      transaction_id: 'TXN_D',
      amount_paise: 250000,
      timestamp: '2026-11-01T13:00:00Z',
    });
    expect(res4.decision).toBe('NOT_QUALIFIED');

    // Event 5 (TXN_E) -> Counter 5 -> NOT_QUALIFIED
    const res5 = await api.simulatePayment({
      transaction_id: 'TXN_E',
      amount_paise: 100000,
      timestamp: '2026-11-01T14:00:00Z',
    });
    expect(res5.decision).toBe('NOT_QUALIFIED');

    // Event 6 (TXN_F) -> Counter 6 -> Qualifies under N=3, BUT budget exhausted -> SKIPPED_BUDGET
    const res6 = await api.simulatePayment({
      transaction_id: 'TXN_F',
      amount_paise: 50000,
      timestamp: '2026-11-01T15:00:00Z',
    });
    expect(res6.decision).toBe('SKIPPED_BUDGET');
    expect(res6.current_counter).toBe(6);
    expect(res6.reward_issued_paise).toBe(0);
    expect(res6.remaining_budget_paise).toBe(0);
  });

  it('guarantees replay idempotency and 409 conflict detection', async () => {
    // In canonical fixture, TXN003 is already recorded with amount 200000 paise (₹2,000) and decision ISSUED
    const replayRes = await api.simulatePayment({
      transaction_id: 'TXN003',
      amount_paise: 200000, // identical amount
      timestamp: '2026-11-01T11:45:00Z',
    });

    expect(replayRes.is_replay).toBe(true);
    expect(replayRes.decision).toBe('ISSUED');

    // Conflicting replay with different amount must trigger 409 conflict
    await expect(
      api.simulatePayment({
        transaction_id: 'TXN003',
        amount_paise: 99900, // changed amount!
        timestamp: '2026-11-01T11:45:00Z',
      })
    ).rejects.toThrow(/Conflict \(409\)/);
  });
});
