import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Project } from '../api/client'

function defaultEnd(): string {
  const d = new Date()
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-01`
}

function defaultStart(): string {
  const d = new Date()
  d.setUTCMonth(d.getUTCMonth() - 23)
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-01`
}

export const useFiltersStore = defineStore('filters', () => {
  const projects = ref<Project[]>([])
  const projectId = ref('fa.wikipedia')
  const compareIds = ref<string[]>(['fa.wikipedia', 'tr.wikipedia'])
  const start = ref(defaultStart())
  const end = ref(defaultEnd())
  const interval = ref('month')
  const loaded = ref(false)

  const queryParams = computed(() => ({
    start: start.value,
    end: end.value,
    interval: interval.value,
  }))

  async function loadProjects() {
    projects.value = await api.projects()
    const def = projects.value.find((p) => p.default_for_workspace)
    if (def && !loaded.value) {
      projectId.value = def.id
    }
    loaded.value = true
  }

  function syncFromRoute(query: Record<string, unknown>) {
    if (typeof query.project === 'string') projectId.value = query.project
    if (typeof query.start === 'string') start.value = query.start
    if (typeof query.end === 'string') end.value = query.end
    if (typeof query.interval === 'string') interval.value = query.interval
    if (typeof query.projects === 'string') {
      compareIds.value = query.projects.split(',').filter(Boolean)
    }
  }

  function toQuery() {
    return {
      project: projectId.value,
      start: start.value,
      end: end.value,
      interval: interval.value,
      projects: compareIds.value.join(','),
    }
  }

  return {
    projects,
    projectId,
    compareIds,
    start,
    end,
    interval,
    loaded,
    queryParams,
    loadProjects,
    syncFromRoute,
    toQuery,
  }
})

/** Keep URL shareable with filter state. */
export function useFilterRouteSync() {
  const route = useRoute()
  const router = useRouter()
  const filters = useFiltersStore()

  watch(
    () => route.query,
    (q) => filters.syncFromRoute(q as Record<string, unknown>),
    { immediate: true },
  )

  watch(
    () => [filters.projectId, filters.start, filters.end, filters.interval, filters.compareIds.join(',')],
    () => {
      router.replace({ query: { ...route.query, ...filters.toQuery() } })
    },
  )
}
