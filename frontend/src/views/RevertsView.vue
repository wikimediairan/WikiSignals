<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FilterBar from '../components/FilterBar.vue'
import { api, type MetricSeries } from '../api/client'
import { useFiltersStore } from '../stores/filters'
import { metricLabel } from '../utils/metricLabel'

const { t } = useI18n()
const filters = useFiltersStore()
const series = ref<MetricSeries | null>(null)

async function load() {
  if (!filters.loaded) await filters.loadProjects()
  series.value = await api.series(filters.projectId, 'reverts.count', filters.queryParams)
}

watch(
  () => [filters.projectId, filters.start, filters.end, filters.interval],
  () => load(),
  { immediate: true },
)
</script>

<template>
  <div>
    <h1>{{ t('reverts.title') }}</h1>
    <p class="muted">{{ t('reverts.intro') }}</p>
    <FilterBar />
    <div class="callout warn">
      {{ series?.unavailable_reason || t('reverts.requiresReplicas') }}
    </div>
    <div class="panel">
      <h2>{{ metricLabel(t, 'reverts.count') }}</h2>
      <p v-if="!series?.points?.length" class="muted">{{ t('common.unavailable') }}</p>
      <div v-else class="table-wrap">
        <table class="data">
          <thead>
            <tr>
              <th>period_start</th>
              <th>value</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in series.points" :key="p.period_start">
              <td>{{ p.period_start }}</td>
              <td>{{ p.value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
