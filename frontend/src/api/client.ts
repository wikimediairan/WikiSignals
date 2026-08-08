export type Project = {
  id: string
  domain: string
  language: string
  text_direction: string
  family: string
  display_name: string
  default_for_workspace: boolean
  features: Record<string, unknown>
  related_projects: string[]
  health_config?: Record<string, unknown>
  enabled: boolean
}

export type MetricDefinition = {
  id: string
  display_name: string
  definition: string
  methodology: string
  source: string
  unit: string
  intervals: string[]
  caveats?: string | null
  privacy_notes?: string | null
  status: string
  module: string
  domain?: string
  role?: string
  numerator?: string | null
  denominator?: string | null
  formula?: string | null
  metric_version?: string
  source_endpoint?: string | null
  provenance_notes?: string | null
  deprecation?: Record<string, unknown> | null
}

export type SeriesPoint = {
  period_start: string
  value: number
  source?: string | null
}

export type MetricSeries = {
  project_id: string
  metric_id: string
  interval: string
  start: string
  end: string
  status: string
  definition?: MetricDefinition | null
  points: SeriesPoint[]
  unavailable_reason?: string | null
}

export type HealthSignal = {
  id: string
  label: string
  domain: string
  value: number | null
  previous: number | null
  period_start: string | null
  change_pct: number | null
  direction: string
  status: string
  rule: string
  role?: string | null
  source?: string | null
  provenance_notes?: string | null
  unavailable_reason?: string | null
}

export type HealthResponse = {
  project_id: string
  period: { end: string; interval: string }
  signals: HealthSignal[]
  context: HealthSignal[]
  disclaimer: string
  new_editor_health?: { url?: string | null; show_context_cards?: boolean; note?: string }
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  projects: () => getJson<Project[]>('/api/v1/projects'),
  definitions: () => getJson<MetricDefinition[]>('/api/v1/metrics/definitions'),
  series: (projectId: string, metricId: string, params: Record<string, string>) => {
    const q = new URLSearchParams(params)
    return getJson<MetricSeries>(
      `/api/v1/projects/${encodeURIComponent(projectId)}/metrics/${encodeURIComponent(metricId)}?${q}`,
    )
  },
  batch: (projectId: string, ids: string[], params: Record<string, string>) => {
    const q = new URLSearchParams({ ...params, ids: ids.join(',') })
    return getJson<{ series: Record<string, MetricSeries> }>(
      `/api/v1/projects/${encodeURIComponent(projectId)}/metrics?${q}`,
    )
  },
  health: (projectId: string, end?: string) => {
    const q = end ? `?end=${encodeURIComponent(end)}` : ''
    return getJson<HealthResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/health${q}`)
  },
  backlogs: (projectId: string) =>
    getJson<{ tracks: Array<Record<string, unknown>>; note?: string }>(
      `/api/v1/projects/${encodeURIComponent(projectId)}/backlogs`,
    ),
  processes: (projectId: string) =>
    getJson<{ tracks: Array<Record<string, unknown>>; note?: string }>(
      `/api/v1/projects/${encodeURIComponent(projectId)}/processes`,
    ),
  compare: (projects: string[], metric: string, params: Record<string, string>) => {
    const q = new URLSearchParams({ ...params, projects: projects.join(','), metric })
    return getJson<{
      disclaimer: string
      series: Record<string, SeriesPoint[]>
      metric_id: string
    }>(`/api/v1/compare?${q}`)
  },
  topPages: (projectId: string, snapshot_type: string) =>
    getJson<{ items: Array<Record<string, unknown>>; period_start?: string }>(
      `/api/v1/projects/${encodeURIComponent(projectId)}/top-pages?snapshot_type=${snapshot_type}`,
    ),
  cohorts: (projectId: string) =>
    getJson<{
      available: boolean
      reason?: string | null
      cohorts: Array<{ cohort_month: string; stages: Array<{ stage: string; value: number }> }>
    }>(`/api/v1/projects/${encodeURIComponent(projectId)}/cohorts`),
  annotations: (projectId: string) =>
    getJson<
      Array<{
        id: number
        title: string
        start_date: string
        end_date?: string | null
        description?: string | null
        category?: string | null
      }>
    >(`/api/v1/projects/${encodeURIComponent(projectId)}/annotations`),
  methodology: () =>
    getJson<{
      timezone: string
      intervals: Record<string, string>
      privacy_summary: string
      metrics: MetricDefinition[]
    }>('/api/v1/methodology'),
  exportUrl: (projects: string[], metrics: string[], params: Record<string, string>, format: 'csv' | 'json') => {
    const q = new URLSearchParams({
      ...params,
      projects: projects.join(','),
      metrics: metrics.join(','),
      format,
    })
    return `/api/v1/export?${q}`
  },
}
