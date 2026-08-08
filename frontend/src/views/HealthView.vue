<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FilterBar from '../components/FilterBar.vue'
import { api, type HealthSignal } from '../api/client'
import { useFiltersStore } from '../stores/filters'
import { formatNumber } from '../utils/format'

const { t, locale } = useI18n()
const filters = useFiltersStore()
const loading = ref(false)
const error = ref<string | null>(null)
const disclaimer = ref('')
const signals = ref<HealthSignal[]>([])
const context = ref<HealthSignal[]>([])
const newcomerNote = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    if (!filters.loaded) await filters.loadProjects()
    const res = await api.health(filters.projectId, filters.end)
    signals.value = res.signals
    context.value = res.context
    disclaimer.value = res.disclaimer
    newcomerNote.value = res.new_editor_health?.note || null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

watch(
  () => [filters.projectId, filters.end],
  () => load(),
  { immediate: true },
)

const byDomain = computed(() => {
  const map: Record<string, HealthSignal[]> = {}
  for (const s of signals.value) {
    map[s.domain] = map[s.domain] || []
    map[s.domain].push(s)
  }
  return map
})

function statusClass(status: string) {
  if (status === 'needs_attention') return 'status-attention'
  if (status === 'improving') return 'status-improving'
  if (status === 'unavailable') return 'status-na'
  return 'status-stable'
}
</script>

<template>
  <div>
    <h1>{{ t('health.title') }}</h1>
    <p class="muted">{{ t('health.intro') }}</p>
    <div class="callout">{{ t('health.vsWikistats') }}</div>
    <FilterBar />
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="callout warn">{{ t('common.error') }}: {{ error }}</p>
    <template v-else>
      <div class="callout">{{ disclaimer }}</div>
      <div v-if="newcomerNote" class="callout muted">{{ newcomerNote }}</div>

      <h2>{{ t('health.signals') }}</h2>
      <div class="cards">
        <div
          v-for="s in signals"
          :key="s.id"
          class="card signal-card"
          :class="statusClass(s.status)"
        >
          <div class="label">{{ s.label }}</div>
          <div class="value">
            <template v-if="s.value !== null && s.value !== undefined">
              {{ formatNumber(s.value, locale) }}
            </template>
            <template v-else>—</template>
          </div>
          <div class="delta" :class="{ up: s.direction === 'up', down: s.direction === 'down' }">
            <template v-if="s.change_pct !== null && s.change_pct !== undefined">
              {{ s.change_pct > 0 ? '+' : '' }}{{ formatNumber(s.change_pct, locale) }}%
              {{ t('common.change') }}
            </template>
            <template v-else>{{ t('common.unavailable') }}</template>
          </div>
          <div class="badge">{{ t(`health.status.${s.status}`) }}</div>
          <router-link class="drill" :to="`/signals/${encodeURIComponent(s.id)}`">
            {{ t('health.drill') }}
          </router-link>
        </div>
      </div>

      <div v-for="(list, domain) in byDomain" :key="domain" class="panel">
        <h2>{{ t(`health.domains.${domain}`, domain) }}</h2>
        <ul class="signal-list">
          <li v-for="s in list" :key="s.id">
            <strong>{{ s.label }}</strong>
            <span v-if="s.value !== null">: {{ formatNumber(s.value, locale) }}</span>
            <span class="badge" :class="statusClass(s.status)">{{ t(`health.status.${s.status}`) }}</span>
            <div class="muted small">{{ s.rule }}</div>
          </li>
        </ul>
      </div>

      <div class="panel">
        <h2>{{ t('health.contextTitle') }}</h2>
        <p class="muted">{{ t('health.contextIntro') }}</p>
        <ul>
          <li v-for="c in context" :key="c.id">
            {{ c.label }}:
            <template v-if="c.value !== null">{{ formatNumber(c.value, locale) }}</template>
            <template v-else>—</template>
            <span class="muted"> ({{ c.source || 'official' }})</span>
          </li>
        </ul>
        <router-link to="/context">{{ t('health.openContext') }}</router-link>
      </div>
    </template>
  </div>
</template>

<style scoped>
.signal-card {
  position: relative;
}
.signal-card .drill {
  display: inline-block;
  margin-top: 0.4rem;
  font-size: 0.85rem;
}
.status-attention {
  border-color: #fc3;
}
.status-improving {
  border-color: #14866d;
}
.status-na {
  opacity: 0.75;
}
.signal-list {
  padding-inline-start: 1.1rem;
}
.small {
  font-size: 0.8rem;
}
</style>
