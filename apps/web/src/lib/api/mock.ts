import {
  HealthResponse,
  MerchantSession,
  Transaction,
  TransactionImportReport,
  TransactionListResponse,
  DashboardResponse,
  AnalyticsResponse,
  ForecastResponse,
  Campaign,
  CreateCampaignRequest,
  RecommendationResponse,
  SimulatePaymentRequest,
  SimulatePaymentResponse,
  Reward,
  RewardListResponse,
  CampaignReport,
  DailySummaryResponse,
  TransactionStatus,
  CampaignStatus,
} from '../generated/types';
import { BizBazaarApi } from './types';

// Canonical fixture transactions
export const CANONICAL_TRANSACTIONS: Transaction[] = [
  {
    transaction_id: 'TXN001',
    merchant_id: 'm_001',
    amount_paise: 100000, // ₹1,000
    status: 'SUCCESS',
    timestamp: '2026-11-01T09:15:00Z',
    customer_vpa: 'customer1@okaxis',
    note: 'Groceries order 101',
  },
  {
    transaction_id: 'TXN002',
    merchant_id: 'm_001',
    amount_paise: 150000, // ₹1,500
    status: 'SUCCESS',
    timestamp: '2026-11-01T10:30:00Z',
    customer_vpa: 'customer2@oksbi',
    note: 'Provisions and spices',
  },
  {
    transaction_id: 'TXN003',
    merchant_id: 'm_001',
    amount_paise: 200000, // ₹2,000
    status: 'SUCCESS',
    timestamp: '2026-11-01T11:45:00Z',
    customer_vpa: 'customer3@okhdfc',
    note: 'Monthly pantry refill',
  },
  {
    transaction_id: 'TXN004',
    merchant_id: 'm_001',
    amount_paise: 250000, // ₹2,500
    status: 'SUCCESS',
    timestamp: '2026-11-01T14:20:00Z',
    customer_vpa: 'customer4@demo',
    note: 'Oil and pulses package',
  },
  {
    transaction_id: 'TXN005',
    merchant_id: 'm_001',
    amount_paise: 100000, // ₹1,000 (Crosses ₹8,000 cumulative)
    status: 'SUCCESS',
    timestamp: '2026-11-01T16:05:00Z',
    customer_vpa: 'customer5@okicici',
    note: 'Snacks and tea bags',
  },
  {
    transaction_id: 'TXN006',
    merchant_id: 'm_001',
    amount_paise: 50000, // ₹500
    status: 'SUCCESS',
    timestamp: '2026-11-01T17:40:00Z',
    customer_vpa: 'customer6@upi',
    note: 'Dairy and bread',
  },
  {
    transaction_id: 'TXN007',
    merchant_id: 'm_001',
    amount_paise: 70000, // ₹700
    status: 'PENDING',
    timestamp: '2026-11-01T18:10:00Z',
    customer_vpa: 'customer7@okaxis',
    note: 'Pending UPI confirmation',
  },
  {
    transaction_id: 'TXN008',
    merchant_id: 'm_001',
    amount_paise: 30000, // ₹300
    status: 'FAILED',
    timestamp: '2026-11-01T18:25:00Z',
    customer_vpa: 'customer8@oksbi',
    note: 'Bank server timeout',
  },
  {
    transaction_id: 'TXN009',
    merchant_id: 'm_001',
    amount_paise: 40000, // ₹400
    status: 'REFUNDED',
    timestamp: '2026-11-01T19:00:00Z',
    customer_vpa: 'customer9@okhdfc',
    note: 'Damaged packaging returned',
  },
];

export class MockBizBazaarApi implements BizBazaarApi {
  private session: MerchantSession = {
    merchant_id: 'm_001',
    merchant_name: 'Gupta Kirana Store',
    timezone: 'Asia/Kolkata',
    currency: 'INR',
    demo_mode: true,
  };

  private transactions: Transaction[] = [...CANONICAL_TRANSACTIONS];
  private campaigns: Campaign[] = [
    {
      id: 'cmp_canonical_01',
      merchant_id: 'm_001',
      name: 'Every 3rd Shopper Reward',
      type: 'NTH_PAYMENT',
      status: 'ACTIVE',
      rule_parameters: { n: 3 },
      reward_cost_paise: 10000, // ₹100
      budget_cap_paise: 10000, // ₹100 cap
      spent_budget_paise: 10000, // TXN003 utilized budget
      rewards_issued_count: 1,
      starts_at: '2026-11-01T00:00:00Z',
      ends_at: '2026-11-30T23:59:59Z',
      created_at: '2026-11-01T08:00:00Z',
    },
  ];

