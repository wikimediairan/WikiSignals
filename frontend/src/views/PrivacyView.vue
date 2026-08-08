<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div>
    <h1>{{ t('privacy.title') }}</h1>
    <div class="panel">
      <p>{{ t('privacy.body') }}</p>
      <ul>
        <li>Aggregate analytics only in primary dashboards</li>
        <li>No individual volunteer ranking or score systems</li>
        <li>No inference of protected or sensitive characteristics</li>
        <li>High-activity lists are pages, not people</li>
        <li>Revert metrics never label users as “problematic”</li>
      </ul>
      <p class="muted">
        Full document:
        <code>docs/PRIVACY.md</code>
      </p>
    </div>
  </div>
</template>
