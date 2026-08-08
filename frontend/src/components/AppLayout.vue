<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { applyDocumentLocale, type Locale } from '../i18n'
import { useFilterRouteSync } from '../stores/filters'
import AppFooter from './AppFooter.vue'

const { t, locale } = useI18n()
useFilterRouteSync()

const theme = computed({
  get: () => document.documentElement.getAttribute('data-theme') || 'light',
  set: (v: string) => {
    if (v === 'light') document.documentElement.removeAttribute('data-theme')
    else document.documentElement.setAttribute('data-theme', v)
  },
})

watch(
  locale,
  (v) => applyDocumentLocale(v as Locale),
  { immediate: true },
)

function setLocale(l: Locale) {
  locale.value = l
}
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <div>
        <router-link class="brand" to="/">{{ t('app.title') }}</router-link>
        <div class="muted" style="font-size: 0.8rem">{{ t('app.tagline') }}</div>
      </div>
      <nav class="nav">
        <router-link to="/">{{ t('nav.health') }}</router-link>
        <router-link to="/capacity">{{ t('nav.capacity') }}</router-link>
        <router-link to="/maintenance">{{ t('nav.maintenance') }}</router-link>
        <router-link to="/governance">{{ t('nav.governance') }}</router-link>
        <router-link to="/admin">{{ t('nav.admin') }}</router-link>
        <router-link to="/conflict">{{ t('nav.conflict') }}</router-link>
        <router-link to="/automation">{{ t('nav.automation') }}</router-link>
        <router-link to="/context">{{ t('nav.context') }}</router-link>
        <router-link to="/compare">{{ t('nav.compare') }}</router-link>
        <router-link to="/history">{{ t('nav.history') }}</router-link>
        <router-link to="/methodology">{{ t('nav.methodology') }}</router-link>
        <router-link to="/privacy">{{ t('nav.privacy') }}</router-link>
      </nav>
      <div class="lang-switch">
        <button class="btn" type="button" @click="setLocale('en')">EN</button>
        <button class="btn" type="button" @click="setLocale('fa')">FA</button>
        <button class="btn" type="button" @click="theme = theme === 'dark' ? 'light' : 'dark'">
          ◐
        </button>
      </div>
    </header>
    <main class="main">
      <slot />
    </main>
    <AppFooter />
  </div>
</template>