  private rewards: Reward[] = [
    {
      reward_id: 'rwd_001',
      campaign_id: 'cmp_canonical_01',
      transaction_id: 'TXN003',
      amount_paise: 10000,
      status: 'SIMULATED',
      recipient_vpa: 'customer3@okhdfc',
      created_at: '2026-11-01T11:45:00Z',
    },
  ];

  // Map to track simulated decisions by transaction_id: { amount_paise, decision, response }
  private simulationDecisions: Map<string, { amount_paise: number; response: SimulatePaymentResponse }> = new Map([
    [
      'TXN003',
      {
        amount_paise: 200000,
        response: {
          transaction_id: 'TXN003',
          decision: 'ISSUED',
          reward_issued_paise: 10000,
          remaining_budget_paise: 0,
          current_counter: 3,
          message: 'Qualified as 3rd shopper! ₹100 simulated reward issued. Budget cap reached.',
          is_replay: false,
        },
      },
    ],
  ]);

  private campaignCounters: Map<string, { count: number; cumulative_paise: number }> = new Map([
    ['cmp_canonical_01', { count: 6, cumulative_paise: 850000 }],
  ]);

  public resetState(): void {
    this.transactions = [...CANONICAL_TRANSACTIONS];
    this.campaigns = [
      {
        id: 'cmp_canonical_01',
        merchant_id: 'm_001',
        name: 'Every 3rd Shopper Reward',
        type: 'NTH_PAYMENT',
        status: 'ACTIVE',
        rule_parameters: { n: 3 },
        reward_cost_paise: 10000,
        budget_cap_paise: 10000,
        spent_budget_paise: 10000,
        rewards_issued_count: 1,
        starts_at: '2026-11-01T00:00:00Z',
        ends_at: '2026-11-30T23:59:59Z',
        created_at: '2026-11-01T08:00:00Z',
      },
    ];
    this.rewards = [
      {
        reward_id: 'rwd_001',
        campaign_id: 'cmp_canonical_01',
        transaction_id: 'TXN003',
        amount_paise: 10000,
        status: 'SIMULATED',
        recipient_vpa: 'customer3@okhdfc',
        created_at: '2026-11-01T11:45:00Z',
      },
    ];
    this.simulationDecisions = new Map([
      [
        'TXN003',
        {
          amount_paise: 200000,
          response: {
            transaction_id: 'TXN003',
            decision: 'ISSUED',
            reward_issued_paise: 10000,
            remaining_budget_paise: 0,
            current_counter: 3,
            message: 'Qualified as 3rd shopper! ₹100 simulated reward issued. Budget cap reached.',
            is_replay: false,
          },
        },
      ],
    ]);
    this.campaignCounters = new Map([
      ['cmp_canonical_01', { count: 6, cumulative_paise: 850000 }],
    ]);
  }

  async getHealth(): Promise<HealthResponse> {
    return {
      status: 'ok',
      timestamp: new Date().toISOString(),
    };
  }

  async getSession(): Promise<MerchantSession> {
    return { ...this.session };
  }

