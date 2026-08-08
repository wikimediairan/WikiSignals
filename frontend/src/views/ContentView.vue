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
const topEdits = ref<Array<Record<string, unknown>>>([])
const topViews = ref<Array<Record<string, unknown>>>([])

const METRICS = [
  'content.pages_created',
  'content.pages_created_content',
  'content.pages_edited',
  'readers.pageviews',
]

async function load() {
  if (!filters.loaded) await filters.loadProjects()
  const res = await api.batch(filters.projectId, METRICS, filters.queryParams)
  seriesMap.value = res.series
  try {
    topEdits.value = (await api.topPages(filters.projectId, 'top_by_edits')).items.slice(0, 20)
    topViews.value = (await api.topPages(filters.projectId, 'top_by_pageviews')).items.slice(0, 20)
  } catch {
    topEdits.value = []
    topViews.value = []
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
    <h1>{{ t('content.title') }}</h1>
    <p class="muted">{{ t('content.intro') }}</p>
    <FilterBar />
    <div class="cards">
      <MetricCard :label="label('content.pages_created_content')" :points="p('content.pages_created_content')" />
      <MetricCard :label="label('content.pages_edited')" :points="p('content.pages_edited')" />
      <MetricCard :label="label('readers.pageviews')" :points="p('readers.pageviews')" />
    </div>
    <SeriesChart
      :title="label('content.pages_created')"
      :series="[
        { name: label('content.pages_created'), points: p('content.pages_created') },
        { name: label('content.pages_created_content'), points: p('content.pages_created_content') },
      ]"
    />
    <div class="grid-2">
      <div class="panel">
        <h2>{{ t('content.topEdits') }}</h2>
        <div class="table-wrap">
          <table class="data">
            <thead>
              <tr>
                <th>page</th>
                <th>edits</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in topEdits" :key="i">
                <td>{{ row.page_title }}</td>
                <td>{{ row.edits }}</td>
              </tr>
              <tr v-if="!topEdits.length">
                <td colspan="2" class="muted">{{ t('common.noData') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="panel">
        <h2>{{ t('content.topViews') }}</h2>
        <div class="table-wrap">
          <table class="data">
            <thead>
              <tr>
                <th>page</th>
                <th>views</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in topViews" :key="i">
                <td>{{ row.page_title }}</td>
                <td>{{ row.views }}</td>
              </tr>
              <tr v-if="!topViews.length">
                <td colspan="2" class="muted">{{ t('common.noData') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
