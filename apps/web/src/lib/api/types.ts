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
  RewardListResponse,
  CampaignReport,
  DailySummaryResponse,
  TransactionStatus,
  CampaignStatus,
} from '../generated/types';

export interface BizBazaarApi {
  getHealth(): Promise<HealthResponse>;
  getSession(): Promise<MerchantSession>;
  importTransactions(file: File): Promise<TransactionImportReport>;
  getTransactions(params?: { status?: TransactionStatus; limit?: number; offset?: number }): Promise<TransactionListResponse>;
  getDashboard(): Promise<DashboardResponse>;
  getAnalytics(): Promise<AnalyticsResponse>;
  getForecast(): Promise<ForecastResponse>;
  getRecommendation(): Promise<RecommendationResponse>;
  listCampaigns(status?: CampaignStatus): Promise<Campaign[]>;
  getCampaign(id: string): Promise<Campaign>;
  createCampaign(data: CreateCampaignRequest): Promise<Campaign>;
  approveCampaign(id: string): Promise<Campaign>;
  activateCampaign(id: string): Promise<Campaign>;
  completeCampaign(id: string): Promise<Campaign>;
  simulatePayment(data: SimulatePaymentRequest): Promise<SimulatePaymentResponse>;
  getRewards(params?: { limit?: number; offset?: number }): Promise<RewardListResponse>;
  getCampaignReport(id: string): Promise<CampaignReport>;
  getDailySummary(locale?: 'en-IN' | 'hi-IN'): Promise<DailySummaryResponse>;
  // Reset mock state helper (useful for demo & tests)
  resetState?(): void;
}