  async importTransactions(file: File): Promise<TransactionImportReport> {
    let text = '';
    if (typeof (file as any).text === 'function') {
      text = await file.text();
    } else if (typeof (file as any).arrayBuffer === 'function') {
      const buf = await (file as any).arrayBuffer();
      text = Buffer.from(buf).toString('utf-8');
    } else if (typeof FileReader !== 'undefined') {
      text = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsText(file);
      });
    }

    const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);

    if (lines.length === 0) {
      return {
        total_rows: 0,
        valid_count: 0,
        invalid_count: 0,
        duplicate_count: 0,
        imported_count: 0,
        issues: [{ row: 0, field: 'file', message: 'CSV file is empty', severity: 'ERROR' }],
      };
    }

    const header = lines[0].split(',').map((h) => h.trim());
    const expectedHeaders = ['transaction_id', 'merchant_id', 'amount_paise', 'status', 'timestamp'];
    const hasRequired = expectedHeaders.every((h) => header.includes(h));

    if (!hasRequired) {
      return {
        total_rows: lines.length - 1,
        valid_count: 0,
        invalid_count: lines.length - 1,
        duplicate_count: 0,
        imported_count: 0,
        issues: [
          {
            row: 1,
            field: 'header',
            message: `Missing required headers: expected ${expectedHeaders.join(', ')}`,
            severity: 'ERROR',
          },
        ],
      };
    }

    const issues: TransactionImportReport['issues'] = [];
    const validRows: Transaction[] = [];
    const existingIds = new Set(this.transactions.map((t) => t.transaction_id));
    const batchIds = new Set<string>();

    let duplicateCount = 0;
    let invalidCount = 0;

    for (let i = 1; i < lines.length; i++) {
      const rowNum = i + 1;
      const values = lines[i].split(',').map((v) => v.trim());
      if (values.length < expectedHeaders.length) {
        issues.push({
          row: rowNum,
          field: 'row',
          message: `Incomplete columns (found ${values.length}, expected >= ${expectedHeaders.length})`,
          severity: 'ERROR',
        });
        invalidCount++;
        continue;
      }

      const rowObj: Record<string, string> = {};
      header.forEach((h, idx) => {
        rowObj[h] = values[idx] || '';
      });

      const { transaction_id, merchant_id, amount_paise, status, timestamp, customer_vpa, note } = rowObj;

      // Merchant session check
      if (merchant_id && merchant_id !== this.session.merchant_id) {
        issues.push({
          row: rowNum,
          field: 'merchant_id',
          message: `Merchant ID '${merchant_id}' does not match authenticated session '${this.session.merchant_id}'`,
          severity: 'ERROR',
        });
        invalidCount++;
        continue;
      }

      // Check duplicate
      if (existingIds.has(transaction_id) || batchIds.has(transaction_id)) {
        issues.push({
          row: rowNum,
          field: 'transaction_id',
          message: `Duplicate transaction ID: '${transaction_id}' already exists`,
          severity: 'WARNING',
        });
        duplicateCount++;
        continue;
      }

      // Validate amount
      const amount = parseInt(amount_paise, 10);
      if (isNaN(amount) || amount <= 0) {
        issues.push({
          row: rowNum,
          field: 'amount_paise',
          message: `Invalid amount_paise '${amount_paise}'; must be positive integer paise`,
          severity: 'ERROR',
        });
        invalidCount++;
        continue;
      }

      // Validate status
      const validStatuses: TransactionStatus[] = ['SUCCESS', 'PENDING', 'FAILED', 'REFUNDED'];
      if (!validStatuses.includes(status as TransactionStatus)) {
        issues.push({
          row: rowNum,
          field: 'status',
          message: `Invalid status '${status}'. Must be SUCCESS, PENDING, FAILED, or REFUNDED`,
          severity: 'ERROR',
        });
        invalidCount++;
        continue;
      }

      // Valid transaction
      batchIds.add(transaction_id);
      validRows.push({
        transaction_id,
        merchant_id: this.session.merchant_id,
        amount_paise: amount,
        status: status as TransactionStatus,
        timestamp: timestamp || new Date().toISOString(),
        customer_vpa: customer_vpa || null,
        note: note || null,
      });
    }

    // Append valid transactions
    this.transactions.push(...validRows);

    return {
      total_rows: lines.length - 1,
      valid_count: validRows.length,
      invalid_count: invalidCount,
      duplicate_count: duplicateCount,
      imported_count: validRows.length,
      issues,
    };
  }

  async getTransactions(params?: {
    status?: TransactionStatus;
    limit?: number;
    offset?: number;
  }): Promise<TransactionListResponse> {
    let filtered = [...this.transactions];
    if (params?.status) {
      filtered = filtered.filter((t) => t.status === params.status);
    }
    const limit = params?.limit || 50;
    const offset = params?.offset || 0;
    const paginated = filtered.slice(offset, offset + limit);

    return {
      items: paginated,
      total: filtered.length,
      limit,
      offset,
    };
  }

  async getDashboard(): Promise<DashboardResponse> {
    const successfulTxns = this.transactions.filter((t) => t.status === 'SUCCESS');
    const pendingCount = this.transactions.filter((t) => t.status === 'PENDING').length;
    const failedCount = this.transactions.filter((t) => t.status === 'FAILED').length;
    const refundedCount = this.transactions.filter((t) => t.status === 'REFUNDED').length;

    const netRecordedCollections = successfulTxns.reduce((acc, t) => acc + t.amount_paise, 0);
    const count = successfulTxns.length;
    const average = count > 0 ? Math.round(netRecordedCollections / count) : null;

    const activeCampaign = this.campaigns.find((c) => c.status === 'ACTIVE') || null;

    const warnings: string[] = [];
    if (pendingCount > 0) {
      warnings.push(`${pendingCount} transaction(s) pending bank confirmation.`);
    }
    if (failedCount > 0) {
      warnings.push(`${failedCount} transaction(s) failed settlement.`);
    }
    if (refundedCount > 0) {
      warnings.push(`${refundedCount} transaction(s) refunded (deducted from net collections).`);
    }

    return {
      net_recorded_collections_paise: netRecordedCollections,
      successful_count: count,
      pending_count: pendingCount,
      failed_count: failedCount,
      refunded_count: refundedCount,
      average_paise: average,
      active_campaign: activeCampaign,
      warnings,
    };
  }

  async getAnalytics(): Promise<AnalyticsResponse> {
    const successfulTxns = this.transactions.filter((t) => t.status === 'SUCCESS');
    const totalPaise = successfulTxns.reduce((sum, t) => sum + t.amount_paise, 0);

    // Group by date
    const dailyMap = new Map<string, { paise: number; count: number }>();
    successfulTxns.forEach((t) => {
      const date = t.timestamp.split('T')[0];
      const cur = dailyMap.get(date) || { paise: 0, count: 0 };
      cur.paise += t.amount_paise;
      cur.count += 1;
      dailyMap.set(date, cur);
    });

    const daily_trends = Array.from(dailyMap.entries()).map(([date, val]) => ({
      date,
      successful_amount_paise: val.paise,
      successful_count: val.count,
    }));

    return {
      daily_trends: daily_trends.length > 0 ? daily_trends : [
        { date: '2026-11-01', successful_amount_paise: 850000, successful_count: 6 },
      ],
      peak_hour: '11:00 AM - 02:00 PM',
      recorded_collections_paise: totalPaise,
      top_payment_method: 'UPI QR (demo records)',
    };
  }

  async getForecast(): Promise<ForecastResponse> {
    return {
      status: 'INSUFFICIENT_DATA',
      message: 'At least 28 complete days and three observations per predicted weekday are required. This mock has no verified coverage declarations.',
      projected_next_week_collections_paise: null,
      confidence_interval: null,
    };
  }

  async getRecommendation(): Promise<RecommendationResponse> {
    return {
      recommendation_id: 'rec_growth_01',
      campaign_type: 'NTH_PAYMENT',
      title: 'Every 3rd Shopper Reward',
      rationale:
        'With an observed average basket of ₹1,416.67 across 6 successful payments, incentivizing every 3rd customer with ₹100 simulated reward boosts afternoon traffic while maintaining a fixed ₹100 maximum merchant budget cap.',
      suggested_rule_parameters: { n: 3 },
      suggested_reward_cost_paise: 10000, // ₹100
      suggested_budget_cap_paise: 10000, // ₹100
      estimated_target_orders: 6,
    };
  }

  async listCampaigns(status?: CampaignStatus): Promise<Campaign[]> {
    if (status) {
      return this.campaigns.filter((c) => c.status === status);
    }
    return [...this.campaigns];
  }

  async getCampaign(id: string): Promise<Campaign> {
    const cmp = this.campaigns.find((c) => c.id === id);
    if (!cmp) {
      throw new Error(`Campaign with id '${id}' not found`);
    }
    return { ...cmp };
  }

  async createCampaign(data: CreateCampaignRequest): Promise<Campaign> {
    const newCampaign: Campaign = {
      id: `cmp_${Date.now()}`,
      merchant_id: this.session.merchant_id,
      name: data.name,
      type: data.type,
      status: 'DRAFT', // Always created as DRAFT
      rule_parameters: data.rule_parameters,
      reward_cost_paise: data.reward_cost_paise,
      budget_cap_paise: data.budget_cap_paise,
      spent_budget_paise: 0,
      rewards_issued_count: 0,
      starts_at: data.starts_at,
      ends_at: data.ends_at,
      created_at: new Date().toISOString(),
    };

    this.campaigns.push(newCampaign);
    return newCampaign;
  }

  async approveCampaign(id: string): Promise<Campaign> {
    const cmp = this.campaigns.find((c) => c.id === id);
    if (!cmp) throw new Error(`Campaign '${id}' not found`);
    if (cmp.status !== 'DRAFT') {
      throw new Error(`Cannot approve campaign in status '${cmp.status}'. Must be DRAFT.`);
    }

    cmp.status = 'APPROVED';
    return { ...cmp };
  }

  async activateCampaign(id: string): Promise<Campaign> {
    const cmp = this.campaigns.find((c) => c.id === id);
    if (!cmp) throw new Error(`Campaign '${id}' not found`);
    if (cmp.status !== 'APPROVED') {
      throw new Error(`Cannot activate campaign in status '${cmp.status}'. Must be APPROVED first.`);
    }

    // Ensure no other active campaign exists
    const hasActive = this.campaigns.some((c) => c.id !== id && c.status === 'ACTIVE');
    if (hasActive) {
      throw new Error('Another campaign is currently ACTIVE. Complete it before activating a new one.');
    }

    cmp.status = 'ACTIVE';
    // Initialize or reset counter on activation
    this.campaignCounters.set(id, { count: 0, cumulative_paise: 0 });
    return { ...cmp };
  }

  async completeCampaign(id: string): Promise<Campaign> {
    const cmp = this.campaigns.find((c) => c.id === id);
    if (!cmp) throw new Error(`Campaign '${id}' not found`);

    cmp.status = 'COMPLETED';
    return { ...cmp };
  }

  async simulatePayment(data: SimulatePaymentRequest): Promise<SimulatePaymentResponse> {
    // 1. Check for duplicate replay
    const priorDecision = this.simulationDecisions.get(data.transaction_id);
    if (priorDecision) {
      if (priorDecision.amount_paise !== data.amount_paise) {
        // Conflicting repeat returns 409
        const err = new Error(
          `Conflict (409): Transaction ${data.transaction_id} already exists with different amount ${priorDecision.amount_paise} paise.`
        );
        (err as any).statusCode = 409;
        throw err;
      }
      // Identical repeat returns stored decision with is_replay = true
      return {
        ...priorDecision.response,
        is_replay: true,
        message: `(Replayed Event) ${priorDecision.response.message}`,
      };
    }

    // 2. Find active campaign
    const activeCampaign = this.campaigns.find((c) => c.status === 'ACTIVE');
    if (!activeCampaign) {
      const resp: SimulatePaymentResponse = {
        transaction_id: data.transaction_id,
        decision: 'NO_ACTIVE_CAMPAIGN',
        reward_issued_paise: 0,
        remaining_budget_paise: 0,
        current_counter: 0,
        message: 'Payment accepted. No active campaign currently running for merchant.',
        is_replay: false,
      };
      this.simulationDecisions.set(data.transaction_id, {
        amount_paise: data.amount_paise,
        response: resp,
      });
      return resp;
    }

    // Counter state
    const counterState = this.campaignCounters.get(activeCampaign.id) || { count: 0, cumulative_paise: 0 };
    const newCount = counterState.count + 1;
    const priorCumulative = counterState.cumulative_paise;
    const newCumulative = priorCumulative + data.amount_paise;

    counterState.count = newCount;
    counterState.cumulative_paise = newCumulative;
    this.campaignCounters.set(activeCampaign.id, counterState);

    let qualifies = false;
    let decisionReason = '';

    if (activeCampaign.type === 'NTH_PAYMENT') {
      const n = activeCampaign.rule_parameters.n || 3;
      qualifies = newCount % n === 0;
      decisionReason = qualifies
        ? `Payment #${newCount} qualifies under N=${n} rule.`
        : `Payment #${newCount} recorded (need multiple of ${n}).`;
    } else if (activeCampaign.type === 'COLLECTION_THRESHOLD') {
      const threshold = activeCampaign.rule_parameters.threshold_paise || 800000;
      // Single reward for first event where prior_cumulative < threshold <= new_cumulative
      qualifies = priorCumulative < threshold && newCumulative >= threshold;
      decisionReason = qualifies
        ? `Collections reached ₹${(newCumulative / 100).toFixed(2)}, crossing threshold of ₹${(threshold / 100).toFixed(2)}!`
        : `Collections at ₹${(newCumulative / 100).toFixed(2)} (threshold: ₹${(threshold / 100).toFixed(2)}).`;
    }

    let decision: SimulatePaymentResponse['decision'] = 'NOT_QUALIFIED';
    let rewardIssued = 0;
    const remainingBudget = activeCampaign.budget_cap_paise - activeCampaign.spent_budget_paise;

    if (qualifies) {
      if (remainingBudget >= activeCampaign.reward_cost_paise) {
        decision = 'ISSUED';
        rewardIssued = activeCampaign.reward_cost_paise;
        activeCampaign.spent_budget_paise += rewardIssued;
        activeCampaign.rewards_issued_count += 1;

        // Create reward record
        this.rewards.unshift({
          reward_id: `rwd_${Date.now()}_${data.transaction_id}`,
          campaign_id: activeCampaign.id,
          transaction_id: data.transaction_id,
          amount_paise: rewardIssued,
          status: 'SIMULATED',
          recipient_vpa: data.customer_vpa || 'customer@bank',
          created_at: new Date().toISOString(),
        });
      } else {
        decision = 'SKIPPED_BUDGET';
      }
    }

    const updatedRemainingBudget = activeCampaign.budget_cap_paise - activeCampaign.spent_budget_paise;
    const responseMessage =
      decision === 'ISSUED'
        ? `Reward Issued! ₹${rewardIssued / 100} simulated reward allocated. ${decisionReason}`
        : decision === 'SKIPPED_BUDGET'
        ? `Qualifying order, but skipped because campaign budget cap of ₹${activeCampaign.budget_cap_paise / 100} has been exhausted.`
        : `Accepted. ${decisionReason}`;

    const simResponse: SimulatePaymentResponse = {
      transaction_id: data.transaction_id,
      decision,
      reward_issued_paise: rewardIssued,
      remaining_budget_paise: updatedRemainingBudget,
      current_counter: newCount,
      message: responseMessage,
      is_replay: false,
    };

    this.simulationDecisions.set(data.transaction_id, {
      amount_paise: data.amount_paise,
      response: simResponse,
    });

    return simResponse;
  }

  async getRewards(params?: { limit?: number; offset?: number }): Promise<RewardListResponse> {
    const limit = params?.limit || 50;
    const offset = params?.offset || 0;
    return {
      items: this.rewards.slice(offset, offset + limit),
      total: this.rewards.length,
      limit,
      offset,
    };
  }

  async getCampaignReport(id: string): Promise<CampaignReport> {
    const cmp = this.campaigns.find((c) => c.id === id);
    if (!cmp) throw new Error(`Campaign '${id}' not found`);

    const remaining = cmp.budget_cap_paise - cmp.spent_budget_paise;
    const utilization = cmp.budget_cap_paise > 0 ? (cmp.spent_budget_paise / cmp.budget_cap_paise) * 100 : 0;

    return {
      campaign_id: cmp.id,
      campaign_name: cmp.name,
      campaign_type: cmp.type,
      status: cmp.status,
      budget_cap_paise: cmp.budget_cap_paise,
      spent_budget_paise: cmp.spent_budget_paise,
      remaining_budget_paise: remaining,
      total_qualifying_events: cmp.rewards_issued_count + (cmp.spent_budget_paise >= cmp.budget_cap_paise ? 1 : 0),
      total_rewards_issued: cmp.rewards_issued_count,
      budget_utilization_pct: Math.min(100, Math.round(utilization * 10) / 10),
    };
  }

  async getDailySummary(): Promise<DailySummaryResponse> {
    const successfulTxns = this.transactions.filter((t) => t.status === 'SUCCESS');
    const netPaise = successfulTxns.reduce((sum, t) => sum + t.amount_paise, 0);
    const count = successfulTxns.length;
    const avgPaise = count > 0 ? Math.round(netPaise / count) : 0;

    const totalSimulatedRewardsPaise = this.rewards.reduce((sum, r) => sum + r.amount_paise, 0);
    const inrText = `₹${(netPaise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    const avgText = `₹${(avgPaise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    const rewardsText = `₹${(totalSimulatedRewardsPaise / 100).toLocaleString('en-IN')}`;

    return {
      date: '2026-11-01',
      merchant_name: this.session.merchant_name,
      recorded_collections_paise: netPaise,
      successful_transactions_count: count,
      simulated_rewards_cost_paise: totalSimulatedRewardsPaise,
      text_summary: `Namaste! On 01 Nov 2026, ${this.session.merchant_name} recorded collections of ${inrText} across ${count} successful payments with an average payment size of ${avgText}. ${this.rewards.length} simulated reward(s) worth ${rewardsText} were issued under active merchant promotions.`,
      voice_script: `Namaste ${this.session.merchant_name}! Today you recorded collections of ${Math.round(netPaise / 100)} rupees from ${count} successful transactions. Your average payment was ${Math.round(avgPaise / 100)} rupees. ${this.rewards.length} simulated reward worth ${Math.round(totalSimulatedRewardsPaise / 100)} rupees was granted.`,
    };
  }
}

export const mockBizBazaarApi = new MockBizBazaarApi();
