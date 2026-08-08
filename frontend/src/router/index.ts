import { createRouter, createWebHistory } from 'vue-router'
import HealthView from '../views/HealthView.vue'
import DomainView from '../views/DomainView.vue'
import ContextView from '../views/ContextView.vue'
import SignalDrillView from '../views/SignalDrillView.vue'
import CompareView from '../views/CompareView.vue'
import HistoryView from '../views/HistoryView.vue'
import MethodologyView from '../views/MethodologyView.vue'
import PrivacyView from '../views/PrivacyView.vue'
import FunnelView from '../views/FunnelView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'health', component: HealthView },
    {
      path: '/capacity',
      name: 'capacity',
      component: DomainView,
      props: {
        domain: 'capacity',
        titleKey: 'nav.capacity',
        introKey: 'domains.capacityIntro',
        metricIds: ['editors.active', 'editors.highly_active', 'editors.new_accounts'],
      },
    },
    {
      path: '/maintenance',
      name: 'maintenance',
      component: DomainView,
      props: {
        domain: 'maintenance',
        titleKey: 'nav.maintenance',
        introKey: 'domains.maintenanceIntro',
        metricIds: ['maintenance.open_total', 'maintenance.backlog_per_active_editor'],
      },
    },
    {
      path: '/governance',
      name: 'governance',
      component: DomainView,
      props: {
        domain: 'governance',
        titleKey: 'nav.governance',
        introKey: 'domains.governanceIntro',
        metricIds: [],
      },
    },
    {
      path: '/admin',
      name: 'admin',
      component: DomainView,
      props: {
        domain: 'admin',
        titleKey: 'nav.admin',
        introKey: 'domains.adminIntro',
        metricIds: [
          'admin.actions_total',
          'admin.actions_per_active_editor',
          'admin.blocks',
          'admin.protections',
          'admin.deletions',
          'admin.moves',
        ],
      },
    },
    {
      path: '/conflict',
      name: 'conflict',
      component: DomainView,
      props: {
        domain: 'conflict',
        titleKey: 'nav.conflict',
        introKey: 'domains.conflictIntro',
        metricIds: ['reverts.count', 'reverts.rate'],
      },
    },
    {
      path: '/automation',
      name: 'automation',
      component: DomainView,
      props: {
        domain: 'automation',
        titleKey: 'nav.automation',
        introKey: 'domains.automationIntro',
        metricIds: [
          'automation.bot_edit_share',
          'edits.group_bot',
          'edits.name_bot',
          'edits.user',
        ],
      },
    },
    { path: '/context', name: 'context', component: ContextView },
    { path: '/signals/:metricId', name: 'signal', component: SignalDrillView },
    { path: '/compare', name: 'compare', component: CompareView },
    { path: '/history', name: 'history', component: HistoryView },
    { path: '/methodology', name: 'methodology', component: MethodologyView },
    { path: '/privacy', name: 'privacy', component: PrivacyView },
    // Soft redirects of old activity-first routes
    { path: '/editors', redirect: '/context' },
    { path: '/content', redirect: '/context' },
    { path: '/overview', redirect: '/' },
    { path: '/reverts', redirect: '/conflict' },
    { path: '/funnel', name: 'funnel', component: FunnelView },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
