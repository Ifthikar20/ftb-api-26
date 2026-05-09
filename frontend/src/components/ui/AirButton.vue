<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'primary' },
  size: { type: String, default: 'md' },
  block: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  iconLeft: { type: String, default: null },
  iconRight: { type: String, default: null },
  as: { type: String, default: 'button' },
  to: { type: [String, Object], default: null },
  href: { type: String, default: null },
  type: { type: String, default: 'button' }
})

defineEmits(['click'])

const tag = computed(() => {
  if (props.as === 'router-link') return 'router-link'
  if (props.as === 'a') return 'a'
  return 'button'
})

const isDisabled = computed(() => props.disabled || props.loading)

const classes = computed(() => [
  'air-btn',
  `air-btn--${props.variant}`,
  `air-btn--${props.size}`,
  {
    'air-btn--block': props.block,
    'air-btn--loading': props.loading,
    'air-btn--disabled': isDisabled.value
  }
])
</script>

<template>
  <component
    :is="tag"
    :class="classes"
    :type="tag === 'button' ? type : undefined"
    :to="tag === 'router-link' ? to : undefined"
    :href="tag === 'a' ? href : undefined"
    :disabled="tag === 'button' ? isDisabled : undefined"
    :aria-disabled="isDisabled || undefined"
    :aria-busy="loading || undefined"
    @click="(e) => !isDisabled && $emit('click', e)"
  >
    <span v-if="loading" class="air-btn__spinner" aria-hidden="true"></span>
    <span v-else-if="iconLeft || $slots.iconLeft" class="air-btn__icon air-btn__icon--left">
      <slot name="iconLeft">
        <span v-html="iconLeft"></span>
      </slot>
    </span>
    <span class="air-btn__label"><slot /></span>
    <span v-if="iconRight || $slots.iconRight" class="air-btn__icon air-btn__icon--right">
      <slot name="iconRight">
        <span v-html="iconRight"></span>
      </slot>
    </span>
  </component>
</template>
