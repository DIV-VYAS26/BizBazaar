import { describe, it, expect, beforeEach } from 'vitest';
import { MockBizBazaarApi } from '../lib/api/mock';

describe('CSV Validation and Transaction Ingestion', () => {
  let api: MockBizBazaarApi;

  beforeEach(() => {
    api = new MockBizBazaarApi();
    api.resetState();
  });

  it('rejects CSV with missing required columns', async () => {
    const badCsv = `amount_paise,status\n10000,SUCCESS`;
    const file = new File([badCsv], 'bad.csv', { type: 'text/csv' });

    const report = await api.importTransactions(file);
    expect(report.valid_count).toBe(0);
    expect(report.issues[0].field).toBe('header');
    expect(report.issues[0].severity).toBe('ERROR');
  });

  it('correctly reports valid, duplicate, and invalid rows', async () => {
    // TXN001 already exists in canonical fixture
    const csvContent = `transaction_id,merchant_id,amount_paise,status,timestamp,customer_vpa,note
TXN_NEW_01,m_001,50000,SUCCESS,2026-11-02T10:00:00Z,shopper@upi,Valid item
TXN001,m_001,100000,SUCCESS,2026-11-02T10:15:00Z,shopper@upi,Duplicate TXN001
TXN_BAD_AMT,m_001,-5000,SUCCESS,2026-11-02T10:30:00Z,shopper@upi,Negative amount
TXN_BAD_STAT,m_001,30000,INVALID_STAT,2026-11-02T10:45:00Z,shopper@upi,Bad status
TXN_BAD_MCH,m_WRONG,20000,SUCCESS,2026-11-02T11:00:00Z,shopper@upi,Wrong merchant`;

    const file = new File([csvContent], 'test.csv', { type: 'text/csv' });
    const report = await api.importTransactions(file);

    expect(report.total_rows).toBe(5);
    expect(report.valid_count).toBe(1);
    expect(report.duplicate_count).toBe(1);
    expect(report.invalid_count).toBe(3);
    expect(report.imported_count).toBe(1);

    // Verify row-level issues
    expect(report.issues.some((i) => i.field === 'transaction_id' && i.severity === 'WARNING')).toBe(true);
    expect(report.issues.some((i) => i.field === 'amount_paise' && i.severity === 'ERROR')).toBe(true);
    expect(report.issues.some((i) => i.field === 'status' && i.severity === 'ERROR')).toBe(true);
    expect(report.issues.some((i) => i.field === 'merchant_id' && i.severity === 'ERROR')).toBe(true);
  });
});
