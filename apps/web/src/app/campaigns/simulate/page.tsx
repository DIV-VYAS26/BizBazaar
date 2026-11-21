'use client';

import React, { useState, useEffect } from 'react';
import { bizbazaarApi, getApiMode } from '@/lib/api/client';
import {
  SimulatePaymentResponse,
  Campaign,
  SimulatePaymentRequest,
} from '@/lib/generated/types';
import { formatPaiseToINR, formatDateKolkata } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Zap,
  Play,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Layers,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

export default function SimulatePage() {
  const [activeCampaign, setActiveCampaign] = useState<Campaign | null>(null);
  const [txnId, setTxnId] = useState('TXN_CUSTOM_01');
  const [amountRupees, setAmountRupees] = useState(1500);
  const [customerVpa, setCustomerVpa] = useState('shopper@upi');

  const [simulationLog, setSimulationLog] = useState<SimulatePaymentResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  const fetchActiveCampaign = async () => {
    try {
      const camps = await bizbazaarApi.listCampaigns();
      const active = camps.find((c) => c.status === 'ACTIVE') || null;
      setActiveCampaign(active);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchActiveCampaign();
  }, []);

  const runSimulation = async (req: SimulatePaymentRequest) => {
    try {
      setIsLoading(true);
      setErrorNotice(null);
      const res = await bizbazaarApi.simulatePayment(req);
      setSimulationLog((prev) => [res, ...prev]);
      await fetchActiveCampaign();
    } catch (err: any) {
      setErrorNotice(err?.message || 'Simulation execution failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runSimulation({
      transaction_id: txnId,
      amount_paise: Math.round(Number(amountRupees) * 100),
      timestamp: new Date().toISOString(),
      customer_vpa: customerVpa,
    });
  };

  // Canonical preset runners
  const runPreset = (id: string, amountPaise: number, vpa: string) => {
    runSimulation({
      transaction_id: id,
      amount_paise: amountPaise,
      timestamp: new Date().toISOString(),
      customer_vpa: vpa,
    });
  };

  const decisionBadge = (decision: SimulatePaymentResponse['decision']) => {
    switch (decision) {
      case 'ISSUED':
        return <Badge variant="success">REWARD ISSUED</Badge>;
      case 'SKIPPED_BUDGET':
        return <Badge variant="warning">SKIPPED (BUDGET CAP)</Badge>;
      case 'NOT_QUALIFIED':
        return <Badge variant="default">NOT QUALIFIED</Badge>;
      case 'NO_ACTIVE_CAMPAIGN':
        return <Badge variant="error">NO ACTIVE CAMPAIGN</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Payment Event Simulator</h1>
            <Badge variant="purple">Deterministic Engine</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Simulate confirmed incoming payments in server acceptance order. Validates Nth payment logic, threshold milestones, budget caps, and replay idempotency.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeCampaign ? (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded-lg flex items-center gap-2 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Active: {activeCampaign.name}</span>
            </div>
          ) : (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-1.5 rounded-lg flex items-center gap-2 font-medium">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              <span>No Active Campaign (Will Record as Unpromoted)</span>
            </div>
          )}
        </div>
      </div>

      {errorNotice && (
        <Alert variant="error" title="Simulation Exception">
          {errorNotice}
        </Alert>
      )}

      {/* Canonical Fixture Stepper */}
      <Card className="border-emerald-200 bg-gradient-to-r from-emerald-50/40 via-white to-white">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-emerald-600" />
              <CardTitle className="text-base font-semibold">Canonical Verification Stepper</CardTitle>
            </div>
            <Badge variant="outline">Specification Flow</Badge>
          </div>
          <CardDescription>
            One-click dispatch of the 6 canonical fixture events in exact server acceptance order:
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <button
              onClick={() => runPreset('TXN001', 100000, 'customer1@okaxis')}
              disabled={isLoading}
              className="p-3 bg-white border border-slate-200 rounded-xl hover:border-emerald-400 text-left transition-all group"
            >
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>#1</span>
                <Play className="w-3 h-3 text-slate-400 group-hover:text-emerald-600" />
              </div>
              <p className="font-bold text-slate-900 font-mono text-xs mt-1">TXN001</p>
              <p className="text-xs text-slate-500 font-sans">₹1,000</p>
              <span className="text-[10px] text-slate-400 block mt-1">Expect: Not Qualified</span>
            </button>

            <button
              onClick={() => runPreset('TXN002', 150000, 'customer2@oksbi')}
              disabled={isLoading}
              className="p-3 bg-white border border-slate-200 rounded-xl hover:border-emerald-400 text-left transition-all group"
            >
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>#2</span>
                <Play className="w-3 h-3 text-slate-400 group-hover:text-emerald-600" />
              </div>
              <p className="font-bold text-slate-900 font-mono text-xs mt-1">TXN002</p>
              <p className="text-xs text-slate-500 font-sans">₹1,500</p>
              <span className="text-[10px] text-slate-400 block mt-1">Expect: Not Qualified</span>
            </button>

            <button
              onClick={() => runPreset('TXN003', 200000, 'customer3@okhdfc')}
              disabled={isLoading}
              className="p-3 bg-white border-2 border-emerald-400 bg-emerald-50/30 rounded-xl hover:bg-emerald-50 text-left transition-all group"
            >
              <div className="flex justify-between items-center text-xs text-emerald-600 font-bold">
                <span>#3 (N=3)</span>
                <Play className="w-3 h-3 text-emerald-600" />
              </div>
              <p className="font-bold text-slate-900 font-mono text-xs mt-1">TXN003</p>
              <p className="text-xs text-slate-600 font-sans">₹2,000</p>
              <span className="text-[10px] text-emerald-700 font-semibold block mt-1">
                Expect: ₹100 ISSUED
              </span>
            </button>

            <button
              onClick={() => runPreset('TXN004', 250000, 'customer4@demo')}
              disabled={isLoading}
              className="p-3 bg-white border border-slate-200 rounded-xl hover:border-emerald-400 text-left transition-all group"
            >
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>#4</span>
                <Play className="w-3 h-3 text-slate-400 group-hover:text-emerald-600" />
              </div>
              <p className="font-bold text-slate-900 font-mono text-xs mt-1">TXN004</p>
              <p className="text-xs text-slate-500 font-sans">₹2,500</p>
              <span className="text-[10px] text-slate-400 block mt-1">Expect: Not Qualified</span>
            </button>

            <button
              onClick={() => runPreset('TXN005', 100000, 'customer5@okicici')}
              disabled={isLoading}
              className="p-3 bg-white border border-slate-200 rounded-xl hover:border-emerald-400 text-left transition-all group"
            >
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>#5 (Milestone)</span>
                <Play className="w-3 h-3 text-slate-400 group-hover:text-emerald-600" />
              </div>
              <p className="font-bold text-slate-900 font-mono text-xs mt-1">TXN005</p>
              <p className="text-xs text-slate-500 font-sans">₹1,000</p>
              <span className="text-[10px] text-purple-600 font-medium block mt-1">
                Reaches ₹8,000
              </span>
            </button>

            <button
              onClick={() => runPreset('TXN006', 50000, 'customer6@upi')}
              disabled={isLoading}
              className="p-3 bg-white border border-amber-300 bg-amber-50/30 rounded-xl hover:bg-amber-50 text-left transition-all group"
            >
              <div className="flex justify-between items-center text-xs text-amber-600 font-bold">
                <span>#6 (N=3)</span>
                <Play className="w-3 h-3 text-amber-600" />
              </div>
              <p className="font-bold text-slate-900 font-mono text-xs mt-1">TXN006</p>
              <p className="text-xs text-slate-600 font-sans">₹500</p>
              <span className="text-[10px] text-amber-700 font-semibold block mt-1">
                Expect: SKIPPED (Cap)
              </span>
            </button>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1.5 font-medium">
              <ShieldAlert className="w-4 h-4 text-emerald-600" />
              Idempotency Tests:
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => runPreset('TXN003', 200000, 'customer3@okhdfc')}
                className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-mono font-medium transition-colors"
              >
                Replay TXN003 (Identical Repeat)
              </button>
              <button
                onClick={() => runPreset('TXN003', 99900, 'customer3@okhdfc')}
                className="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg font-mono font-medium transition-colors"
              >
                Conflict TXN003 (₹999 Repeat → Expect 409)
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Custom Simulation Form and Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Custom Form */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Custom Transaction Event</CardTitle>
            <CardDescription>Dispatch arbitrary simulated payments</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCustomSubmit} className="space-y-4">
              <Input
                label="Transaction ID"
                value={txnId}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTxnId(e.target.value)}
                required
              />
              <Input
                label="Amount (in ₹ Rupees)"
                type="number"
                min="1"
                value={amountRupees}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAmountRupees(Number(e.target.value))}
                required
              />
              <Input
                label="Customer UPI VPA"
                value={customerVpa}
                disabled={getApiMode() === 'live'}
                helperText={getApiMode() === 'live' ? 'Customer contact details are not collected by the live simulator.' : undefined}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCustomerVpa(e.target.value)}
              />
              <Button type="submit" variant="primary" className="w-full" isLoading={isLoading}>
                <Zap className="w-4 h-4 mr-1.5" />
                Simulate Payment Event
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Live Simulation Feed */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Layers className="w-5 h-5 text-emerald-600" />
                Simulation Outcome Feed ({simulationLog.length})
              </CardTitle>
              <CardDescription>Real-time results emitted by deterministic rule evaluator</CardDescription>
            </div>
            {simulationLog.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setSimulationLog([])}>
                Clear Feed
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {simulationLog.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No payment events simulated in this session yet. Click any button in the Canonical Stepper above to test.
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {simulationLog.map((log, index) => (
                  <div
                    key={index}
                    className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2 font-mono">
                        <span className="font-bold text-slate-900">{log.transaction_id}</span>
                        <span className="text-slate-400">• Order #{log.current_counter}</span>
                        {log.is_replay && (
                          <Badge variant="purple" className="text-[10px]">
                            IDEMPOTENT REPLAY
                          </Badge>
                        )}
                      </div>
                      <div>{decisionBadge(log.decision)}</div>
                    </div>

                    <p className="text-slate-600 text-xs leading-relaxed font-sans">{log.message}</p>

                    <div className="flex items-center gap-4 pt-1 border-t border-slate-100 text-[11px] text-slate-500 font-mono">
                      <span>
                        Reward:{' '}
                        <strong className="text-emerald-700">
                          {formatPaiseToINR(log.reward_issued_paise)}
                        </strong>
                      </span>
                      <span>
                        Remaining Budget:{' '}
                        <strong className="text-slate-800">
                          {formatPaiseToINR(log.remaining_budget_paise)}
                        </strong>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
