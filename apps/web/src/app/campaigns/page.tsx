'use client';

import React, { useState, useEffect } from 'react';
import { bizbazaarApi } from '@/lib/api/client';
import {
  Campaign,
  RecommendationResponse,
  CampaignType,
  CreateCampaignRequest,
} from '@/lib/generated/types';
import { formatPaiseToINR, formatDateKolkata } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import {
  Sparkles,
  PlusCircle,
  ShieldCheck,
  CheckCircle,
  PlayCircle,
  StopCircle,
  AlertTriangle,
  Info,
  Calendar,
  Gift,
  HelpCircle,
  RefreshCw,
} from 'lucide-react';

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);
  const [recommendationNotice, setRecommendationNotice] = useState<string | null>(null);

  // Modals state
  const [isDraftModalOpen, setIsDraftModalOpen] = useState(false);
  const [selectedCampaignForAction, setSelectedCampaignForAction] = useState<{
    campaign: Campaign;
    action: 'APPROVE' | 'ACTIVATE' | 'COMPLETE';
  } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Draft form state
  const [formName, setFormName] = useState('Every 3rd Shopper Reward');
  const [formType, setFormType] = useState<CampaignType>('NTH_PAYMENT');
  const [formN, setFormN] = useState<number>(3);
  const [formThresholdRupees, setFormThresholdRupees] = useState<number>(8000);
  const [formRewardRupees, setFormRewardRupees] = useState<number>(100);
  const [formBudgetCapRupees, setFormBudgetCapRupees] = useState<number>(100);
  const [formStartsAt, setFormStartsAt] = useState(() => new Date(Date.now() - 60_000).toISOString());
  const [formEndsAt, setFormEndsAt] = useState(() => new Date(Date.now() + 86_400_000).toISOString());

  const loadData = async () => {
    try {
      setIsLoading(true);
      setActionError(null);
      const [allCamps, rec] = await Promise.allSettled([
        bizbazaarApi.listCampaigns(),
        bizbazaarApi.getRecommendation(),
      ]);
      if (allCamps.status === 'rejected') throw allCamps.reason;
      setCampaigns(allCamps.value);
      setRecommendation(rec.status === 'fulfilled' ? rec.value : null);
      setRecommendationNotice(rec.status === 'rejected' ? rec.reason?.message || 'Recommendation unavailable' : null);
    } catch (err: any) {
      setActionError(err?.message || 'Failed to load campaigns');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApplyRecommendation = (rec: RecommendationResponse) => {
    setFormName(rec.title);
    setFormType(rec.campaign_type);
    if (rec.suggested_rule_parameters.n) {
      setFormN(rec.suggested_rule_parameters.n);
    }
    if (rec.suggested_rule_parameters.threshold_paise) {
      setFormThresholdRupees(rec.suggested_rule_parameters.threshold_paise / 100);
    }
    setFormRewardRupees(rec.suggested_reward_cost_paise / 100);
    setFormBudgetCapRupees(rec.suggested_budget_cap_paise / 100);
    if (rec.suggested_starts_at) setFormStartsAt(rec.suggested_starts_at);
    if (rec.suggested_ends_at) setFormEndsAt(rec.suggested_ends_at);
    setIsDraftModalOpen(true);
  };

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      setActionError(null);

      const payload: CreateCampaignRequest = {
        name: formName,
        type: formType,
        rule_parameters:
          formType === 'NTH_PAYMENT' ? { n: Number(formN) } : { threshold_paise: Number(formThresholdRupees) * 100 },
        reward_cost_paise: Math.round(Number(formRewardRupees) * 100),
        budget_cap_paise: Math.round(Number(formBudgetCapRupees) * 100),
        starts_at: formStartsAt,
        ends_at: formEndsAt,
      };

      await bizbazaarApi.createCampaign(payload);
      setIsDraftModalOpen(false);
      await loadData();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to create campaign draft');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExecuteAction = async () => {
    if (!selectedCampaignForAction) return;
    const { campaign, action } = selectedCampaignForAction;

    try {
      setIsSubmitting(true);
      setActionError(null);

      if (action === 'APPROVE') {
        await bizbazaarApi.approveCampaign(campaign.id);
      } else if (action === 'ACTIVATE') {
        await bizbazaarApi.activateCampaign(campaign.id);
      } else if (action === 'COMPLETE') {
        await bizbazaarApi.completeCampaign(campaign.id);
      }

      setSelectedCampaignForAction(null);
      await loadData();
    } catch (err: any) {
      setActionError(err?.message || `Failed to execute ${action}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const hasActiveCampaign = campaigns.some((c) => c.status === 'ACTIVE');

  return (
    <div className="space-y-6">
      {recommendationNotice && <Alert variant="info" title="Recommendation unavailable">
        {recommendationNotice} You can still create and approve a campaign manually.
      </Alert>}
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Promotional Campaigns & Rules</h1>
          <p className="text-sm text-slate-500 mt-1">
            Deterministic, budget-capped rewards. <strong>Merchant explicit 2-step approval & activation required</strong> before any campaign can go live.
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={() => setIsDraftModalOpen(true)}>
          <PlusCircle className="w-4 h-4 mr-1.5" />
          Create Campaign Draft
        </Button>
      </div>

      {actionError && (
        <Alert variant="error" title="Campaign Action Notice">
          {actionError}
        </Alert>
      )}

      {/* AI Recommendation Banner */}
      {recommendation && (
        <Card className="border-purple-200 bg-gradient-to-r from-purple-50/70 via-indigo-50/30 to-white">
          <CardHeader className="flex flex-col sm:flex-row sm:items-start justify-between pb-3">
            <div className="flex items-start gap-3">
              <div className="p-2.5 bg-purple-100 text-purple-700 rounded-xl mt-0.5">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <Badge variant="purple">{recommendation.generation_mode === 'DETERMINISTIC_FALLBACK'
                    ? 'Configured recommendation' : 'AI RECOMMENDATION'}</Badge>
                  <span className="text-xs text-slate-500 font-mono">Based on configured rules and recorded data</span>
                </div>
                <CardTitle className="text-lg mt-1 text-slate-900">{recommendation.title}</CardTitle>
                <CardDescription className="mt-1 text-slate-600 max-w-2xl leading-relaxed">
                  {recommendation.rationale}
                </CardDescription>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="mt-3 sm:mt-0 border-purple-300 text-purple-700 hover:bg-purple-50"
              onClick={() => handleApplyRecommendation(recommendation)}
            >
              Use This Template
            </Button>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex flex-wrap gap-4 text-xs font-medium text-slate-700 bg-white/80 p-3 rounded-lg border border-purple-100">
              <div>
                <span className="text-slate-400 block text-[11px]">Rule Trigger:</span>
                <span>{recommendation.campaign_type === 'NTH_PAYMENT'
                  ? `Every ${recommendation.suggested_rule_parameters.n}th eligible payment`
                  : `First crossing of ${formatPaiseToINR(recommendation.suggested_rule_parameters.threshold_paise)}`}</span>
              </div>
              <div className="w-px bg-slate-200 h-6 my-auto" />
              <div>
                <span className="text-slate-400 block text-[11px]">Reward per Winner:</span>
                <span className="font-bold text-slate-900">
                  {formatPaiseToINR(recommendation.suggested_reward_cost_paise)}
                </span>
              </div>
              <div className="w-px bg-slate-200 h-6 my-auto" />
              <div>
                <span className="text-slate-400 block text-[11px]">Strict Total Budget:</span>
                <span className="font-bold text-purple-700">
                  {formatPaiseToINR(recommendation.suggested_budget_cap_paise)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Campaigns List */}
      <Card>
        <CardHeader>
          <CardTitle>Merchant Campaign Registry</CardTitle>
          <CardDescription>
            Lifecycle:{' '}
            <code className="text-xs bg-slate-100 px-1 py-0.5 rounded font-mono text-slate-700">
              DRAFT → [Merchant Approves] → APPROVED → [Merchant Activates] → ACTIVE → COMPLETED
            </code>
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-12 flex justify-center items-center">
              <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
            </div>
          ) : campaigns.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              No campaigns created yet. Click "Create Campaign Draft" above to begin.
            </div>
          ) : (
            <div className="space-y-4">
              {campaigns.map((cmp) => {
                const remaining = cmp.budget_cap_paise - cmp.spent_budget_paise;
                return (
                  <div
                    key={cmp.id}
                    className="p-5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-all space-y-4"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 text-base">{cmp.name}</span>
                          <span className="font-mono text-xs text-slate-400">({cmp.id})</span>
                          {cmp.status === 'DRAFT' && <Badge variant="default">DRAFT</Badge>}
                          {cmp.status === 'APPROVED' && <Badge variant="info">APPROVED</Badge>}
                          {cmp.status === 'ACTIVE' && <Badge variant="success">ACTIVE</Badge>}
                          {cmp.status === 'COMPLETED' && <Badge variant="outline">COMPLETED</Badge>}
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          Type: <strong className="text-slate-700">{cmp.type}</strong> | Rule:{' '}
                          {cmp.type === 'NTH_PAYMENT'
                            ? `Every ${cmp.rule_parameters.n}th customer payment`
                            : `Reach threshold of ₹${((cmp.rule_parameters.threshold_paise || 0) / 100).toLocaleString('en-IN')}`}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          Starts: {formatDateKolkata(cmp.starts_at)} | Ends: {formatDateKolkata(cmp.ends_at)}
                        </p>
                      </div>

                      {/* State transition buttons */}
                      <div className="flex items-center gap-2">
                        {cmp.status === 'DRAFT' && (
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() =>
                              setSelectedCampaignForAction({ campaign: cmp, action: 'APPROVE' })
                            }
                          >
                            <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
                            Approve Terms
                          </Button>
                        )}

                        {cmp.status === 'APPROVED' && (
                          <Button
                            variant="success"
                            size="sm"
                            disabled={hasActiveCampaign}
                            title={
                              hasActiveCampaign
                                ? 'Another campaign is currently ACTIVE. Complete it first.'
                                : 'Explicit merchant activation'
                            }
                            onClick={() =>
                              setSelectedCampaignForAction({ campaign: cmp, action: 'ACTIVATE' })
                            }
                          >
                            <PlayCircle className="w-3.5 h-3.5 mr-1.5" />
                            Activate Campaign
                          </Button>
                        )}

                        {cmp.status === 'ACTIVE' && (
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() =>
                              setSelectedCampaignForAction({ campaign: cmp, action: 'COMPLETE' })
                            }
                          >
                            <StopCircle className="w-3.5 h-3.5 mr-1.5" />
                            End Campaign
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Stats pills */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs">
                      <div>
                        <span className="text-slate-400 block">Reward per Win:</span>
                        <span className="font-semibold text-slate-800">
                          {formatPaiseToINR(cmp.reward_cost_paise)}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">Hard Budget Cap:</span>
                        <span className="font-semibold text-slate-800">
                          {formatPaiseToINR(cmp.budget_cap_paise)}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">Rewards Issued:</span>
                        <span className="font-semibold text-emerald-600">
                          {cmp.rewards_issued_count} simulated
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">Remaining Budget:</span>
                        <span
                          className={`font-semibold ${
                            remaining <= 0 ? 'text-rose-600' : 'text-slate-800'
                          }`}
                        >
                          {formatPaiseToINR(remaining)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Draft Modal */}
      <Modal
        isOpen={isDraftModalOpen}
        onClose={() => setIsDraftModalOpen(false)}
        title="Create New Campaign Draft"
        description="Draft will not trigger customer rewards until explicitly approved and activated."
        maxWidth="lg"
      >
        <form onSubmit={handleCreateDraft} className="space-y-4">
          <Input
            label="Campaign Name"
            value={formName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormName(e.target.value)}
            required
          />

          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700">Campaign Rule Type</label>
            <select
              value={formType}
              onChange={(e) => setFormType(e.target.value as CampaignType)}
              className="flex h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="NTH_PAYMENT">Nth Payment (e.g. Every Nth customer)</option>
              <option value="COLLECTION_THRESHOLD">Collection Threshold (First event crossing ₹X)</option>
            </select>
          </div>

          {formType === 'NTH_PAYMENT' ? (
            <Input
              label="Every Nth Payment (N)"
              type="number"
              min="1"
              value={formN}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormN(Number(e.target.value))}
              helperText="E.g. N=3 rewards the 3rd, 6th, 9th eligible payments"
              required
            />
          ) : (
            <Input
              label="Threshold Amount (in ₹ Rupees)"
              type="number"
              min="1"
              value={formThresholdRupees}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormThresholdRupees(Number(e.target.value))}
              helperText="E.g. ₹8,000 grants a single reward to the shopper whose payment reaches ₹8,000"
              required
            />
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Simulated Reward (in ₹ Rupees)"
              type="number"
              min="1"
              value={formRewardRupees}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormRewardRupees(Number(e.target.value))}
              helperText="E.g. ₹100 per eligible customer"
              required
            />
            <Input
              label="Hard Budget Cap (in ₹ Rupees)"
              type="number"
              min="1"
              value={formBudgetCapRupees}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormBudgetCapRupees(Number(e.target.value))}
              helperText="E.g. ₹100 max merchant expense"
              required
            />
          </div>

          <Input label="Starts at (ISO timestamp)" value={formStartsAt}
            onChange={event => setFormStartsAt(event.target.value)} required />
          <Input label="Ends at (ISO timestamp)" value={formEndsAt}
            onChange={event => setFormEndsAt(event.target.value)} required />
          <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800">
            <strong>Merchant Policy:</strong> Initial creation creates a <strong>DRAFT</strong>. You must explicitly review terms, click Approve, and then click Activate to accept simulation events.
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsDraftModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Save Draft
            </Button>
          </div>
        </form>
      </Modal>

      {/* Explicit Confirmation Modal for Approve / Activate / Complete */}
      {selectedCampaignForAction && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedCampaignForAction(null)}
          title={
            selectedCampaignForAction.action === 'APPROVE'
              ? 'Merchant Approval Confirmation'
              : selectedCampaignForAction.action === 'ACTIVATE'
              ? 'Merchant Campaign Activation'
              : 'End Active Campaign'
          }
          description={`Campaign: ${selectedCampaignForAction.campaign.name}`}
        >
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Campaign window: {formatDateKolkata(selectedCampaignForAction.campaign.starts_at)}
              {' '}to {formatDateKolkata(selectedCampaignForAction.campaign.ends_at)}.
            </p>
            {selectedCampaignForAction.action === 'APPROVE' && (
              <div className="space-y-3 text-sm text-slate-600">
                <p>
                  By approving, you verify that the promotional terms, reward value (
                  <strong>{formatPaiseToINR(selectedCampaignForAction.campaign.reward_cost_paise)}</strong>
                  ), and maximum budget cap (
                  <strong>{formatPaiseToINR(selectedCampaignForAction.campaign.budget_cap_paise)}</strong>
                  ) match your business intentions.
                </p>
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
                  <strong>Notice:</strong> Approval changes status to <strong>APPROVED</strong>. You will still have a separate activation step to start live payment simulation.
                </div>
              </div>
            )}

            {selectedCampaignForAction.action === 'ACTIVATE' && (
              <div className="space-y-3 text-sm text-slate-600">
                <p>
                  You are about to activate <strong>{selectedCampaignForAction.campaign.name}</strong>.
                  New simulated incoming payments will immediately be checked against this campaign's deterministic rules.
                </p>
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800">
                  <strong>Constraint Check:</strong> No other campaign can be active simultaneously. Counter resets to 0 upon activation.
                </div>
              </div>
            )}

            {selectedCampaignForAction.action === 'COMPLETE' && (
              <div className="space-y-3 text-sm text-slate-600">
                <p>
                  Are you sure you want to end this campaign? Once completed, no further rewards will be issued under this campaign ID.
                </p>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-3">
              <Button variant="outline" onClick={() => setSelectedCampaignForAction(null)}>
                Cancel
              </Button>
              <Button
                variant={
                  selectedCampaignForAction.action === 'COMPLETE' ? 'danger' : 'primary'
                }
                isLoading={isSubmitting}
                onClick={handleExecuteAction}
              >
                {selectedCampaignForAction.action === 'APPROVE' && 'Confirm & Approve Draft'}
                {selectedCampaignForAction.action === 'ACTIVATE' && 'Confirm & Activate'}
                {selectedCampaignForAction.action === 'COMPLETE' && 'Complete Campaign'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
