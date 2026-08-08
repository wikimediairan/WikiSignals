<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FilterBar from '../components/FilterBar.vue'
import SeriesChart from '../components/SeriesChart.vue'
import { api, type MetricSeries } from '../api/client'
import { useFiltersStore } from '../stores/filters'
import { metricLabel } from '../utils/metricLabel'

const { t } = useI18n()
const filters = useFiltersStore()
const series = ref<MetricSeries | null>(null)
const annotations = ref<
  Array<{ id: number; title: string; start_date: string; end_date?: string | null; description?: string | null }>
>([])

async function load() {
  if (!filters.loaded) await filters.loadProjects()
  series.value = await api.series(filters.projectId, 'editors.active', {
    ...filters.queryParams,
    // widen for history if needed
  })
  annotations.value = await api.annotations(filters.projectId)
}

watch(
  () => [filters.projectId, filters.start, filters.end, filters.interval],
  () => load(),
  { immediate: true },
)
</script>

<template>
  <div>
    <h1>{{ t('history.title') }}</h1>
    <p class="muted">{{ t('history.intro') }}</p>
    <FilterBar />
    <SeriesChart
      :title="metricLabel(t, 'editors.active')"
      :series="[{ name: metricLabel(t, 'editors.active'), points: series?.points || [] }]"
    />
    <div class="panel">
      <h2>{{ t('history.annotations') }}</h2>
      <ul>
        <li v-for="a in annotations" :key="a.id">
          <strong>{{ a.start_date }}</strong>
          <span v-if="a.end_date"> – {{ a.end_date }}</span>: {{ a.title }}
          <div v-if="a.description" class="muted">{{ a.description }}</div>
        </li>
        <li v-if="!annotations.length" class="muted">{{ t('common.noData') }}</li>
      </ul>
    </div>
  </div>
</template>
