'use client';

import React, { useState, useEffect } from 'react';
import { bizbazaarApi } from '@/lib/api/client';
import { AnalyticsResponse, ForecastResponse } from '@/lib/generated/types';
import { formatPaiseToINR } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  TrendingUp,
  Clock,
  QrCode,
  Calendar,
  AlertTriangle,
  HelpCircle,
  Sparkles,
  BarChart3,
  RefreshCw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        const [aData, fData] = await Promise.all([
          bizbazaarApi.getAnalytics(),
          bizbazaarApi.getForecast(),
        ]);
        setAnalytics(aData);
        setForecast(fData);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Aggregating historical analytical trends...</p>
      </div>
    );
  }

  if (!analytics || !forecast) return null;

  // Chart data format
  const chartData = analytics.daily_trends.map((item) => ({
    date: item.date,
    collectionsINR: Math.round(item.successful_amount_paise / 100),
    txnCount: item.successful_count,
  }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Analytical Insights & Forecast</h1>
          <Badge variant="purple">Empirical Trends</Badge>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Observed patterns calculated strictly from verified successful payments. No synthetic margins or fabricated claims.
        </p>
      </div>

      {analytics.insights && analytics.insights.length > 0 && <Alert variant="info" title="Recorded trends">
        <ul>{analytics.insights.map((insight, index) => <li key={index}>{insight}</li>)}</ul>
        {analytics.average_value_decline_percent != null && <p>
          Average payment {analytics.average_value_decline_percent >= 0 ? 'decreased' : 'increased'} by{' '}
          {Math.abs(analytics.average_value_decline_percent)}% between the comparison windows.
        </p>}
      </Alert>}
      {/* Top Level Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none">
            <CardTitle className="text-sm font-medium text-slate-500">Recorded Total Collections</CardTitle>
            <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
              <TrendingUp className="w-5 h-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-extrabold text-slate-900">
              {formatPaiseToINR(analytics.recorded_collections_paise)}
            </div>
            <p className="text-xs text-slate-500 mt-1">Active verified ledger sum</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none">
            <CardTitle className="text-sm font-medium text-slate-500">Peak Order Window</CardTitle>
            <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
              <Clock className="w-5 h-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-extrabold text-slate-900">{analytics.peak_hour}</div>
            <p className="text-xs text-slate-500 mt-1">Highest frequency of incoming customer payments</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-none">
            <CardTitle className="text-sm font-medium text-slate-500">Top Payment Channel</CardTitle>
            <div className="p-2 bg-amber-50 rounded-lg text-amber-600">
              <QrCode className="w-5 h-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold text-slate-900 truncate">{analytics.top_payment_method}</div>
            <p className="text-xs text-slate-500 mt-1">Simulated merchant QR endpoint</p>
          </CardContent>
        </Card>
      </div>

      {/* Daily Recorded Collections Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-emerald-600" />
            Daily Recorded Collections (INR)
          </CardTitle>
          <CardDescription>Visualizing verified collections across recorded active dates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} />
                <YAxis
                  stroke="#64748b"
                  fontSize={12}
                  tickLine={false}
                  tickFormatter={(val) => `₹${val.toLocaleString('en-IN')}`}
                />
                <Tooltip
                  formatter={(val: number) => [`₹${val.toLocaleString('en-IN')}`, 'Collections']}
                  labelFormatter={(lbl) => `Date: ${lbl}`}
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="collectionsINR" fill="#059669" radius={[6, 6, 0, 0]} maxBarSize={60} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Forecast Section - INSUFFICIENT DATA Handling */}
      <Card className="border-slate-300">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              <CardTitle className="text-base font-semibold">Weekday Baseline Forecast</CardTitle>
            </div>
            {forecast.status === 'INSUFFICIENT_DATA' ? (
              <Badge variant="warning">INSUFFICIENT DATA</Badge>
            ) : (
              <Badge variant="success">FORECAST AVAILABLE</Badge>
            )}
          </div>
          <CardDescription>
            Forecasts require 28 complete past days and three observations per predicted weekday.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {forecast.status === 'INSUFFICIENT_DATA' ? (
            <div className="p-6 bg-amber-50/60 rounded-xl border border-amber-200/80 flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <div className="p-3 bg-amber-100 rounded-xl text-amber-700 shrink-0">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h4 className="font-semibold text-amber-900 text-sm">
                  Insufficient Historical Days for Statistical Forecast
                </h4>
                <p className="text-xs text-amber-800 leading-relaxed max-w-2xl">
                  {forecast.message}
                </p>
                <div className="pt-2 flex items-center gap-2 text-xs text-amber-700">
                  <HelpCircle className="w-4 h-4" />
                  <span>
                    Import records and declare coverage for at least 28 complete past days. Missing days stay unknown.
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 bg-emerald-50 rounded-xl border border-emerald-200 space-y-3">
              <h4 className="font-semibold text-emerald-900">7-Day Estimated Collections</h4>
              <div className="text-3xl font-extrabold text-emerald-800">
                {formatPaiseToINR(forecast.projected_next_week_collections_paise)}
              </div>
              <p className="text-xs text-emerald-700">
                {forecast.confidence_interval
                  ? `Prediction interval: ${forecast.confidence_interval}`
                  : 'A calibrated prediction interval is not available.'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
