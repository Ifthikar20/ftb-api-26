<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({
  size: { type: String, default: 'md' },
  interactive: { type: Boolean, default: false },
  as: { type: String, default: 'div' },
  to: { type: [String, Object], default: null },
  href: { type: String, default: null },
  padded: { type: Boolean, default: true }
})

defineEmits(['click'])
const slots = useSlots()

const tag = computed(() => {
  if (props.as === 'router-link') return 'router-link'
  if (props.as === 'a') return 'a'
  if (props.as === 'button') return 'button'
  return 'div'
})

const hasMedia = computed(() => !!slots.media)

const classes = computed(() => [
  'air-card',
  `air-card--${props.size}`,
  {
    'air-card--interactive': props.interactive,
    'air-card--unpadded': !props.padded,
    'air-card--has-media': hasMedia.value
  }
])
</script>

<template>
  <component
    :is="tag"
    :class="classes"
    :to="tag === 'router-link' ? to : undefined"
    :href="tag === 'a' ? href : undefined"
    :type="tag === 'button' ? 'button' : undefined"
    @click="(e) => $emit('click', e)"
  >
    <div v-if="hasMedia" class="air-card__media">
      <slot name="media" />
    </div>
    <div class="air-card__body">
      <div v-if="$slots.header" class="air-card__header">
        <slot name="header" />
      </div>
      <slot />
      <div v-if="$slots.footer" class="air-card__footer">
        <slot name="footer" />
      </div>
    </div>
  </component>
</template>
