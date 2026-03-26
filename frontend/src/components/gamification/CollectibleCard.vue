<template>
  <div
    class="collectible-card"
    :class="[card.rarity, { locked: !card.earned, 'is-new': card.is_new }]"
    @click="$emit('select', card)"
  >
    <div class="card-inner">
      <!-- Front -->
      <div class="card-front">
        <div class="card-art">
          <img
            v-if="card.earned && card.image"
            :src="card.image"
            :alt="card.name"
            class="card-image"
          />
          <div v-else class="card-locked">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
          </div>
        </div>
        <div class="card-info">
          <span class="card-name">{{ card.earned ? card.name : '???' }}</span>
          <span class="card-points">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4z" />
            </svg>
            {{ card.point_value }} pts
          </span>
        </div>
        <div class="rarity-badge">{{ card.rarity }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  card: { type: Object, required: true },
})
defineEmits(['select'])
</script>

<style scoped>
/* Rarity color tokens */
.collectible-card { --rarity-color: #94a3b8; }
.collectible-card.rare { --rarity-color: #3b82f6; }
.collectible-card.epic { --rarity-color: #a855f7; }
.collectible-card.legendary { --rarity-color: #f59e0b; }

.collectible-card {
  perspective: 600px;
  cursor: pointer;
  transition: transform 300ms cubic-bezier(0.23, 1, 0.32, 1);
}

.collectible-card:hover {
  transform: translateY(-4px) scale(1.02);
}

.collectible-card:active {
  transform: scale(0.97);
}

.card-inner {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  background: var(--bg-card);
  border: 2px solid var(--rarity-color);
  box-shadow:
    0 2px 8px rgba(0,0,0,0.08),
    0 0 0 1px rgba(0,0,0,0.04);
  transition: box-shadow 300ms ease, border-color 300ms ease;
}

.collectible-card:hover .card-inner {
  box-shadow:
    0 8px 24px rgba(0,0,0,0.12),
    0 0 20px color-mix(in srgb, var(--rarity-color) 30%, transparent);
}

.collectible-card.legendary .card-inner {
  box-shadow:
    0 2px 8px rgba(0,0,0,0.08),
    0 0 12px color-mix(in srgb, var(--rarity-color) 20%, transparent);
}

.card-art {
  aspect-ratio: 1 / 1;
  overflow: hidden;
  background: var(--bg-surface);
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 300ms ease;
}

.collectible-card:hover .card-image {
  transform: scale(1.05);
}

.card-locked {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--text-muted);
  background: var(--bg-surface);
}

.locked .card-art {
  filter: grayscale(1) brightness(0.7);
}

.card-info {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-name {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.locked .card-name {
  color: var(--text-muted);
}

.card-points {
  font-size: var(--font-xs);
  color: var(--rarity-color);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.rarity-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--rarity-color);
  color: white;
}

/* New card shimmer */
.is-new .card-inner::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 40%,
    rgba(255,255,255,0.3) 50%,
    transparent 60%
  );
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
  pointer-events: none;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
