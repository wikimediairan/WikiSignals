<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FilterBar from '../components/FilterBar.vue'
import SeriesChart from '../components/SeriesChart.vue'
import MetricCard from '../components/MetricCard.vue'
import { api, type MetricSeries } from '../api/client'
import { useFiltersStore } from '../stores/filters'
import { metricLabel } from '../utils/metricLabel'

const props = defineProps<{
  domain: string
  metricIds: string[]
  titleKey: string
  introKey: string
}>()

const { t } = useI18n()
const filters = useFiltersStore()
const seriesMap = ref<Record<string, MetricSeries>>({})
const loading = ref(false)
const extraNote = ref<string | null>(null)
const backlogTracks = ref<Array<Record<string, unknown>>>([])
const processTracks = ref<Array<Record<string, unknown>>>([])

async function load() {
  loading.value = true
  try {
    if (!filters.loaded) await filters.loadProjects()
    if (props.metricIds.length) {
      const res = await api.batch(filters.projectId, props.metricIds, filters.queryParams)
      seriesMap.value = res.series
    }
    if (props.domain === 'maintenance') {
      const b = await api.backlogs(filters.projectId)
      backlogTracks.value = b.tracks
      extraNote.value = b.note || null
    }
    if (props.domain === 'governance') {
      const p = await api.processes(filters.projectId)
      processTracks.value = p.tracks
      extraNote.value = p.note || null
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => [filters.projectId, filters.start, filters.end, filters.interval, props.domain],
  () => load(),
  { immediate: true },
)

const chartSeries = computed(() =>
  props.metricIds
    .filter((id) => (seriesMap.value[id]?.points || []).length)
    .map((id) => ({ name: metricLabel(t, id), points: seriesMap.value[id]?.points || [] })),
)
</script>

<template>
  <div>
    <h1>{{ t(titleKey) }}</h1>
    <p class="muted">{{ t(introKey) }}</p>
    <FilterBar />
    <div v-if="extraNote" class="callout">{{ extraNote }}</div>
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <div class="cards">
      <MetricCard
        v-for="id in metricIds"
        :key="id"
        :label="metricLabel(t, id)"
        :points="seriesMap[id]?.points || []"
        :status="seriesMap[id]?.status"
      />
    </div>
    <SeriesChart
      v-if="chartSeries.length"
      :title="t(titleKey)"
      :series="chartSeries"
    />
    <div v-if="domain === 'maintenance'" class="panel">
      <h2>{{ t('health.configuredTracks') }}</h2>
      <table class="data">
        <thead>
          <tr>
            <th>id</th>
            <th>label</th>
            <th>enabled</th>
            <th>open</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tr in backlogTracks" :key="String(tr.id)">
            <td><code>{{ tr.id }}</code></td>
            <td>{{ tr.label }}</td>
            <td>{{ tr.enabled }}</td>
            <td>{{ (tr.latest as any)?.open_count ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="domain === 'governance'" class="panel">
      <h2>{{ t('health.processTracks') }}</h2>
      <table class="data">
        <thead>
          <tr>
            <th>id</th>
            <th>label</th>
            <th>enabled</th>
            <th>open</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tr in processTracks" :key="String(tr.id)">
            <td><code>{{ tr.id }}</code></td>
            <td>{{ tr.label }}</td>
            <td>{{ tr.enabled }}</td>
            <td>{{ (tr.latest as any)?.open_count ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
