import type * as Wire from '../generated/backend';
import type * as View from '../generated/types';
import type { BizBazaarApi } from './types';

export class LiveApiError extends Error {
  constructor(message: string, public code = 'API_ERROR', public statusCode = 500,
    public details?: unknown, public requestId?: string) {
    super(message);
    this.name = 'LiveApiError';
  }
}

export function csrfToken(): string {
  if (typeof document === 'undefined') return '';
  const entry = document.cookie.split('; ').find(item => item.startsWith('bizbazaar_csrf='));
  return entry ? decodeURIComponent(entry.slice('bizbazaar_csrf='.length)) : '';
}

function mapCampaign(row: Wire.CampaignView): View.Campaign {
  return { id: row.id, name: row.name, type: row.type, status: row.status,
    rule_parameters: row.rule_parameters, reward_cost_paise: row.reward_cost_paise,
    budget_cap_paise: row.budget_cap_paise, spent_budget_paise: row.consumed_paise,
    rewards_issued_count: row.rewards_issued_count, starts_at: row.starts_at, ends_at: row.ends_at };
}

function available<T>(response: { status: string; result: T | null; limitations: string[] }): T {
  if (response.status !== 'AVAILABLE' || response.result === null) {
    throw new LiveApiError(response.limitations.join(' '), 'ANALYTICS_UNAVAILABLE', 503);
  }
  return response.result;
}

