import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format integer paise into Indian Rupee currency format (e.g. 850000 -> ₹8,500.00)
 */
export function formatPaiseToINR(paise: number | null | undefined, showDecimals: boolean = true): string {
  if (paise === null || paise === undefined || isNaN(paise)) {
    return '—';
  }

  const rupees = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: showDecimals ? 2 : 0,
    maximumFractionDigits: showDecimals ? 2 : 0,
  }).format(rupees);
}

/**
 * Convert integer rupees to integer paise
 */
export function rupeesToPaise(rupees: number): number {
  return Math.round(rupees * 100);
}

/**
 * Format ISO timestamp into Asia/Kolkata merchant local time
 */
export function formatDateKolkata(
  isoDateStr: string,
  options?: Intl.DateTimeFormatOptions
): string {
  try {
    const date = new Date(isoDateStr);
    if (isNaN(date.getTime())) return isoDateStr;

    const defaultOptions: Intl.DateTimeFormatOptions = {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      ...options,
    };

    return new Intl.DateTimeFormat('en-IN', defaultOptions).format(date);
  } catch {
    return isoDateStr;
  }
}

/**
 * Truncate long IDs or hashes with ellipsis
 */
export function truncateId(id: string, len: number = 8): string {
  if (!id) return '';
  if (id.length <= len) return id;
  return `${id.slice(0, len)}...`;
}
