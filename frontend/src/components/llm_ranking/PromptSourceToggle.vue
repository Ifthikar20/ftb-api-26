<template>
  <fieldset class="space-y-2">
    <legend class="text-sm font-medium text-gray-700">Prompt source</legend>
    <label
      v-for="opt in options"
      :key="opt.value"
      class="flex items-start gap-2 rounded-lg border border-gray-200 px-3 py-2 hover:border-indigo-400"
    >
      <input
        type="radio"
        :value="opt.value"
        :checked="modelValue === opt.value"
        class="mt-1"
        @change="$emit('update:modelValue', opt.value)"
      />
      <span>
        <span class="block text-sm font-medium text-gray-900">{{ opt.label }}</span>
        <span class="block text-xs text-gray-500">{{ opt.help }}</span>
      </span>
    </label>
  </fieldset>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: 'hybrid' },
})
defineEmits(['update:modelValue'])

const options = [
  {
    value: 'library',
    label: 'Demand-side library (recommended)',
    help: 'Real questions buyers ask AI assistants, mined from Reddit, search, and synthesis.',
  },
  {
    value: 'vault',
    label: 'My keywords only',
    help: 'Use the prompts generated from the keywords you provided.',
  },
  {
    value: 'hybrid',
    label: 'Mix both',
    help: 'Library prompts followed by your keyword prompts. Default.',
  },
]
</script>
