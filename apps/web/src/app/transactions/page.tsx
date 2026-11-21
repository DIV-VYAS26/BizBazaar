'use client';

import React, { useState, useEffect, useRef } from 'react';
import { bizbazaarApi, getApiMode } from '@/lib/api/client';
import {
  Transaction,
  TransactionImportReport,
  TransactionStatus,
} from '@/lib/generated/types';
import { formatPaiseToINR, formatDateKolkata } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  UploadCloud,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  Filter,
  Download,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState<TransactionStatus | 'ALL'>('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [importReport, setImportReport] = useState<TransactionImportReport | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchTransactions = async () => {
    try {
      setIsLoading(true);
      const res = await bizbazaarApi.getTransactions({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        limit: 100,
        offset: 0,
      });
      setTransactions(res.items);
      setTotalCount(res.total);
    } catch (err: any) {
      setUploadError(err?.message || 'Unable to load transactions');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [statusFilter]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      setUploadError(null);
      const report = await bizbazaarApi.importTransactions(file);
      setImportReport(report);
      await fetchTransactions();
    } catch (err: any) {
      setUploadError(err?.message || 'Failed to upload and validate CSV');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDownloadSample = (type: 'canonical' | 'errors') => {
    let content = '';
    let filename = '';

    if (type === 'canonical') {
      content = `transaction_id,merchant_id,amount_paise,status,timestamp,customer_vpa,note
TXN001,m_001,100000,SUCCESS,2026-11-01T09:15:00Z,customer1@okaxis,Groceries order 101
TXN002,m_001,150000,SUCCESS,2026-11-01T10:30:00Z,customer2@oksbi,Provisions and spices
TXN003,m_001,200000,SUCCESS,2026-11-01T11:45:00Z,customer3@okhdfc,Monthly pantry refill
TXN004,m_001,250000,SUCCESS,2026-11-01T14:20:00Z,customer4@demo,Oil and pulses package
TXN005,m_001,100000,SUCCESS,2026-11-01T16:05:00Z,customer5@okicici,Snacks and tea bags
TXN006,m_001,50000,SUCCESS,2026-11-01T17:40:00Z,customer6@upi,Dairy and bread
TXN007,m_001,70000,PENDING,2026-11-01T18:10:00Z,customer7@okaxis,Pending UPI confirmation
TXN008,m_001,30000,FAILED,2026-11-01T18:25:00Z,customer8@oksbi,Bank server timeout
TXN009,m_001,40000,REFUNDED,2026-11-01T19:00:00Z,customer9@okhdfc,Damaged packaging returned`;
      filename = 'canonical_transactions.csv';
    } else {
      content = `transaction_id,merchant_id,amount_paise,status,timestamp,customer_vpa,note
TXN001,m_001,100000,SUCCESS,2026-11-01T09:15:00Z,cust1@upi,Valid txn 1
TXN001,m_001,100000,SUCCESS,2026-11-01T09:15:00Z,cust1@upi,Duplicate TXN001
TXN_ERR1,m_001,-5000,SUCCESS,2026-11-01T12:00:00Z,cust3@upi,Invalid negative amount
TXN_ERR2,m_001,50000,UNKNOWN_STATUS,2026-11-01T13:00:00Z,cust4@upi,Invalid status string
TXN_ERR3,m_WRONG,20000,SUCCESS,2026-11-01T14:00:00Z,cust5@upi,Wrong merchant id`;
      filename = 'sample_with_errors.csv';
    }

    if (getApiMode() === 'live') {
      content = type === 'canonical'
        ? `transaction_id,amount_paise,currency,timestamp,status\nDEMO_CSV_001,100000,INR,2026-11-01T09:15:00Z,SUCCESS\n`
        : `transaction_id,amount_paise,currency,timestamp,status\nDEMO_CSV_001,100000,INR,2026-11-01T09:15:00Z,SUCCESS\nDEMO_INVALID,-1,INR,2026-11-01T10:00:00Z,SUCCESS\n`;
      filename = type === 'canonical' ? 'labelled_demo_import.csv' : 'labelled_demo_errors.csv';
    }
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const statusBadge = (status: TransactionStatus) => {
    switch (status) {
      case 'SUCCESS':
        return <Badge variant="success">SUCCESS</Badge>;
      case 'PENDING':
        return <Badge variant="warning">PENDING</Badge>;
      case 'FAILED':
        return <Badge variant="error">FAILED</Badge>;
      case 'REFUNDED':
        return <Badge variant="outline">REFUNDED</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Transactions & CSV Import</h1>
          <p className="text-sm text-slate-500 mt-1">
            Import raw transaction rows. BizBazaar validates authenticated merchant ID, positive paise amounts, and duplicate IDs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => handleDownloadSample('canonical')}>
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Download Canonical CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleDownloadSample('errors')}>
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Download Test Error CSV
          </Button>
        </div>
      </div>

      {/* Upload Dropzone */}
      <Card>
        <CardContent className="p-6">
          <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 flex flex-col items-center justify-center text-center hover:border-emerald-400 transition-colors bg-slate-50/50">
            <UploadCloud className="w-10 h-10 text-emerald-600 mb-3" />
            <h3 className="text-base font-semibold text-slate-800">Upload Transaction CSV</h3>
            <p className="text-xs text-slate-500 max-w-md mt-1 mb-4">
              Columns required:{' '}
              <code className="bg-slate-200 px-1 py-0.5 rounded text-slate-700 font-mono">
                transaction_id, amount_paise, currency, timestamp, status
              </code>
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              className="hidden"
              id="csv-file-input"
            />
            <Button
              variant="primary"
              size="md"
              isLoading={isUploading}
              onClick={() => fileInputRef.current?.click()}
            >
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              Choose CSV File
            </Button>
          </div>

          {uploadError && (
            <Alert variant="error" title="Upload Failed" className="mt-4">
              {uploadError}
            </Alert>
          )}

          {/* Import Report Breakdown */}
          {importReport && (
            <div className="mt-6 p-4 rounded-xl border border-slate-200 bg-slate-50/80 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Import Validation Summary
                </h4>
                <Button variant="ghost" size="sm" onClick={() => setImportReport(null)}>
                  Dismiss
                </Button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
                <div className="p-3 bg-white rounded-lg border border-slate-200">
                  <span className="text-xs text-slate-500 block">Total Rows</span>
                  <span className="text-lg font-bold text-slate-800">{importReport.total_rows}</span>
                </div>
                <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                  <span className="text-xs text-emerald-700 block">Valid Rows</span>
                  <span className="text-lg font-bold text-emerald-700">{importReport.valid_count}</span>
                </div>
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <span className="text-xs text-amber-700 block">Duplicates (Ignored)</span>
                  <span className="text-lg font-bold text-amber-700">{importReport.duplicate_count}</span>
                </div>
                <div className="p-3 bg-rose-50 rounded-lg border border-rose-200">
                  <span className="text-xs text-rose-700 block">Invalid (Rejected)</span>
                  <span className="text-lg font-bold text-rose-700">{importReport.invalid_count}</span>
                </div>
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <span className="text-xs text-blue-700 block">Net Imported</span>
                  <span className="text-lg font-bold text-blue-700">{importReport.imported_count}</span>
                </div>
              </div>

              {/* Row-level errors/warnings */}
              {importReport.issues.length > 0 && (
                <div className="mt-4 space-y-2">
                  <h5 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Row-Level Diagnostics ({importReport.issues.length})
                  </h5>
                  <div className="max-h-48 overflow-y-auto space-y-1.5 font-mono text-xs">
                    {importReport.issues.map((issue, idx) => (
                      <div
                        key={idx}
                        className={`p-2 rounded-md flex items-center justify-between ${
                          issue.severity === 'ERROR'
                            ? 'bg-rose-100/70 text-rose-900 border border-rose-200'
                            : 'bg-amber-100/70 text-amber-900 border border-amber-200'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-bold">Row {issue.row}:</span>
                          <span className="text-slate-600">[{issue.field}]</span>
                          <span>{issue.message}</span>
                        </div>
                        <Badge variant={issue.severity === 'ERROR' ? 'error' : 'warning'}>
                          {issue.severity}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filter and Transaction List */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <CardTitle>Recorded Transactions ({totalCount})</CardTitle>
            <CardDescription>
              Sorted in server acceptance order. Only SUCCESS status transactions are included in net recorded collections.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="text-xs rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="ALL">All Statuses ({totalCount})</option>
              <option value="SUCCESS">SUCCESS only</option>
              <option value="PENDING">PENDING only</option>
              <option value="FAILED">FAILED only</option>
              <option value="REFUNDED">REFUNDED only</option>
            </select>
          </div>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="py-12 flex justify-center items-center">
              <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
            </div>
          ) : transactions.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              No transactions found matching filter.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase">
                  <tr>
                    <th className="py-3 px-4">TXN ID</th>
                    <th className="py-3 px-4">Timestamp (IST)</th>
                    <th className="py-3 px-4">Customer VPA</th>
                    <th className="py-3 px-4">Note</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {transactions.map((txn) => (
                    <tr key={txn.transaction_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-900">{txn.transaction_id}</td>
                      <td className="py-3 px-4 text-slate-600 font-sans">
                        {formatDateKolkata(txn.timestamp)}
                      </td>
                      <td className="py-3 px-4 text-slate-500">{txn.customer_vpa || '—'}</td>
                      <td className="py-3 px-4 text-slate-500 font-sans">{txn.note || '—'}</td>
                      <td className="py-3 px-4">{statusBadge(txn.status)}</td>
                      <td className="py-3 px-4 text-right font-bold text-slate-900">
                        {formatPaiseToINR(txn.amount_paise)}
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
