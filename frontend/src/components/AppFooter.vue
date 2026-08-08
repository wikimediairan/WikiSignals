<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const LINKS = {
  author: 'https://meta.wikimedia.org/wiki/User:Arian',
  github: 'https://github.com/wikimediairan/WikiSignals',
  toolforge: 'https://wikitech.wikimedia.org/wiki/Portal:Toolforge',
  license: 'https://www.gnu.org/licenses/gpl-3.0.html',
} as const
</script>

<template>
  <footer class="app-footer">
    <div class="app-footer__inner">
      <p class="app-footer__line">
        {{ t('footer.createdWith') }}
        <a :href="LINKS.author" target="_blank" rel="noopener noreferrer">Arian</a>
        –
        <a :href="LINKS.github" target="_blank" rel="noopener noreferrer">{{ t('footer.github') }}</a>
        –
        <a :href="LINKS.toolforge" target="_blank" rel="noopener noreferrer">{{ t('footer.toolforge') }}</a>
      </p>
      <p class="app-footer__line">
        {{ t('footer.licensePrefix') }}
        <a :href="LINKS.license" target="_blank" rel="noopener noreferrer">{{ t('footer.licenseName') }}</a>
      </p>
    </div>
  </footer>
</template>
