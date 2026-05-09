<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[200] flex items-center justify-center bg-zinc-900/60 px-4"
      @click.self="close"
    >
      <div class="w-full max-w-lg rounded-3xl bg-white p-8 shadow-lg">
        <div class="mb-6 flex items-start justify-between">
          <div>
            <h2 class="text-xl font-semibold tracking-tight text-zinc-900">
              {{ isEdit ? 'Edit publish target' : 'Add a publish target' }}
            </h2>
            <p class="mt-1 text-sm text-zinc-500">
              Choose where approved drafts should land.
            </p>
          </div>
          <button
            type="button"
            class="rounded-full p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
            aria-label="Close"
            @click="close"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M3 3l8 8M11 3l-8 8" />
            </svg>
          </button>
        </div>

        <!-- Provider radio cards -->
        <div class="mb-6">
          <label class="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Provider
          </label>
          <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <button
              v-for="p in providers"
              :key="p.value"
              type="button"
              class="flex flex-col items-center gap-1.5 rounded-2xl border p-4 text-center transition-all duration-150 ease-out"
              :class="form.provider === p.value
                ? 'border-rose-500 bg-rose-50/60 text-rose-700 shadow-sm'
                : 'border-zinc-200 bg-white text-zinc-700 hover:border-zinc-300 hover:-translate-y-0.5 hover:shadow-sm'"
              @click="form.provider = p.value"
            >
              <span v-html="p.icon"></span>
              <span class="text-xs font-medium">{{ p.label }}</span>
            </button>
          </div>
        </div>

        <!-- Common fields -->
        <div class="mb-4">
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Label
          </label>
          <input
            v-model="form.label"
            type="text"
            class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm text-zinc-900 outline-none transition-colors focus:border-rose-400 focus:ring-2 focus:ring-rose-100"
            placeholder="e.g. Marketing blog"
          />
        </div>

        <!-- Per-provider config -->
        <div v-if="form.provider === 'webhook'" class="mb-4 grid gap-3">
          <div>
            <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">URL</label>
            <input v-model="form.config.url" type="url" placeholder="https://example.com/hook"
              class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
          </div>
          <div>
            <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Secret (optional)</label>
            <input v-model="form.config.secret" type="text" placeholder="Signing secret"
              class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
          </div>
        </div>

        <div v-else-if="form.provider === 'wordpress'" class="mb-4 grid gap-3">
          <div>
            <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Site URL</label>
            <input v-model="form.config.site_url" type="url" placeholder="https://yoursite.com"
              class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Username</label>
              <input v-model="form.config.username" type="text"
                class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">App password</label>
              <input v-model="form.config.app_password" type="password"
                class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
            </div>
          </div>
        </div>

        <div v-else-if="form.provider === 'ghost'" class="mb-4 grid gap-3">
          <div>
            <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Admin API URL</label>
            <input v-model="form.config.api_url" type="url"
              class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
          </div>
          <div>
            <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Admin API key</label>
            <input v-model="form.config.api_key" type="password"
              class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
          </div>
        </div>

        <div v-else-if="form.provider === 'email'" class="mb-4 grid gap-3">
          <div>
            <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Recipient</label>
            <input v-model="form.config.to" type="email" placeholder="editor@yourcompany.com"
              class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
          </div>
        </div>

        <div v-else-if="form.provider === 'github'" class="mb-4 grid gap-3">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Owner</label>
              <input v-model="form.config.owner" type="text"
                class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Repo</label>
              <input v-model="form.config.repo" type="text"
                class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
            </div>
          </div>
          <div>
            <label class="mb-1 block text-xs font-semibold uppercase tracking-wider text-zinc-500">Token</label>
            <input v-model="form.config.token" type="password"
              class="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100" />
          </div>
        </div>

        <!-- Flags -->
        <div class="mb-6 flex items-center gap-5">
          <label class="inline-flex items-center gap-2 text-sm text-zinc-700">
            <input type="checkbox" v-model="form.is_default" class="h-4 w-4 rounded text-rose-500 focus:ring-rose-400" />
            Set as default
          </label>
          <label class="inline-flex items-center gap-2 text-sm text-zinc-700">
            <input type="checkbox" v-model="form.is_active" class="h-4 w-4 rounded text-rose-500 focus:ring-rose-400" />
            Active
          </label>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            class="rounded-full px-5 py-2.5 text-sm font-semibold text-zinc-700 hover:bg-zinc-100"
            @click="close"
          >
            Cancel
          </button>
          <button
            type="button"
            class="rounded-full bg-rose-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-rose-600 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="saving"
            @click="submit"
          >
            {{ saving ? 'Saving...' : isEdit ? 'Save changes' : 'Add target' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  target: { type: Object, default: null },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const providers = [
  { value: 'webhook', label: 'Webhook', icon: '<svg width="20" height="20" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="6" r="2.5"/><path d="M11 8.5l-3 5"/><circle cx="6" cy="16" r="2.5"/><path d="M8.5 16h7"/><circle cx="16" cy="16" r="2.5"/></svg>' },
  { value: 'wordpress', label: 'WordPress', icon: '<svg width="20" height="20" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="M3.5 8l4 11M14.5 19l4-11M3 11h16"/></svg>' },
  { value: 'ghost', label: 'Ghost', icon: '<svg width="20" height="20" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h16M3 9h16M3 13h10M3 17h16"/></svg>' },
  { value: 'email', label: 'Email', icon: '<svg width="20" height="20" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="16" height="12" rx="2"/><path d="M3 7l8 6 8-6"/></svg>' },
  { value: 'github', label: 'GitHub', icon: '<svg width="20" height="20" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M11 2C6 2 2 6 2 11c0 4 2.6 7.4 6.2 8.6.4.1.6-.2.6-.4v-1.6c-2.5.5-3-1.2-3-1.2-.4-1-1-1.3-1-1.3-.8-.5.1-.5.1-.5 1 0 1.5 1 1.5 1 .8 1.5 2.2 1 2.7.8.1-.6.3-1 .6-1.3-2-.2-4-1-4-4.4 0-1 .3-1.7.9-2.3 0-.3-.4-1.2.1-2.4 0 0 .7-.2 2.4 1 1.4-.4 2.9-.4 4.3 0 1.7-1.2 2.4-1 2.4-1 .5 1.2.2 2.1.1 2.4.6.6.9 1.3.9 2.3 0 3.4-2 4.2-4 4.4.4.3.7.9.7 1.8v2.6c0 .2.2.5.6.4C17.4 18.4 20 15 20 11c0-5-4-9-9-9z"/></svg>' },
]

const isEdit = computed(() => !!props.target?.id)

const form = reactive({
  provider: 'webhook',
  label: '',
  config: {},
  is_default: false,
  is_active: true,
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.target) {
      form.provider = props.target.provider || 'webhook'
      form.label = props.target.label || ''
      form.config = { ...(props.target.config || {}) }
      form.is_default = !!props.target.is_default
      form.is_active = props.target.is_active !== false
    } else {
      form.provider = 'webhook'
      form.label = ''
      form.config = {}
      form.is_default = false
      form.is_active = true
    }
  },
  { immediate: true },
)

watch(() => form.provider, () => {
  // Reset provider-specific config when switching providers (keep none cross-pollinated).
  form.config = {}
})

function close() {
  emit('update:modelValue', false)
}

function submit() {
  emit('submit', {
    provider: form.provider,
    label: form.label,
    config: form.config,
    is_default: form.is_default,
    is_active: form.is_active,
  })
}
</script>
