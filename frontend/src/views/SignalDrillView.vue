<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import FilterBar from '../components/FilterBar.vue'
import SeriesChart from '../components/SeriesChart.vue'
import { api, type MetricSeries } from '../api/client'
import { useFiltersStore } from '../stores/filters'
import { metricLabel } from '../utils/metricLabel'

const route = useRoute()
const { t } = useI18n()
const filters = useFiltersStore()
const series = ref<MetricSeries | null>(null)

const metricId = computed(() => String(route.params.metricId || ''))

async function load() {
  if (!metricId.value) return
  if (!filters.loaded) await filters.loadProjects()
  series.value = await api.series(filters.projectId, metricId.value, filters.queryParams)
}

watch(
  () => [metricId.value, filters.projectId, filters.start, filters.end, filters.interval],
  () => load(),
  { immediate: true },
)

const def = computed(() => series.value?.definition)
</script>

<template>
  <div>
    <h1>{{ metricLabel(t, metricId) }}</h1>
    <p class="muted"><code>{{ metricId }}</code></p>
    <FilterBar />
    <div v-if="def" class="panel">
      <p><strong>{{ t('methodology.definition') }}:</strong> {{ def.definition }}</p>
      <p><strong>{{ t('methodology.method') }}:</strong> {{ def.methodology }}</p>
      <p v-if="def.formula"><strong>{{ t('methodology.formula') }}:</strong> <code>{{ def.formula }}</code></p>
      <p v-if="def.numerator"><strong>{{ t('methodology.numerator') }}:</strong> {{ def.numerator }}</p>
      <p v-if="def.denominator"><strong>{{ t('methodology.denominator') }}:</strong> {{ def.denominator }}</p>
      <p>
        <strong>{{ t('methodology.source') }}:</strong> {{ def.source }}
        <span v-if="def.role" class="badge">{{ def.role }}</span>
        <span v-if="def.domain" class="badge">{{ def.domain }}</span>
      </p>
      <p v-if="def.provenance_notes" class="muted">{{ def.provenance_notes }}</p>
      <p v-if="def.caveats"><strong>{{ t('methodology.caveats') }}:</strong> {{ def.caveats }}</p>
    </div>
    <SeriesChart
      :title="metricLabel(t, metricId)"
      :series="[{ name: metricLabel(t, metricId), points: series?.points || [] }]"
    />
    <p v-if="series?.unavailable_reason" class="callout warn">{{ series.unavailable_reason }}</p>
  </div>
</template>
