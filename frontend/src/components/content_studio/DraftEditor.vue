<template>
  <div class="flex h-full flex-col gap-4">
    <!-- Title input -->
    <div>
      <label class="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Title
      </label>
      <input
        :value="title"
        @input="$emit('update:title', $event.target.value)"
        type="text"
        placeholder="Give this piece a clear, specific title"
        class="w-full rounded-2xl border border-zinc-200 bg-white px-5 py-4 text-2xl font-semibold leading-tight text-zinc-900 outline-none transition-colors placeholder:text-zinc-400 focus:border-rose-400 focus:ring-2 focus:ring-rose-100"
      />
    </div>

    <!-- Tab toggle -->
    <div class="flex items-center gap-1 rounded-full border border-zinc-200 bg-white p-1 self-start">
      <button
        type="button"
        class="rounded-full px-4 py-1.5 text-xs font-semibold transition-colors"
        :class="mode === 'edit' ? 'bg-zinc-900 text-white' : 'text-zinc-500 hover:text-zinc-900'"
        @click="mode = 'edit'"
      >
        Edit
      </button>
      <button
        type="button"
        class="rounded-full px-4 py-1.5 text-xs font-semibold transition-colors"
        :class="mode === 'preview' ? 'bg-zinc-900 text-white' : 'text-zinc-500 hover:text-zinc-900'"
        @click="mode = 'preview'"
      >
        Preview
      </button>
    </div>

    <!-- Body editor / preview -->
    <div class="flex-1">
      <textarea
        v-if="mode === 'edit'"
        :value="body"
        @input="$emit('update:body', $event.target.value)"
        spellcheck="true"
        class="block h-full min-h-[480px] w-full resize-y rounded-2xl border border-zinc-200 bg-white px-5 py-4 font-mono text-[14px] leading-relaxed text-zinc-900 outline-none transition-colors placeholder:text-zinc-400 focus:border-rose-400 focus:ring-2 focus:ring-rose-100"
        placeholder="Start writing in markdown..."
      ></textarea>
      <div
        v-else
        class="h-full min-h-[480px] overflow-auto rounded-2xl border border-zinc-200 bg-white px-6 py-5 text-[15px] leading-relaxed text-zinc-800"
      >
        <pre class="whitespace-pre-wrap font-sans">{{ body || 'Nothing to preview yet.' }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  title: { type: String, default: '' },
  body: { type: String, default: '' },
})

defineEmits(['update:title', 'update:body'])

const mode = ref('edit')
</script>
