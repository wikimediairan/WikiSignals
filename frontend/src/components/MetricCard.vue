<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatNumber, pctChange } from '../utils/format'

const props = defineProps<{
  label: string
  points: Array<{ period_start: string; value: number }>
  status?: string
}>()

const { t, locale } = useI18n()

const latest = computed(() => props.points[props.points.length - 1])
const prev = computed(() => props.points[props.points.length - 2])
const delta = computed(() =>
  latest.value ? pctChange(latest.value.value, prev.value?.value) : null,
)
</script>

<template>
  <div class="card">
    <div class="label">
      {{ label }}
      <span v-if="status && status !== 'stable'" class="badge">{{ status }}</span>
    </div>
    <div v-if="latest" class="value">{{ formatNumber(latest.value, locale) }}</div>
    <div v-else class="value muted">—</div>
    <div
      v-if="delta !== null"
      class="delta"
      :class="{ up: delta > 0, down: delta < 0 }"
    >
      {{ delta > 0 ? '+' : '' }}{{ formatNumber(delta, locale) }}% {{ t('common.change') }}
    </div>
  </div>
</template>
