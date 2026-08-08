<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FilterBar from '../components/FilterBar.vue'
import MetricCard from '../components/MetricCard.vue'
import SeriesChart from '../components/SeriesChart.vue'
import { api, type MetricSeries } from '../api/client'
import { useFiltersStore } from '../stores/filters'
import { metricLabel } from '../utils/metricLabel'

const { t } = useI18n()
const filters = useFiltersStore()
const seriesMap = ref<Record<string, MetricSeries>>({})

const METRICS = [
  'edits.total',
  'edits.user',
  'editors.active',
  'editors.highly_active',
  'editors.new_accounts',
  'content.pages_created_content',
  'content.pages_edited',
  'readers.pageviews',
  'readers.unique_devices',
]

async function load() {
  if (!filters.loaded) await filters.loadProjects()
  const res = await api.batch(filters.projectId, METRICS, filters.queryParams)
  seriesMap.value = res.series
}

watch(
  () => [filters.projectId, filters.start, filters.end, filters.interval],
  () => load(),
  { immediate: true },
)

const p = (id: string) => seriesMap.value[id]?.points || []
</script>

<template>
  <div>
    <h1>{{ t('context.title') }}</h1>
    <div class="callout">{{ t('context.intro') }}</div>
    <p class="muted">
      <a href="https://stats.wikimedia.org" target="_blank" rel="noopener">stats.wikimedia.org</a>
      · Wikimedia Analytics API provenance on each series
    </p>
    <FilterBar />
    <div class="cards">
      <MetricCard
        v-for="id in METRICS"
        :key="id"
        :label="metricLabel(t, id)"
        :points="p(id)"
        status="official_context"
      />
    </div>
    <div class="grid-2">
      <SeriesChart
        :title="metricLabel(t, 'editors.active')"
        :series="[{ name: metricLabel(t, 'editors.active'), points: p('editors.active') }]"
      />
      <SeriesChart
        :title="metricLabel(t, 'readers.pageviews')"
        :series="[{ name: metricLabel(t, 'readers.pageviews'), points: p('readers.pageviews') }]"
      />
    </div>
  </div>
</template>
