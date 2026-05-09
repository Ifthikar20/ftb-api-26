<template>
  <div
    class="group relative flex items-center gap-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition-all duration-150 ease-out hover:-translate-y-0.5 hover:shadow-md"
  >
    <div
      class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-zinc-50 text-zinc-700"
      v-html="providerIcon"
    ></div>
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <h4 class="truncate text-[15px] font-medium text-zinc-900">
          {{ target.label || providerLabel }}
        </h4>
        <span
          v-if="target.is_default"
          class="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-rose-600"
        >
          Default
        </span>
        <span
          v-if="!target.is_active"
          class="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-500"
        >
          Disabled
        </span>
      </div>
      <p class="mt-0.5 text-xs text-zinc-500">{{ providerLabel }}</p>
    </div>
    <div class="hidden items-center gap-1 group-hover:flex">
      <button
        type="button"
        class="rounded-full p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
        title="Edit"
        @click="$emit('edit', target)"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9.5 2L12 4.5 5 11.5 2 12l.5-3z" />
        </svg>
      </button>
      <button
        type="button"
        class="rounded-full p-2 text-zinc-500 hover:bg-rose-50 hover:text-rose-600"
        title="Delete"
        @click="$emit('delete', target)"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2.5 4h9M5.5 4V2.5h3V4M3.5 4l.5 7.5h6L10.5 4" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  target: { type: Object, required: true },
})
defineEmits(['edit', 'delete'])

const PROVIDERS = {
  webhook: {
    label: 'Webhook',
    icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="6" r="2.5"/><path d="M11 8.5l-3 5"/><circle cx="6" cy="16" r="2.5"/><path d="M8.5 16h7"/><circle cx="16" cy="16" r="2.5"/></svg>',
  },
  wordpress: {
    label: 'WordPress',
    icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="M3.5 8l4 11M14.5 19l4-11M3 11h16"/></svg>',
  },
  ghost: {
    label: 'Ghost',
    icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h16M3 9h16M3 13h10M3 17h16"/></svg>',
  },
  email: {
    label: 'Email',
    icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="16" height="12" rx="2"/><path d="M3 7l8 6 8-6"/></svg>',
  },
  github: {
    label: 'GitHub',
    icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M11 2c-5 0-9 4-9 9 0 4 2.6 7.4 6.2 8.6.4.1.6-.2.6-.4v-1.6c-2.5.5-3-1.2-3-1.2-.4-1-1-1.3-1-1.3-.8-.5.1-.5.1-.5 1 0 1.5 1 1.5 1 .8 1.5 2.2 1 2.7.8.1-.6.3-1 .6-1.3-2-.2-4-1-4-4.4 0-1 .3-1.7.9-2.3 0-.3-.4-1.2.1-2.4 0 0 .7-.2 2.4 1 .7-.2 1.5-.3 2.2-.3s1.5.1 2.2.3c1.7-1.2 2.4-1 2.4-1 .5 1.2.2 2.1.1 2.4.6.6.9 1.3.9 2.3 0 3.4-2 4.2-4 4.4.4.3.7.9.7 1.8v2.6c0 .2.2.5.6.4 3.6-1.2 6.2-4.6 6.2-8.6 0-5-4-9-9-9z"/></svg>',
  },
}

const providerKey = computed(() => (props.target.provider || 'webhook').toLowerCase())
const providerLabel = computed(() => PROVIDERS[providerKey.value]?.label || props.target.provider || 'Custom')
const providerIcon = computed(() => PROVIDERS[providerKey.value]?.icon || PROVIDERS.webhook.icon)
</script>
