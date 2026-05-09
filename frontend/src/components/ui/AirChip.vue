<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'neutral' },
  size: { type: String, default: 'sm' },
  closable: { type: Boolean, default: false },
  as: { type: String, default: 'span' }
})

defineEmits(['close', 'click'])

const tag = computed(() => (props.as === 'button' ? 'button' : 'span'))

const classes = computed(() => [
  'air-chip',
  `air-chip--${props.variant}`,
  `air-chip--${props.size}`
])
</script>

<template>
  <component
    :is="tag"
    :class="classes"
    :type="tag === 'button' ? 'button' : undefined"
    @click="(e) => $emit('click', e)"
  >
    <slot />
    <button
      v-if="closable"
      type="button"
      class="air-chip__close"
      aria-label="Remove"
      @click.stop="$emit('close')"
    >
      &times;
    </button>
  </component>
</template>
