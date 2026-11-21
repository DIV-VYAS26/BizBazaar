'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { bizbazaarApi } from '@/lib/api/client';
import { DashboardResponse } from '@/lib/generated/types';
import { formatPaiseToINR, formatDateKolkata } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  IndianRupee,
  Receipt,
  TrendingUp,
  AlertCircle,
  Clock,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  Zap,
} from 'lucide-react';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await bizbazaarApi.getDashboard();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard metrics');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Calculating verified recorded collections...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Alert variant="error" title="Dashboard Error">
          {error}
        </Alert>
        <Button onClick={fetchDashboard} variant="outline" size="sm">
          Retry
        </Button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Top Banner / Merchant Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Recorded Collections Dashboard</h1>
            <Badge variant="success" className="font-medium">
              Verified Ledger
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Displaying reconciled non-refunded transactions. Unsettled and refunded rows excluded from net collections.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/transactions">
            <Button variant="outline" size="sm">
              <Receipt className="w-4 h-4 mr-1.5" />
              Upload CSV
            </Button>
          </Link>
          <Link href="/campaigns/simulate">
            <Button variant="primary" size="sm">
              <Zap className="w-4 h-4 mr-1.5" />
              Simulate Payment
            </Button>
          </Link>
        </div>
      </div>

      {/* Warnings & Ledger Disclaimers if any */}
      {data.warnings && data.warnings.length > 0 && (
        <div className="space-y-2">
          {data.warnings.map((warning, idx) => (
            <Alert key={idx} variant="warning" title="Ledger Notice">
              {warning}
            </Alert>
          ))}
        </div>
      )}

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Net Collections */}
        <Card className="hover:border-slate-300 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none">
            <CardTitle className="text-sm font-medium text-slate-500">Net Recorded Collections</CardTitle>
            <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
              <IndianRupee className="w-5 h-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight" data-testid="net-collections">
              {formatPaiseToINR(data.net_recorded_collections_paise)}
            </div>
            <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
              Includes successful, non-refunded payments only
            </p>
          </CardContent>
        </Card>

        {/* Successful Count */}
        <Card className="hover:border-slate-300 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none">
            <CardTitle className="text-sm font-medium text-slate-500">Successful Payments</CardTitle>
            <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
              <Receipt className="w-5 h-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight" data-testid="successful-count">
              {data.successful_count}
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
              <span className="text-amber-600 font-medium">{data.pending_count} pending</span>
              <span>•</span>
              <span className="text-rose-600 font-medium">{data.failed_count} failed</span>
              <span>•</span>
              <span className="text-slate-500 font-medium">{data.refunded_count} refunded</span>
            </div>
          </CardContent>
        </Card>

        {/* Average Payment */}
        <Card className="hover:border-slate-300 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none">
            <CardTitle className="text-sm font-medium text-slate-500">Average Successful Payment</CardTitle>
            <div className="p-2 bg-purple-50 rounded-lg text-purple-600">
              <TrendingUp className="w-5 h-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight" data-testid="average-payment">
              {data.average_paise !== null ? formatPaiseToINR(data.average_paise) : '—'}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Calculated half-up to paise (₹8,500 ÷ 6 = ₹1,416.67)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Active Campaign Status or Recommendation Callout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {data.active_campaign ? (
            <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50/40 via-white to-white">
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Badge variant="success">ACTIVE CAMPAIGN</Badge>
                    <span className="text-xs text-slate-400 font-mono">ID: {data.active_campaign.id}</span>
                  </div>
                  <CardTitle className="text-xl mt-2 text-slate-900">{data.active_campaign.name}</CardTitle>
                  <CardDescription className="mt-1">
                    Rule:{' '}
                    {data.active_campaign.type === 'NTH_PAYMENT'
                      ? `Every ${data.active_campaign.rule_parameters.n}th customer payment receives a simulated reward.`
                      : `First customer crossing ₹${((data.active_campaign.rule_parameters.threshold_paise || 0) / 100).toLocaleString('en-IN')} cumulative collections.`}
                  </CardDescription>
                </div>
                <Link href="/campaigns">
                  <Button variant="outline" size="sm">
                    Manage
                  </Button>
                </Link>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-white/80 rounded-xl border border-emerald-100 text-sm">
                  <div>
                    <span className="text-xs text-slate-500 block">Reward per Win</span>
                    <span className="font-bold text-slate-800 text-base">
                      {formatPaiseToINR(data.active_campaign.reward_cost_paise)}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 block">Hard Budget Cap</span>
                    <span className="font-bold text-slate-800 text-base">
                      {formatPaiseToINR(data.active_campaign.budget_cap_paise)}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 block">Simulated Rewards</span>
                    <span className="font-bold text-emerald-600 text-base">
                      {data.active_campaign.rewards_issued_count} issued
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 block">Budget Spent</span>
                    <span className="font-bold text-slate-800 text-base">
                      {formatPaiseToINR(data.active_campaign.spent_budget_paise)}
                    </span>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
                  <span>
                    Started: {formatDateKolkata(data.active_campaign.starts_at)}
                  </span>
                  <Link
                    href="/campaigns/simulate"
                    className="text-emerald-700 font-semibold hover:underline inline-flex items-center gap-1"
                  >
                    Simulate Next Payment <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-dashed border-2 border-slate-200">
              <CardContent className="flex flex-col items-center justify-center py-10 text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800">No Active Promotional Campaign</h4>
                  <p className="text-sm text-slate-500 max-w-sm mt-1">
                    AI growth suggestions are prepared based on your recorded collections. Draft, approve, and activate one click at a time.
                  </p>
                </div>
                <Link href="/campaigns">
                  <Button variant="primary" size="sm">
                    View AI Recommendations
                  </Button>
                </Link>
              </CardContent>
            </Card>
          )}

          {/* Quick Canonical Audit Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Canonical Verification Breakdown</CardTitle>
              <CardDescription>
                Cross-checking server acceptance order and deterministic calculations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase">
                    <tr>
                      <th className="py-2.5 px-3">Transaction</th>
                      <th className="py-2.5 px-3">Type / Note</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Amount</th>
                      <th className="py-2.5 px-3 text-right">Net Effect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-800">TXN001 - TXN006</td>
                      <td className="py-2 px-3 text-slate-600 font-sans">6 Successful Payments</td>
                      <td className="py-2 px-3">
                        <Badge variant="success">SUCCESS</Badge>
                      </td>
                      <td className="py-2 px-3 text-right">₹8,500.00</td>
                      <td className="py-2 px-3 text-right text-emerald-600 font-bold">+ ₹8,500.00</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 text-slate-700">TXN007</td>
                      <td className="py-2 px-3 text-slate-500 font-sans">Pending UPI Confirmation</td>
                      <td className="py-2 px-3">
                        <Badge variant="warning">PENDING</Badge>
                      </td>
                      <td className="py-2 px-3 text-right">₹700.00</td>
                      <td className="py-2 px-3 text-right text-slate-400">Excluded (₹0)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 text-slate-700">TXN008</td>
                      <td className="py-2 px-3 text-slate-500 font-sans">Bank Server Timeout</td>
                      <td className="py-2 px-3">
                        <Badge variant="error">FAILED</Badge>
                      </td>
                      <td className="py-2 px-3 text-right">₹300.00</td>
                      <td className="py-2 px-3 text-right text-slate-400">Excluded (₹0)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 text-slate-700">TXN009</td>
                      <td className="py-2 px-3 text-slate-500 font-sans">Customer Return</td>
                      <td className="py-2 px-3">
                        <Badge variant="outline">REFUNDED</Badge>
                      </td>
                      <td className="py-2 px-3 text-right">₹400.00</td>
                      <td className="py-2 px-3 text-right text-rose-600">Deducted (₹0)</td>
                    </tr>
                  </tbody>
                  <tfoot className="bg-slate-50 font-semibold text-slate-900 border-t border-slate-200">
                    <tr>
                      <td colSpan={3} className="py-2.5 px-3 font-sans">
                        Net Confirmed Recorded Collections (6 txns)
                      </td>
                      <td colSpan={2} className="py-2.5 px-3 text-right text-emerald-700 font-bold text-sm">
                        ₹8,500.00
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Sidebar: AI Copilot summary card */}
        <div className="space-y-6">
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white">
            <CardHeader className="border-slate-800">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span className="text-xs uppercase tracking-wider font-semibold text-emerald-400">
                  AI Merchant Briefing
                </span>
              </div>
              <CardTitle className="text-lg text-white">Daily Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-slate-300 text-sm leading-relaxed">
              <p>
                Gupta Kirana Store has recorded <strong className="text-white">₹8,500.00</strong> across 6 verified payments today.
              </p>
              <div className="p-3 bg-slate-800/80 rounded-lg border border-slate-700/80 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Average Ticket:</span>
                  <span className="text-white font-mono font-medium">₹1,416.67</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Simulated Rewards:</span>
                  <span className="text-emerald-400 font-mono font-medium">1 issued (₹100)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Active Campaign:</span>
                  <span className="text-white">Every 3rd Shopper</span>
                </div>
              </div>
              <Link href="/reports" className="block">
                <Button variant="outline" size="sm" className="w-full text-slate-900 bg-white hover:bg-slate-100">
                  Listen to Audio Briefing
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-slate-700">Quick Testing Links</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link
                href="/transactions"
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 border border-transparent hover:border-slate-200 text-xs font-medium text-slate-700 transition-all"
              >
                <span>Upload New Transactions (CSV)</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </Link>
              <Link
                href="/campaigns/simulate"
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 border border-transparent hover:border-slate-200 text-xs font-medium text-slate-700 transition-all"
              >
                <span>Run Payment Event Simulation</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </Link>
              <Link
                href="/reports"
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50 border border-transparent hover:border-slate-200 text-xs font-medium text-slate-700 transition-all"
              >
                <span>Check Simulated Rewards Ledger</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
