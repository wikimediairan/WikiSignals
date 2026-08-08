export function formatNumber(n: number, locale: string): string {
  return new Intl.NumberFormat(locale === 'fa' ? 'fa-IR' : 'en', {
    maximumFractionDigits: 1,
  }).format(n)
}

export function pctChange(current: number, previous: number | undefined): number | null {
  if (previous === undefined || previous === 0) return null
  return ((current - previous) / previous) * 100
}

export function seriesToCsv(metricId: string, points: Array<{ period_start: string; value: number }>): string {
  const lines = ['period_start,value,metric_id']
  for (const p of points) {
    lines.push(`${p.period_start},${p.value},${metricId}`)
  }
  return lines.join('\n')
}

export function downloadText(filename: string, text: string, mime = 'text/csv') {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
