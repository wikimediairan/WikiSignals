/**
 * Human-readable labels for metric IDs.
 *
 * vue-i18n treats "." as a path separator, so IDs like "readers.pageviews"
 * must map to nested message keys: metrics.readers.pageviews
 */
import type { ComposerTranslation } from 'vue-i18n'

/** Nested under `metrics` in locale files — mirrors metric id segments. */
const FALLBACK_EN: Record<string, string> = {
  'edits.total': 'Total edits (official)',
  'edits.user': 'Human edits (official)',
  'edits.group_bot': 'Group-bot edits (official)',
  'edits.name_bot': 'Name-bot edits (official)',
  'edits.anonymous': 'Anonymous edits (official)',
  'editors.active': 'Active editors (official)',
  'editors.highly_active': 'Highly active editors (official)',
  'editors.new_accounts': 'New accounts (official)',
  'editors.activity_1_4': 'Editors with 1–4 edits',
  'editors.activity_5_24': 'Editors with 5–24 edits',
  'editors.activity_25_99': 'Editors with 25–99 edits',
  'content.pages_created': 'Pages created (official)',
  'content.pages_created_content': 'Content pages created (official)',
  'content.pages_edited': 'Pages edited (official)',
  'content.pages_deleted': 'Pages deleted',
  'readers.pageviews': 'Page views (official)',
  'readers.unique_devices': 'Unique devices (official)',
  'moderation.blocks': 'Blocks',
  'admin.blocks': 'Blocks',
  'admin.unblocks': 'Unblocks',
  'admin.protections': 'Protections',
  'admin.unprotections': 'Unprotections',
  'admin.deletions': 'Deletions',
  'admin.undeletions': 'Undeletions',
  'admin.moves': 'Page moves',
  'admin.rights_changes': 'Rights changes',
  'admin.actions_total': 'Admin actions (total)',
  'admin.actions_per_active_editor': 'Admin actions per active editor',
  'maintenance.open_total': 'Maintenance backlog (configured)',
  'maintenance.backlog_per_active_editor': 'Backlog per active editor',
  'automation.bot_edit_share': 'Bot edit share',
  'reverts.count': 'Reverted edits',
  'reverts.rate': 'Revert rate',
  'reverts.newcomer_rate': 'Newcomer revert rate',
  'editors.returning': 'Returning editors',
  'funnel.accounts': 'New accounts (cohort)',
  'funnel.first_edit': 'Made a first edit',
  'funnel.second_edit': 'Made a second edit',
  'funnel.active_7d': 'Active within 7 days',
  'funnel.active_30d': 'Active within 30 days',
  'funnel.active_90d': 'Active within 90 days',
  'funnel.active_180d': 'Active within 180 days',
}

export function metricLabel(t: ComposerTranslation, metricId: string): string {
  const key = `metrics.${metricId}`
  const translated = String(t(key))
  // Missing keys return the key path itself in vue-i18n
  if (translated && translated !== key) {
    return translated
  }
  return FALLBACK_EN[metricId] ?? humanizeMetricId(metricId)
}

function humanizeMetricId(id: string): string {
  const leaf = id.includes('.') ? id.slice(id.lastIndexOf('.') + 1) : id
  return leaf
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Options for compare / metric pickers */
export const METRIC_OPTIONS: { id: string; group: string }[] = [
  { id: 'editors.active', group: 'Editors' },
  { id: 'editors.highly_active', group: 'Editors' },
  { id: 'editors.new_accounts', group: 'Editors' },
  { id: 'edits.total', group: 'Edits' },
  { id: 'edits.user', group: 'Edits' },
  { id: 'readers.pageviews', group: 'Readers' },
  { id: 'readers.unique_devices', group: 'Readers' },
  { id: 'content.pages_created_content', group: 'Content' },
  { id: 'content.pages_edited', group: 'Content' },
]
