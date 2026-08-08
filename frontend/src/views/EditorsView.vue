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
const loading = ref(false)

const METRICS = [
  'editors.active',
  'editors.highly_active',
  'editors.new_accounts',
  'editors.activity_1_4',
  'editors.activity_5_24',
  'editors.activity_25_99',
  'edits.user',
  'edits.group_bot',
  'edits.name_bot',
  'edits.anonymous',
]

async function load() {
  loading.value = true
  try {
    if (!filters.loaded) await filters.loadProjects()
    const res = await api.batch(filters.projectId, METRICS, filters.queryParams)
    seriesMap.value = res.series
  } finally {
    loading.value = false
  }
}

watch(
  () => [filters.projectId, filters.start, filters.end, filters.interval],
  () => load(),
  { immediate: true },
)

const p = (id: string) => seriesMap.value[id]?.points || []
const label = (id: string) => metricLabel(t, id)
</script>

<template>
  <div>
    <h1>{{ t('editors.title') }}</h1>
    <p class="muted">{{ t('editors.intro') }}</p>
    <FilterBar />
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <template v-else>
      <div class="cards">
        <MetricCard :label="label('editors.active')" :points="p('editors.active')" />
        <MetricCard :label="label('editors.highly_active')" :points="p('editors.highly_active')" />
        <MetricCard :label="label('editors.new_accounts')" :points="p('editors.new_accounts')" />
      </div>
      <SeriesChart
        :title="t('editors.activityDist')"
        type="bar"
        stacked
        :series="[
          { name: label('editors.activity_1_4'), points: p('editors.activity_1_4') },
          { name: label('editors.activity_5_24'), points: p('editors.activity_5_24') },
          { name: label('editors.activity_25_99'), points: p('editors.activity_25_99') },
          { name: label('editors.highly_active'), points: p('editors.highly_active') },
        ]"
      />
      <SeriesChart
        :title="t('editors.botHuman')"
        type="bar"
        stacked
        :series="[
          { name: label('edits.user'), points: p('edits.user') },
          { name: label('edits.group_bot'), points: p('edits.group_bot') },
          { name: label('edits.name_bot'), points: p('edits.name_bot') },
          { name: label('edits.anonymous'), points: p('edits.anonymous') },
        ]"
      />
    </template>
  </div>
</template>
