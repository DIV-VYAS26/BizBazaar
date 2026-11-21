import React from 'react';
import { ShieldAlert } from 'lucide-react';

export function DisclaimerBanner() {
  return (
    <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 text-xs text-amber-900 font-medium flex items-center justify-between flex-wrap gap-2">
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
        <span>
          <strong>Merchant records:</strong> Sales and repayments record payments you received separately. Campaign rewards and the payment simulator are simulations. BizBazaar does not process payments.
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="bg-amber-200/60 text-amber-800 px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide uppercase">
          Merchant workspace
        </span>
      </div>
    </div>
  );
}
