<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFiltersStore } from '../stores/filters'

const { t } = useI18n()
const filters = useFiltersStore()

onMounted(() => {
  if (!filters.loaded) filters.loadProjects()
})
</script>

<template>
  <div class="filters">
    <div class="field">
      <label for="project">{{ t('filters.project') }}</label>
      <select id="project" v-model="filters.projectId">
        <option v-for="p in filters.projects" :key="p.id" :value="p.id">
          {{ p.display_name }}
        </option>
      </select>
    </div>
    <div class="field">
      <label for="start">{{ t('filters.start') }} ({{ t('common.utc') }})</label>
      <input id="start" v-model="filters.start" type="date" />
    </div>
    <div class="field">
      <label for="end">{{ t('filters.end') }} ({{ t('common.utc') }})</label>
      <input id="end" v-model="filters.end" type="date" />
    </div>
    <div class="field">
      <label for="interval">{{ t('filters.interval') }}</label>
      <select id="interval" v-model="filters.interval">
        <option value="day">{{ t('filters.day') }}</option>
        <option value="week">{{ t('filters.week') }}</option>
        <option value="month">{{ t('filters.month') }}</option>
        <option value="quarter">{{ t('filters.quarter') }}</option>
        <option value="year">{{ t('filters.year') }}</option>
      </select>
    </div>
  </div>
</template>
