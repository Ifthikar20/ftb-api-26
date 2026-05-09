<template>
  <div class="relative">
    <input
      v-model="query"
      type="text"
      :placeholder="placeholder"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      @focus="open = true"
      @blur="onBlur"
    />
    <ul
      v-if="open && filtered.length"
      class="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg"
    >
      <li
        v-for="industry in filtered"
        :key="industry.id"
        class="cursor-pointer px-3 py-2 text-sm hover:bg-indigo-50"
        @mousedown.prevent="select(industry)"
      >
        {{ industry.name }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import promptLibrary from '@/api/promptLibrary'

const props = defineProps({
  modelValue: { type: [String, Object], default: null },
  placeholder: { type: String, default: 'Select an industry' },
})

const emit = defineEmits(['update:modelValue', 'select'])

const industries = ref([])
const query = ref('')
const open = ref(false)
const selected = ref(null)

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return industries.value
  return industries.value.filter((i) => i.name.toLowerCase().includes(q))
})

function select(industry) {
  selected.value = industry
  query.value = industry.name
  open.value = false
  emit('update:modelValue', industry.id)
  emit('select', industry)
}

function onBlur() {
  // Defer so a click on a list item registers before the dropdown closes.
  setTimeout(() => {
    open.value = false
  }, 120)
}

async function load() {
  try {
    const { data } = await promptLibrary.getIndustries()
    industries.value = Array.isArray(data) ? data : (data?.results || data?.data || [])
  } catch (err) {
    industries.value = []
  }
}

onMounted(load)

watch(
  () => props.modelValue,
  (val) => {
    if (!val) return
    const match = industries.value.find((i) => i.id === val)
    if (match) {
      selected.value = match
      query.value = match.name
    }
  },
)
</script>
