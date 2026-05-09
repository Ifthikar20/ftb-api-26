<script setup>
import AirButton from '@/components/ui/AirButton.vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirCardHeader from '@/components/ui/AirCardHeader.vue'
import AirCardTitle from '@/components/ui/AirCardTitle.vue'
import AirCardSubtitle from '@/components/ui/AirCardSubtitle.vue'
import AirCardFooter from '@/components/ui/AirCardFooter.vue'
import AirChip from '@/components/ui/AirChip.vue'

const variants = ['primary', 'secondary', 'ghost', 'outline', 'link', 'danger']
const sizes = ['xs', 'sm', 'md', 'lg', 'xl']
const cardSizes = ['sm', 'md', 'lg', 'hero']
const chipVariants = ['neutral', 'primary', 'success', 'warning', 'danger', 'info']
const chipSizes = ['xs', 'sm', 'md']
</script>

<template>
  <div class="mx-auto max-w-6xl p-6 md:p-8" style="color: var(--text-primary)">
    <header class="mb-10">
      <h1 class="text-3xl font-semibold tracking-tight">Design System</h1>
      <p class="mt-2 text-sm" style="color: var(--text-secondary)">
        Buttons, cards, and chips — Airbnb-inspired, brand-tokenized.
      </p>
    </header>

    <section class="mb-12">
      <h2 class="mb-4 text-xl font-semibold">Buttons</h2>
      <div
        v-for="variant in variants"
        :key="variant"
        class="mb-4 flex flex-wrap items-center gap-3"
      >
        <span class="w-24 text-xs uppercase tracking-wider" style="color: var(--text-secondary)">
          {{ variant }}
        </span>
        <AirButton v-for="s in sizes" :key="s" :variant="variant" :size="s">
          {{ s.toUpperCase() }} button
        </AirButton>
      </div>
      <div class="mt-6 flex flex-wrap items-center gap-3">
        <AirButton variant="primary" loading>Loading</AirButton>
        <AirButton variant="primary" disabled>Disabled</AirButton>
        <AirButton variant="primary" block class="max-w-xs">Block</AirButton>
      </div>
    </section>

    <section class="mb-12">
      <h2 class="mb-4 text-xl font-semibold">Cards</h2>
      <div class="grid gap-4 md:grid-cols-2">
        <AirCard v-for="s in cardSizes" :key="s" :size="s" interactive>
          <AirCardHeader>
            <div>
              <AirCardTitle>{{ s.toUpperCase() }} card</AirCardTitle>
              <AirCardSubtitle>Interactive — hover lifts</AirCardSubtitle>
            </div>
          </AirCardHeader>
          <p class="text-sm" style="color: var(--text-secondary)">
            Body content for the {{ s }} card. Generous whitespace, soft shadow.
          </p>
          <AirCardFooter>
            <span class="text-xs" style="color: var(--text-secondary)">Footer</span>
            <AirButton variant="primary" size="sm">Action</AirButton>
          </AirCardFooter>
        </AirCard>
      </div>
    </section>

    <section class="mb-12">
      <h2 class="mb-4 text-xl font-semibold">Chips</h2>
      <div
        v-for="size in chipSizes"
        :key="size"
        class="mb-3 flex flex-wrap items-center gap-2"
      >
        <span class="w-16 text-xs uppercase tracking-wider" style="color: var(--text-secondary)">
          {{ size }}
        </span>
        <AirChip v-for="v in chipVariants" :key="v" :variant="v" :size="size">
          {{ v }}
        </AirChip>
      </div>
    </section>
  </div>
</template>
