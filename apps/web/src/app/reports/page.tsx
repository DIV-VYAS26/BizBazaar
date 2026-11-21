'use client';

import React, { useState, useEffect } from 'react';
import { bizbazaarApi, getApiMode } from '@/lib/api/client';
import {
  Reward,
  CampaignReport,
  DailySummaryResponse,
  Campaign,
} from '@/lib/generated/types';
import { formatPaiseToINR, formatDateKolkata } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  Volume2,
  VolumeX,
  FileSpreadsheet,
  Award,
  PieChart,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Radio,
  RefreshCw,
} from 'lucide-react';

export default function ReportsPage() {
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [totalRewards, setTotalRewards] = useState(0);
  const [campaignReport, setCampaignReport] = useState<CampaignReport | null>(null);
  const [dailySummary, setDailySummary] = useState<DailySummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [summaryLocale, setSummaryLocale] = useState<'en-IN' | 'hi-IN'>('en-IN');

  // Web Speech API state
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        setNotice(null);
        const [rRes, sumRes, camps] = await Promise.allSettled([
          bizbazaarApi.getRewards({ limit: 50, offset: 0 }),
          bizbazaarApi.getDailySummary(summaryLocale),
          bizbazaarApi.listCampaigns(),
        ]);
        if (rRes.status === 'rejected') throw rRes.reason;
        if (camps.status === 'rejected') throw camps.reason;
        setRewards(rRes.value.items);
        setTotalRewards(rRes.value.total);
        setDailySummary(sumRes.status === 'fulfilled' ? sumRes.value : null);
        if (sumRes.status === 'rejected') setNotice(sumRes.reason?.message || 'Daily summary unavailable');

        const activeCamp = camps.value.find((c) => c.status === 'ACTIVE') || camps.value[0];
        if (activeCamp) {
          const cReport = await bizbazaarApi.getCampaignReport(activeCamp.id);
          setCampaignReport(cReport);
        }
      } catch (err: any) {
        setNotice(err?.message || 'Unable to load reports');
      } finally {
        setIsLoading(false);
      }
    }

    loadData();

    if (typeof window !== 'undefined' && !('speechSynthesis' in window)) {
      setSpeechSupported(false);
    }
  }, [summaryLocale]);

  const handlePlayVoice = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setSpeechSupported(false);
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    if (!dailySummary?.voice_script) return;

    window.speechSynthesis.cancel(); // clear previous
    const utterance = new SpeechSynthesisUtterance(dailySummary.voice_script);
    utterance.lang = dailySummary.locale || 'en-IN';
    utterance.rate = 0.95;

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Generating verified audit reports...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {notice && <Alert variant="info" title="Report notice">{notice}</Alert>}
      {/* Page Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Reward Reports & Daily Summary</h1>
            <Badge variant="purple">Simulated Rewards</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Reconciled reward allocations, budget burn rates, and daily audio briefing.
          </p>
        </div>
        {getApiMode() === 'live' && <label className="text-sm">Summary language{' '}
          <select aria-label="Summary language" value={summaryLocale}
            onChange={event => setSummaryLocale(event.target.value as 'en-IN' | 'hi-IN')}
            className="border rounded p-2">
            <option value="en-IN">English</option><option value="hi-IN">हिन्दी</option>
          </select>
        </label>}
      </div>

      {/* Daily AI Briefing & Audio Playback Card */}
      {dailySummary && (
        <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50/60 via-white to-white">
          <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-100 text-emerald-700 rounded-xl">
                <Radio className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <CardTitle className="text-lg text-slate-900">Verified Daily Merchant Briefing</CardTitle>
                <CardDescription>
                  Date: {dailySummary.date} | Merchant: {dailySummary.merchant_name}
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={isSpeaking ? 'danger' : 'primary'}
                size="sm"
                onClick={handlePlayVoice}
                className="gap-2"
              >
                {isSpeaking ? (
                  <>
                    <VolumeX className="w-4 h-4" /> Stop Audio
                  </>
                ) : (
                  <>
                    <Volume2 className="w-4 h-4" /> Listen to Briefing
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-white rounded-xl border border-emerald-100 text-slate-800 text-sm leading-relaxed font-sans shadow-2xs">
              <p className="font-medium">{dailySummary.text_summary}</p>
            </div>

            {!speechSupported && (
              <Alert variant="info" title="Speech Synthesis Notice">
                Web Speech API is unavailable in this environment. The full briefing text is verified and presented above without loss of information.
              </Alert>
            )}

            <div className="text-xs text-slate-500 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                Calculated strictly from non-refunded transactions and verified campaign budgets.
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Campaign Budget & Burn Report */}
      {campaignReport && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <PieChart className="w-5 h-5 text-emerald-600" />
                Active Campaign Budget Utilization
              </CardTitle>
              <Badge variant="success">{campaignReport.status}</Badge>
            </div>
            <CardDescription>
              {campaignReport.campaign_name} ({campaignReport.campaign_type})
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100 mb-4">
              <div>
                <span className="text-xs text-slate-500 block">Total Budget Cap</span>
                <span className="text-xl font-bold text-slate-900">
                  {formatPaiseToINR(campaignReport.budget_cap_paise)}
                </span>
              </div>
              <div>
                <span className="text-xs text-slate-500 block">Spent Budget</span>
                <span className="text-xl font-bold text-emerald-700">
                  {formatPaiseToINR(campaignReport.spent_budget_paise)}
                </span>
              </div>
              <div>
                <span className="text-xs text-slate-500 block">Remaining Budget</span>
                <span
                  className={`text-xl font-bold ${
                    campaignReport.remaining_budget_paise <= 0 ? 'text-rose-600' : 'text-slate-900'
                  }`}
                >
                  {formatPaiseToINR(campaignReport.remaining_budget_paise)}
                </span>
              </div>
              <div>
                <span className="text-xs text-slate-500 block">Utilization</span>
                <span className="text-xl font-bold text-slate-900">
                  {campaignReport.budget_utilization_pct}%
                </span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
              <div
                className="bg-emerald-600 h-full transition-all duration-500 rounded-full"
                style={{ width: `${Math.min(100, campaignReport.budget_utilization_pct)}%` }}
              />
            </div>

            <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
              <span>Total Qualifying Events: {campaignReport.total_qualifying_events}</span>
              <span>Total Rewards Issued: {campaignReport.total_rewards_issued}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rewards Ledger Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-500" />
              Simulated Customer Rewards ({totalRewards})
            </CardTitle>
            <CardDescription>
              Deterministic allocations. Clearly marked as simulated demo rewards.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {rewards.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              No rewards issued yet. Run the Payment Simulator to trigger qualifying payments!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase">
                  <tr>
                    <th className="py-3 px-4">Reward ID</th>
                    <th className="py-3 px-4">Qualifying TXN</th>
                    <th className="py-3 px-4">Recipient VPA</th>
                    <th className="py-3 px-4">Timestamp (IST)</th>
                    <th className="py-3 px-4">Nature</th>
                    <th className="py-3 px-4 text-right">Reward Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {rewards.map((rwd) => (
                    <tr key={rwd.reward_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-900">{rwd.reward_id}</td>
                      <td className="py-3 px-4 text-emerald-700 font-semibold">{rwd.transaction_id}</td>
                      <td className="py-3 px-4 text-slate-500">{rwd.recipient_vpa || '—'}</td>
                      <td className="py-3 px-4 text-slate-600 font-sans">
                        {formatDateKolkata(rwd.created_at)}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="purple">SIMULATED</Badge>
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-emerald-700">
                        {formatPaiseToINR(rwd.amount_paise)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
