<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import SeriesChart from '../components/SeriesChart.vue'
import { api } from '../api/client'
import { useFiltersStore } from '../stores/filters'
import { METRIC_OPTIONS, metricLabel } from '../utils/metricLabel'

const { t } = useI18n()
const filters = useFiltersStore()
const metric = ref('editors.active')
const disclaimer = ref('')
const series = ref<Array<{ name: string; points: Array<{ period_start: string; value: number }> }>>([])

async function load() {
  if (!filters.loaded) await filters.loadProjects()
  const res = await api.compare(filters.compareIds, metric.value, filters.queryParams)
  disclaimer.value = res.disclaimer
  series.value = Object.entries(res.series).map(([name, points]) => ({ name, points }))
}

watch(
  () => [filters.compareIds.join(','), filters.start, filters.end, filters.interval, metric.value],
  () => load(),
  { immediate: true },
)
</script>

<template>
  <div>
    <h1>{{ t('compare.title') }}</h1>
    <p class="muted">{{ t('compare.intro') }}</p>
    <div class="callout">{{ disclaimer || t('common.disclaimerCompare') }}</div>
    <div class="filters">
      <div class="field">
        <label>{{ t('common.projects') }}</label>
        <select
          multiple
          :value="filters.compareIds"
          style="min-height: 100px"
          @change="
            filters.compareIds = Array.from(($event.target as HTMLSelectElement).selectedOptions).map(
              (o) => o.value,
            )
          "
        >
          <option v-for="p in filters.projects" :key="p.id" :value="p.id">
            {{ p.display_name }}
          </option>
        </select>
      </div>
      <div class="field">
        <label>{{ t('common.metric') }}</label>
        <select v-model="metric">
          <option v-for="opt in METRIC_OPTIONS" :key="opt.id" :value="opt.id">
            {{ metricLabel(t, opt.id) }}
          </option>
        </select>
      </div>
      <div class="field">
        <label>{{ t('filters.start') }}</label>
        <input v-model="filters.start" type="date" />
      </div>
      <div class="field">
        <label>{{ t('filters.end') }}</label>
        <input v-model="filters.end" type="date" />
      </div>
    </div>
    <SeriesChart :title="metricLabel(t, metric)" :series="series" />
  </div>
</template>
