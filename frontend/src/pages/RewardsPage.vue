<template>
  <div class="rewards-page fade-in">
    <div v-if="loading" class="loading-state">Loading rewards...</div>
    <template v-else>
      <!-- Header Banner -->
      <div class="rewards-header">
        <div class="header-left">
          <h1 class="rewards-title">🏆 Rewards</h1>
          <p class="rewards-sub">Collect cards by hitting growth milestones. Level up your marketing game!</p>
        </div>
      </div>

      <!-- Progress Card -->
      <div class="progress-card stagger-enter">
        <div class="level-badge">
          <span class="level-num">{{ progress.current_level }}</span>
          <span class="level-label">Level</span>
        </div>
        <div class="progress-details">
          <div class="progress-header">
            <span class="progress-points">{{ progress.total_points }} / {{ progress.next_level_points }} pts</span>
            <span class="progress-cards">{{ progress.cards_collected }} cards collected</span>
          </div>
          <div class="xp-bar">
            <div class="xp-fill" :style="{ width: progress.progress_pct + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Card Collection Grid -->
      <div class="collection-section">
        <h2 class="section-title">Your Collection</h2>
        <div class="rarity-filter">
          <button
            v-for="r in rarityFilters"
            :key="r.value"
            class="filter-btn"
            :class="{ active: activeFilter === r.value }"
            @click="activeFilter = r.value"
          >{{ r.label }}</button>
        </div>
        <div class="card-grid stagger-enter">
          <CollectibleCard
            v-for="card in filteredCards"
            :key="card.id"
            :card="card"
            @select="openCard"
          />
        </div>
      </div>

      <!-- Card Detail Modal -->
      <Teleport to="body">
        <div v-if="selectedCard" class="modal-overlay" @click.self="selectedCard = null">
          <div class="card-modal" :class="selectedCard.rarity">
            <button class="modal-close" @click="selectedCard = null">&times;</button>
            <div class="modal-art">
              <img
                v-if="selectedCard.earned && selectedCard.image"
                :src="selectedCard.image"
                :alt="selectedCard.name"
              />
              <div v-else class="modal-locked-art">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
              </div>
            </div>
            <div class="modal-info">
              <div class="modal-rarity" :style="{ color: rarityColor(selectedCard.rarity) }">
                {{ selectedCard.rarity }}
              </div>
              <h3 class="modal-name">{{ selectedCard.earned ? selectedCard.name : '???' }}</h3>
              <p class="modal-desc">{{ selectedCard.earned ? selectedCard.description : selectedCard.milestone_description }}</p>
              <div class="modal-points">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4z" />
                </svg>
                {{ selectedCard.point_value }} points
              </div>
              <div class="modal-status" :class="selectedCard.earned ? 'earned' : 'locked'">
                {{ selectedCard.earned ? '✓ Earned' : '🔒 ' + selectedCard.milestone_title }}
              </div>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import gamificationApi from '@/api/gamification'
import CollectibleCard from '@/components/gamification/CollectibleCard.vue'

const loading = ref(true)
const progress = ref({ total_points: 0, current_level: 1, cards_collected: 0, next_level_points: 100, progress_pct: 0 })
const cards = ref([])
const selectedCard = ref(null)
const activeFilter = ref('all')

const rarityFilters = [
  { value: 'all', label: 'All' },
  { value: 'common', label: 'Common' },
  { value: 'rare', label: 'Rare' },
  { value: 'epic', label: 'Epic' },
  { value: 'legendary', label: 'Legendary' },
]

const filteredCards = computed(() => {
  if (activeFilter.value === 'all') return cards.value
  return cards.value.filter(c => c.rarity === activeFilter.value)
})

const rarityColor = (rarity) => {
  const map = { common: '#94a3b8', rare: '#3b82f6', epic: '#a855f7', legendary: '#f59e0b' }
  return map[rarity] || '#94a3b8'
}

const openCard = (card) => {
  selectedCard.value = card
}

onMounted(async () => {
  try {
    const [progressRes, cardsRes] = await Promise.all([
      gamificationApi.progress(),
      gamificationApi.cards(),
    ])
    progress.value = progressRes.data?.data || progressRes.data
    cards.value = cardsRes.data?.data || cardsRes.data || []
  } catch (e) {
    console.error('Rewards load error', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.rewards-page { max-width: 1200px; }

.loading-state {
  text-align: center;
  padding: 80px 20px;
  font-size: var(--font-md);
  color: var(--text-muted);
}

/* Header */
.rewards-header {
  margin-bottom: 24px;
}
.rewards-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.rewards-sub {
  font-size: var(--font-sm);
  color: var(--text-muted);
  margin-top: 4px;
}

/* Progress */
.progress-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
  box-shadow: var(--shadow-card);
}

.level-badge {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: white;
}
.level-num { font-size: 1.5rem; font-weight: 800; line-height: 1; }
.level-label { font-size: 0.6rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.9; }

.progress-details { flex: 1; }
.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.progress-points { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }
.progress-cards { font-size: var(--font-xs); color: var(--text-muted); }

.xp-bar {
  height: 8px;
  background: var(--bg-surface);
  border-radius: 4px;
  overflow: hidden;
}
.xp-fill {
  height: 100%;
  background: linear-gradient(90deg, #f59e0b, #f97316);
  border-radius: 4px;
  transition: width 600ms cubic-bezier(0.23, 1, 0.32, 1);
}

/* Collection */
.collection-section { margin-top: 8px; }
.section-title {
  font-size: var(--font-md);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.rarity-filter {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.filter-btn {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: var(--font-xs);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.filter-btn:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}
.filter-btn.active {
  background: var(--text-primary);
  color: var(--bg-card);
  border-color: var(--text-primary);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 20px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: fadeIn 200ms ease;
}

.card-modal {
  --modal-rarity: #94a3b8;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  max-width: 360px;
  width: 100%;
  overflow: hidden;
  position: relative;
  box-shadow: 0 16px 48px rgba(0,0,0,0.2);
  animation: slideUp 300ms cubic-bezier(0.23, 1, 0.32, 1);
}
.card-modal.rare { --modal-rarity: #3b82f6; }
.card-modal.epic { --modal-rarity: #a855f7; }
.card-modal.legendary { --modal-rarity: #f59e0b; }

.modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
  background: rgba(0,0,0,0.5);
  border: none;
  color: white;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-art {
  aspect-ratio: 1 / 1;
  background: var(--bg-surface);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.modal-locked-art {
  color: var(--text-muted);
}

.modal-info {
  padding: 20px;
}
.modal-rarity {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 4px;
}
.modal-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.modal-desc {
  font-size: var(--font-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
}
.modal-points {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--modal-rarity);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}
.modal-status {
  font-size: var(--font-xs);
  font-weight: 600;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  display: inline-block;
}
.modal-status.earned {
  background: var(--color-success-bg);
  color: var(--color-success);
}
.modal-status.locked {
  background: var(--bg-surface);
  color: var(--text-muted);
}

@media (max-width: 640px) {
  .card-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .progress-card { flex-direction: column; text-align: center; }
}
</style>