export class LiveBizBazaarApi implements BizBazaarApi {
  private baseUrl: string;
  private timezone = 'Asia/Kolkata';

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20_000);
    const method = options.method || 'GET';
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options, credentials: 'include', signal: controller.signal,
        headers: { Accept: 'application/json',
          ...(method !== 'GET' ? { 'X-CSRF-Token': csrfToken() } : {}), ...options.headers },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as Wire.ErrorEnvelope | null;
        throw new LiveApiError(body?.error.message || `Request failed (${response.status})`,
          body?.error.code || 'HTTP_ERROR', response.status,
          body?.error.details, body?.error.request_id);
      }
      return await response.json() as T;
    } catch (error) {
      if (error instanceof LiveApiError) throw error;
      throw new LiveApiError('Unable to reach the BizBazaar API. Check the local backend connection.',
        controller.signal.aborted ? 'TIMEOUT' : 'NETWORK_ERROR', 0);
    } finally {
      clearTimeout(timer);
    }
  }

  private today(): string {
    return new Intl.DateTimeFormat('en-CA', { timeZone: this.timezone,
      year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  }

  private range(): string {
    const end = this.today();
    const start = new Date(`${end}T00:00:00Z`);
    start.setUTCDate(start.getUTCDate() - 29);
    return `start_date=${start.toISOString().slice(0, 10)}&end_date=${end}`;
  }

  async connect(token: string): Promise<View.MerchantSession> {
    const row = await this.request<Wire.SessionView>('/demo/session', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }),
    });
    this.timezone = row.timezone;
    return { merchant_id: row.merchant_id, merchant_name: row.merchant_name,
      timezone: row.timezone, currency: 'INR', demo_mode: true };
  }

  async logout(): Promise<void> {
    await this.request<Wire.MessageView>('/session/logout', { method: 'POST' });
  }

  async getHealth(): Promise<View.HealthResponse> {
    const row = await this.request<Wire.HealthView>('/health');
    return { status: row.status || 'ok', timestamp: '' };
  }

  async getSession(): Promise<View.MerchantSession> {
    const row = await this.request<Wire.SessionView>('/session');
    this.timezone = row.timezone;
    return { merchant_id: row.merchant_id, merchant_name: row.merchant_name,
      timezone: row.timezone, currency: 'INR', demo_mode: row.is_demo === true };
  }

  async importTransactions(file: File): Promise<View.TransactionImportReport> {
    const body = new FormData();
    body.append('file', file);
    const row = await this.request<Wire.ImportReport>('/transactions/import', { method: 'POST', body });
    return { total_rows: row.imported + row.invalid + row.duplicates + row.conflicts,
      valid_count: row.imported, imported_count: row.imported,
      invalid_count: row.invalid + row.conflicts, duplicate_count: row.duplicates,
      issues: row.issues.map(issue => ({ row: issue.row, field: issue.field || 'transaction_id',
        message: issue.reason, severity: issue.kind === 'DUPLICATE' ? 'WARNING' : 'ERROR' })) };
  }

  async getTransactions(params?: { status?: View.TransactionStatus; limit?: number; offset?: number }): Promise<View.TransactionListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const row = await this.request<Wire.Page_TransactionView_>(`/transactions?${query}`);
    const session = await this.getSession();
    return { ...row, items: row.items.map(item => ({ transaction_id: item.transaction_id,
      merchant_id: session.merchant_id, amount_paise: item.amount_paise,
      timestamp: item.timestamp, status: item.status })) };
  }

  async listCampaigns(status?: View.CampaignStatus): Promise<View.Campaign[]> {
    const rows: View.Campaign[] = [];
    for (let offset = 0; offset < 1000; offset += 100) {
      const page = await this.request<Wire.Page_CampaignView_>(`/campaigns?limit=100&offset=${offset}`);
      rows.push(...page.items.map(mapCampaign));
      if (offset + page.items.length >= page.total) return status ? rows.filter(row => row.status === status) : rows;
    }
    throw new LiveApiError('Too many campaigns for this view. Use the paginated API.', 'VIEW_LIMIT');
  }

  async getCampaign(id: string): Promise<View.Campaign> {
    return mapCampaign(await this.request<Wire.CampaignView>(`/campaigns/${encodeURIComponent(id)}`));
  }

  async createCampaign(data: View.CreateCampaignRequest): Promise<View.Campaign> {
    return mapCampaign(await this.request<Wire.CampaignView>('/campaigns', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    }));
  }

  private async transition(id: string, action: string): Promise<View.Campaign> {
    return mapCampaign(await this.request<Wire.CampaignView>(`/campaigns/${encodeURIComponent(id)}/${action}`, { method: 'POST' }));
  }
  approveCampaign(id: string) { return this.transition(id, 'approve'); }
  activateCampaign(id: string) { return this.transition(id, 'activate'); }
  completeCampaign(id: string) { return this.transition(id, 'complete'); }

  async simulatePayment(data: View.SimulatePaymentRequest): Promise<View.SimulatePaymentResponse> {
    // Stable ID for a transaction: retries cannot evade backend transaction deduplication.
    const payload: Wire.SimulationPayment = { event_id: data.transaction_id,
      transaction_id: data.transaction_id, amount_paise: data.amount_paise,
      timestamp: data.timestamp, status: 'SUCCESS' };
    const row = await this.request<Wire.PaymentDecision>('/simulations/payments', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const decisions = { ISSUED: 'ISSUED', SKIPPED_BUDGET: 'SKIPPED_BUDGET',
      NOT_ELIGIBLE: 'NOT_QUALIFIED', CAMPAIGN_INACTIVE: 'NO_ACTIVE_CAMPAIGN' } as const;
    return { transaction_id: row.transaction_id, decision: decisions[row.decision],
      reward_issued_paise: row.reward_cost_paise ?? 0,
      remaining_budget_paise: row.remaining_budget_paise ?? null,
      current_counter: row.eligible_count ?? null,
      message: `Simulated event decision: ${row.decision}.` };
  }

  async getRewards(params?: { limit?: number; offset?: number }): Promise<View.RewardListResponse> {
    const query = new URLSearchParams({ limit: String(params?.limit ?? 20), offset: String(params?.offset ?? 0) });
    const row = await this.request<Wire.Page_RewardView_>(`/rewards?${query}`);
    return { ...row, items: row.items.map(item => ({ reward_id: item.id,
      campaign_id: item.campaign_id, transaction_id: item.transaction_id || item.transaction_pk,
      amount_paise: item.cost_paise, status: 'SIMULATED', created_at: item.created_at })) };
  }

  async getCampaignReport(id: string): Promise<View.CampaignReport> {
    const row = await this.request<Wire.ReportView>(`/campaigns/${encodeURIComponent(id)}/report`);
    return { campaign_id: row.campaign.id, campaign_name: row.campaign.name,
      campaign_type: row.campaign.type, status: row.campaign.status,
      budget_cap_paise: row.campaign.budget_cap_paise, spent_budget_paise: row.issued_cost_paise,
      remaining_budget_paise: row.remaining_budget_paise,
      total_qualifying_events: row.campaign.eligible_count, total_rewards_issued: row.issued_count,
      budget_utilization_pct: Math.round(100 * row.issued_cost_paise / row.campaign.budget_cap_paise) };
  }

  async getDashboard(): Promise<View.DashboardResponse> {
    const envelope = await this.request<Wire.DashboardEnvelope>(`/dashboard?${this.range()}`);
    const metrics = available(envelope);
    const campaigns = await this.listCampaigns('ACTIVE');
    return { net_recorded_collections_paise: metrics.collections_paise,
      successful_count: metrics.successful_count, average_paise: metrics.average_payment_paise,
      pending_count: metrics.status_counts.pending, failed_count: metrics.status_counts.failed,
      refunded_count: metrics.status_counts.refunded, active_campaign: campaigns[0] || null,
      warnings: [...metrics.warnings, ...envelope.limitations] };
  }

  async getAnalytics(): Promise<View.AnalyticsResponse> {
    const result = available(await this.request<Wire.TrendsEnvelope>(`/analytics?${this.range()}`));
    return { recorded_collections_paise: result.metrics.collections_paise,
      average_value_decline_percent: result.average_value_decline_percent,
      insights: [...result.slow_periods.map(row => row.explanation), ...result.limitations],
      daily_trends: result.metrics.daily_collections.map(row => ({ date: row.date,
        successful_amount_paise: row.collections_paise, successful_count: row.successful_count })),
      peak_hour: 'Not available from this contract', top_payment_method: 'Not collected' };
  }

  async getForecast(): Promise<View.ForecastResponse> {
    const result = available(await this.request<Wire.ForecastEnvelope>(`/forecast?${this.range()}&horizon_days=7`));
    return { status: result.status, message: result.limitations.join(' '),
      projected_next_week_collections_paise: result.status === 'AVAILABLE'
        ? result.projected_total_paise : null,
      confidence_interval: null };
  }

  async getRecommendation(): Promise<View.RecommendationResponse> {
    const envelope = await this.request<Wire.RecommendationEnvelope>(`/recommendations/current?${this.range()}`);
    const result = available(envelope);
    const action = result.suggested_action;
    if (!action) throw new LiveApiError(result.explanation, 'NO_RECOMMENDATION', 503);
    return { generation_mode: result.generation_mode,
      recommendation_id: `configured-${envelope.end_date}`, campaign_type: action.type,
      title: action.name, rationale: result.explanation, suggested_rule_parameters: action.rule_parameters,
      suggested_reward_cost_paise: action.reward_cost_paise, suggested_budget_cap_paise: action.budget_cap_paise,
      suggested_starts_at: action.starts_at, suggested_ends_at: action.ends_at };
  }

  async getDailySummary(locale: 'en-IN' | 'hi-IN' = 'en-IN'): Promise<View.DailySummaryResponse> {
    const result = available(await this.request<Wire.SummaryEnvelope>(`/summaries/daily?report_date=${this.today()}&locale=${locale}`));
    const session = await this.getSession();
    return { date: result.date, merchant_name: session.merchant_name,
      recorded_collections_paise: result.metrics.collections_paise,
      locale: result.locale,
      successful_transactions_count: result.metrics.successful_count,
      text_summary: result.summary_text, voice_script: result.summary_text };
  }
}

export const liveBizBazaarApi = new LiveBizBazaarApi();
