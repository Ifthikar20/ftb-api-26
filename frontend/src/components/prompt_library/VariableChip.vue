<script setup>
import { computed } from 'vue'
import AirChip from '@/components/ui/AirChip.vue'

const props = defineProps({
  name: { type: String, required: true },
  value: { type: [String, Number, null], default: null },
})

defineEmits(['request-edit'])

const resolved = computed(() => props.value !== null && props.value !== undefined && String(props.value).length > 0)
const variant = computed(() => (resolved.value ? 'info' : 'warning'))
const tooltip = computed(() =>
  resolved.value ? `{{ ${props.name} }} = ${props.value}` : `{{ ${props.name} }} not set — click to fill`,
)
</script>

<template>
  <AirChip
    as="button"
    size="xs"
    :variant="variant"
    :title="tooltip"
    @click="$emit('request-edit', name)"
  >
    <span v-if="resolved">{{ value }}</span>
    <span v-else>{{ name }}</span>
  </AirChip>
</template>
