import { BizBazaarApi } from './types';
import { mockBizBazaarApi } from './mock';
import { liveBizBazaarApi } from './live';

export type ApiMode = 'mock' | 'live';

let currentMode: ApiMode = process.env.NEXT_PUBLIC_DEMO_MODE === 'false' ? 'live' :
  typeof window !== 'undefined' && localStorage.getItem('bizbazaar_api_mode')
    ? (localStorage.getItem('bizbazaar_api_mode') as ApiMode)
    : (process.env.NEXT_PUBLIC_API_MODE as ApiMode) || 'live';

const listeners = new Set<(mode: ApiMode) => void>();

export function getApiMode(): ApiMode {
  return process.env.NEXT_PUBLIC_DEMO_MODE === 'false' ? 'live' : currentMode;
}

export function setApiMode(mode: ApiMode): void {
  currentMode = process.env.NEXT_PUBLIC_DEMO_MODE === 'false' ? 'live' : mode;
  if (typeof window !== 'undefined') {
    localStorage.setItem('bizbazaar_api_mode', mode);
  }
  listeners.forEach((cb) => cb(mode));
}

export function subscribeApiMode(cb: (mode: ApiMode) => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

/**
 * Delegating BizBazaarApi instance that routes calls to either mock or live implementation
 */
export const bizbazaarApi: BizBazaarApi = {
  getHealth: () => (currentMode === 'live' ? liveBizBazaarApi.getHealth() : mockBizBazaarApi.getHealth()),
  getSession: () => (currentMode === 'live' ? liveBizBazaarApi.getSession() : mockBizBazaarApi.getSession()),
  importTransactions: (file: File) =>
    currentMode === 'live' ? liveBizBazaarApi.importTransactions(file) : mockBizBazaarApi.importTransactions(file),
  getTransactions: (params) =>
    currentMode === 'live' ? liveBizBazaarApi.getTransactions(params) : mockBizBazaarApi.getTransactions(params),
  getDashboard: () => (currentMode === 'live' ? liveBizBazaarApi.getDashboard() : mockBizBazaarApi.getDashboard()),
  getAnalytics: () => (currentMode === 'live' ? liveBizBazaarApi.getAnalytics() : mockBizBazaarApi.getAnalytics()),
  getForecast: () => (currentMode === 'live' ? liveBizBazaarApi.getForecast() : mockBizBazaarApi.getForecast()),
  getRecommendation: () =>
    currentMode === 'live' ? liveBizBazaarApi.getRecommendation() : mockBizBazaarApi.getRecommendation(),
  listCampaigns: (status) =>
    currentMode === 'live' ? liveBizBazaarApi.listCampaigns(status) : mockBizBazaarApi.listCampaigns(status),
  getCampaign: (id) => (currentMode === 'live' ? liveBizBazaarApi.getCampaign(id) : mockBizBazaarApi.getCampaign(id)),
  createCampaign: (data) =>
    currentMode === 'live' ? liveBizBazaarApi.createCampaign(data) : mockBizBazaarApi.createCampaign(data),
  approveCampaign: (id) =>
    currentMode === 'live' ? liveBizBazaarApi.approveCampaign(id) : mockBizBazaarApi.approveCampaign(id),
  activateCampaign: (id) =>
    currentMode === 'live' ? liveBizBazaarApi.activateCampaign(id) : mockBizBazaarApi.activateCampaign(id),
  completeCampaign: (id) =>
    currentMode === 'live' ? liveBizBazaarApi.completeCampaign(id) : mockBizBazaarApi.completeCampaign(id),
  simulatePayment: (data) =>
    currentMode === 'live' ? liveBizBazaarApi.simulatePayment(data) : mockBizBazaarApi.simulatePayment(data),
  getRewards: (params) =>
    currentMode === 'live' ? liveBizBazaarApi.getRewards(params) : mockBizBazaarApi.getRewards(params),
  getCampaignReport: (id) =>
    currentMode === 'live' ? liveBizBazaarApi.getCampaignReport(id) : mockBizBazaarApi.getCampaignReport(id),
  getDailySummary: (locale) =>
    currentMode === 'live' ? liveBizBazaarApi.getDailySummary(locale) : mockBizBazaarApi.getDailySummary(),
  resetState: () => mockBizBazaarApi.resetState?.(),
};
