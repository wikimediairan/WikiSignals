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
const loading = ref(false)
const error = ref<string | null>(null)
const seriesMap = ref<Record<string, MetricSeries>>({})

const METRICS = [
  'edits.total',
  'edits.user',
  'editors.active',
  'editors.highly_active',
  'editors.new_accounts',
  'content.pages_created',
  'content.pages_edited',
  'readers.pageviews',
  'readers.unique_devices',
]

async function load() {
  loading.value = true
  error.value = null
  try {
    if (!filters.loaded) await filters.loadProjects()
    const res = await api.batch(filters.projectId, METRICS, filters.queryParams)
    seriesMap.value = res.series
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

watch(
  () => [filters.projectId, filters.start, filters.end, filters.interval],
  () => load(),
  { immediate: true },
)

function label(id: string) {
  return metricLabel(t, id)
}

function points(id: string) {
  return seriesMap.value[id]?.points || []
}
</script>

<template>
  <div>
    <h1>{{ t('overview.title') }}</h1>
    <p class="muted">{{ t('overview.intro') }}</p>
    <FilterBar />
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="callout warn">{{ t('common.error') }}: {{ error }}</p>
    <template v-else>
      <div class="cards">
        <MetricCard
          v-for="id in METRICS"
          :key="id"
          :label="label(id)"
          :points="points(id)"
          :status="seriesMap[id]?.status"
        />
      </div>
      <SeriesChart
        :title="label('edits.total')"
        :series="[{ name: label('edits.total'), points: points('edits.total') }]"
      />
      <div class="grid-2">
        <SeriesChart
          :title="label('editors.active')"
          :series="[{ name: label('editors.active'), points: points('editors.active') }]"
        />
        <SeriesChart
          :title="label('readers.pageviews')"
          :series="[{ name: label('readers.pageviews'), points: points('readers.pageviews') }]"
        />
      </div>
    </template>
  </div>
</template>
