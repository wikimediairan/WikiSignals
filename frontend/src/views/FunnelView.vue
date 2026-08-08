<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FilterBar from '../components/FilterBar.vue'
import { api } from '../api/client'
import { useFiltersStore } from '../stores/filters'
import { metricLabel } from '../utils/metricLabel'

const { t } = useI18n()
const filters = useFiltersStore()
const available = ref(false)
const reason = ref<string | null>(null)
const cohorts = ref<
  Array<{ cohort_month: string; stages: Array<{ stage: string; value: number }> }>
>([])

async function load() {
  if (!filters.loaded) await filters.loadProjects()
  const res = await api.cohorts(filters.projectId)
  available.value = res.available
  reason.value = res.reason || null
  cohorts.value = res.cohorts
}

watch(
  () => filters.projectId,
  () => load(),
  { immediate: true },
)
</script>

<template>
  <div>
    <h1>{{ t('funnel.title') }}</h1>
    <p class="muted">{{ t('funnel.intro') }}</p>
    <div class="callout warn">{{ t('funnel.requiresReplicas') }}</div>
    <FilterBar />
    <div v-if="!available" class="callout">
      {{ reason || t('common.unavailable') }}
    </div>
    <div v-else class="stack">
      <div v-for="c in cohorts" :key="c.cohort_month" class="panel">
        <h2>{{ c.cohort_month }}</h2>
        <table class="data">
          <thead>
            <tr>
              <th>stage</th>
              <th>value</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in c.stages" :key="s.stage">
              <td>{{ metricLabel(t, s.stage) }}</td>
              <td>{{ s.value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
