<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, type MetricDefinition } from '../api/client'

const { t } = useI18n()
const metrics = ref<MetricDefinition[]>([])
const timezone = ref('UTC')
const intervals = ref<Record<string, string>>({})
const privacy = ref('')

onMounted(async () => {
  const res = await api.methodology()
  metrics.value = res.metrics
  timezone.value = res.timezone
  intervals.value = res.intervals
  privacy.value = res.privacy_summary
})
</script>

<template>
  <div>
    <h1>{{ t('methodology.title') }}</h1>
    <p class="muted">{{ t('methodology.intro') }}</p>
    <div class="callout">
      <div><strong>Timezone:</strong> {{ timezone }}</div>
      <div>{{ privacy }}</div>
    </div>
    <div class="panel">
      <h2>Intervals</h2>
      <ul>
        <li v-for="(v, k) in intervals" :key="k"><code>{{ k }}</code>: {{ v }}</li>
      </ul>
    </div>
    <div v-for="m in metrics" :key="m.id" class="panel">
      <h2>
        {{ m.display_name }}
        <span class="badge">{{ m.status }}</span>
      </h2>
      <p class="muted" style="margin-top: -0.35rem">
        <code>{{ m.id }}</code>
      </p>
      <p><strong>Definition:</strong> {{ m.definition }}</p>
      <p><strong>Methodology:</strong> {{ m.methodology }}</p>
      <p><strong>Source:</strong> {{ m.source }} · <strong>Unit:</strong> {{ m.unit }}</p>
      <p v-if="m.caveats"><strong>Caveats:</strong> {{ m.caveats }}</p>
      <p v-if="m.privacy_notes"><strong>Privacy:</strong> {{ m.privacy_notes }}</p>
    </div>
  </div>
</template>
