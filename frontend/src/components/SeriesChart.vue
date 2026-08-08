<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { useI18n } from 'vue-i18n'
import { downloadText, seriesToCsv } from '../utils/format'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const props = defineProps<{
  title: string
  series: Array<{
    name: string
    points: Array<{ period_start: string; value: number }>
  }>
  type?: 'line' | 'bar'
  stacked?: boolean
}>()

const { t } = useI18n()

const option = computed(() => {
  const categories = Array.from(
    new Set(props.series.flatMap((s) => s.points.map((p) => p.period_start))),
  ).sort()
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: props.series.map((s) => s.name), type: 'scroll' },
    grid: { left: 48, right: 16, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: categories },
    yAxis: { type: 'value' },
    series: props.series.map((s) => {
      const map = new Map(s.points.map((p) => [p.period_start, p.value]))
      return {
        name: s.name,
        type: props.type || 'line',
        smooth: true,
        stack: props.stacked ? 'total' : undefined,
        data: categories.map((c) => map.get(c) ?? null),
        areaStyle: props.stacked ? {} : undefined,
      }
    }),
  }
})

function exportCsv() {
  const chunks = props.series.map((s) => seriesToCsv(s.name, s.points))
  downloadText(`${props.title.replace(/\s+/g, '_').toLowerCase()}.csv`, chunks.join('\n\n'))
}
</script>

<template>
  <div class="panel">
    <div class="panel-tools">
      <h2>{{ title }}</h2>
      <button class="btn" type="button" @click="exportCsv">{{ t('common.exportCsv') }}</button>
    </div>
    <VChart class="chart" :option="option" autoresize />
    <div class="table-wrap">
      <table class="data" :aria-label="t('common.dataTable')">
        <thead>
          <tr>
            <th>period_start (UTC)</th>
            <th v-for="s in series" :key="s.name">{{ s.name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="period in Array.from(
              new Set(series.flatMap((s) => s.points.map((p) => p.period_start))),
            ).sort()"
            :key="period"
          >
            <td>{{ period }}</td>
            <td v-for="s in series" :key="s.name">
              {{ s.points.find((p) => p.period_start === period)?.value ?? '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
