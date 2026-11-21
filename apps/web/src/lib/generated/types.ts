/**
 * Member 1 presentation types; backend wire types are generated in backend.ts.
 * The live API adapter maps backend wire types into these presentation types.
 * Monetary values are integer paise; timestamps are ISO-8601 strings.
 */

export type TransactionStatus = 'SUCCESS' | 'PENDING' | 'FAILED' | 'REFUNDED';
export type CampaignType = 'NTH_PAYMENT' | 'COLLECTION_THRESHOLD';
export type CampaignStatus = 'DRAFT' | 'APPROVED' | 'ACTIVE' | 'COMPLETED';
export type SimulationDecision = 'ISSUED' | 'SKIPPED_BUDGET' | 'NOT_QUALIFIED' | 'NO_ACTIVE_CAMPAIGN';
export type ForecastStatus = 'INSUFFICIENT_DATA' | 'AVAILABLE';

export interface HealthResponse {
  status: string;
  timestamp: string;
}

export interface MerchantSession {
  merchant_id: string;
  merchant_name: string;
  timezone: string;
  currency: 'INR';
  demo_mode: boolean;
}

export interface Transaction {
  transaction_id: string;
  merchant_id: string;
  amount_paise: number;
  status: TransactionStatus;
  timestamp: string;
  customer_vpa?: string | null;
  note?: string | null;
}

export interface TransactionImportIssue {
  row: number;
  field: string;
  message: string;
  severity: 'WARNING' | 'ERROR';
}

export interface TransactionImportReport {
  total_rows: number;
  valid_count: number;
  invalid_count: number;
  duplicate_count: number;
  imported_count: number;
  issues: TransactionImportIssue[];
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  limit: number;
  offset: number;
}

export interface CampaignRuleParameters {
  n?: number;
  threshold_paise?: number;
}

export interface Campaign {
  id: string;
  merchant_id?: string;
  name: string;
  type: CampaignType;
  status: CampaignStatus;
  rule_parameters: CampaignRuleParameters;
  reward_cost_paise: number;
  budget_cap_paise: number;
  spent_budget_paise: number;
  rewards_issued_count: number;
  starts_at: string;
  ends_at: string;
  created_at?: string;
}

export interface DashboardResponse {
  net_recorded_collections_paise: number;
  successful_count: number;
  pending_count: number;
  failed_count: number;
  refunded_count: number;
  average_paise: number | null;
  active_campaign: Campaign | null;
  warnings: string[];
}

export interface AnalyticsPoint {
  date: string;
  successful_amount_paise: number;
  successful_count: number;
}

export interface AnalyticsResponse {
  average_value_decline_percent?: number | null;
  insights?: string[];
  daily_trends: AnalyticsPoint[];
  peak_hour: string;
  recorded_collections_paise: number;
  top_payment_method: string;
}

export interface ForecastResponse {
  status: ForecastStatus;
  message: string;
  projected_next_week_collections_paise?: number | null;
  confidence_interval?: string | null;
}

export interface CreateCampaignRequest {
  name: string;
  type: CampaignType;
  rule_parameters: CampaignRuleParameters;
  reward_cost_paise: number;
  budget_cap_paise: number;
  starts_at: string;
  ends_at: string;
}

export interface RecommendationResponse {
  generation_mode?: 'DETERMINISTIC_FALLBACK' | 'EXTERNAL_LLM';
  recommendation_id: string;
  campaign_type: CampaignType;
  title: string;
  rationale: string;
  suggested_rule_parameters: CampaignRuleParameters;
  suggested_reward_cost_paise: number;
  suggested_budget_cap_paise: number;
  suggested_starts_at?: string;
  suggested_ends_at?: string;
  estimated_target_orders?: number;
}

export interface SimulatePaymentRequest {
  transaction_id: string;
  amount_paise: number;
  timestamp: string;
  customer_vpa?: string;
}

export interface SimulatePaymentResponse {
  transaction_id: string;
  decision: SimulationDecision;
  reward_issued_paise: number;
  remaining_budget_paise: number | null;
  current_counter: number | null;
  message: string;
  is_replay?: boolean;
}

export interface Reward {
  reward_id: string;
  campaign_id: string;
  transaction_id: string;
  amount_paise: number;
  status: 'SIMULATED';
  recipient_vpa?: string;
  created_at: string;
}

export interface RewardListResponse {
  items: Reward[];
  total: number;
  limit: number;
  offset: number;
}

export interface CampaignReport {
  campaign_id: string;
  campaign_name: string;
  campaign_type: CampaignType;
  status: CampaignStatus;
  budget_cap_paise: number;
  spent_budget_paise: number;
  remaining_budget_paise: number;
  total_qualifying_events: number;
  total_rewards_issued: number;
  budget_utilization_pct: number;
}

export interface DailySummaryResponse {
  locale?: 'en-IN' | 'hi-IN';
  date: string;
  merchant_name: string;
  recorded_collections_paise: number;
  successful_transactions_count: number;
  simulated_rewards_cost_paise?: number;
  text_summary: string;
  voice_script: string;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: any;
    request_id?: string;
  };
}
