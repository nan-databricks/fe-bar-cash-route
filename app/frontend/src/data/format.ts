export function thb(n: number, compact = true): string {
  if (compact) {
    if (Math.abs(n) >= 1_000_000) return `฿${(n / 1_000_000).toFixed(2)}M`;
    if (Math.abs(n) >= 1_000) return `฿${(n / 1_000).toFixed(0)}K`;
  }
  return `฿${n.toLocaleString("en-US")}`;
}

export function km(n: number): string {
  return `${n.toLocaleString("en-US", { maximumFractionDigits: 1 })} km`;
}

export function hours(n: number): string {
  return `${n.toLocaleString("en-US", { maximumFractionDigits: 1 })} h`;
}
