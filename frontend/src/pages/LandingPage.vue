<template>
  <div class="lp">
    <!-- ═══ Nav ═══ -->
    <nav class="nav" :class="{ scrolled }">
      <div class="wrap nav-row">
        <router-link to="/" class="brand">
          <img src="/images/fb-logo.png" alt="FetchBot" class="brand-logo" />
          <span class="brand-name">FetchBot</span>
          <span class="brand-beta">BETA</span>
        </router-link>
        <div class="nav-links">
          <a href="#features">Features</a>
          <a href="#how">How It Works</a>
          <a href="#pricing">Pricing</a>
          <router-link to="/integrations">Integrations</router-link>
        </div>
        <div class="nav-right">
          <router-link to="/login" class="nav-link-text">Log In</router-link>
          <router-link to="/register" class="nav-cta">Get Started</router-link>
        </div>
      </div>
    </nav>

    <!-- ═══ Hero ═══ -->
    <section class="hero">
      <div class="wrap">
        <h1 class="hero-h anim" data-anim="fade-up">
          <span class="tw-line" ref="twLine1"></span><br/>
          <span class="tw-line" ref="twLine2"></span><br/>
          <em><span class="tw-line" ref="twLine3"></span></em>
          <span class="tw-cursor" :class="{ 'tw-cursor--done': twDone }">|</span>
        </h1>
        <p class="hero-p anim" data-anim="fade-up" data-delay="60">
          Track visitors, score leads, audit your site, and grow<br class="hide-m"/>
          with AI — all in one platform.
        </p>
        <div class="hero-ctas anim" data-anim="fade-up" data-delay="120">
          <router-link to="/register" class="btn-primary">Get Started</router-link>
          <router-link to="/login" class="btn-ghost">Sign In</router-link>
        </div>
      </div>
    </section>

    <!-- ═══ Features — Travel Lab Carousel ═══ -->
    <section class="features-section" id="features">
      <div class="feat-full anim" data-anim="fade-up">
        <!-- Header row — Framer-style animated text -->
        <div class="feat-header wrap">
          <h2 class="feat-headline">
            OUR TOOLS FOR
            <span class="feat-word-cycler">
              <TransitionGroup name="word-cycle">
                <span class="feat-word" :key="categories[activeCat]">
                  {{ categories[activeCat] }}
                  <span class="feat-word-glow"></span>
                </span>
              </TransitionGroup>
            </span>
          </h2>
          <div class="feat-tabs">
            <button v-for="(cat, ci) in categories" :key="cat"
                    class="feat-tab" :class="{ active: ci === activeCat }"
                    @click="activeCat = ci; resetCycle()">{{ cat }}</button>
          </div>
        </div>

        <!-- Carousel -->
        <div class="carousel-wrap">
          <div class="carousel-track" ref="trackRef"
               :style="{ transform: `translateX(${trackOffset}px)` }">
            <div v-for="(f, i) in features" :key="f.title"
                 class="carousel-card" :class="[f.tint, { expanded: activeCard === i, 'is-playing': activeCard === i }]"
                 :style="{ animationDelay: `${i * 100}ms` }"
                 @click="activeCard = activeCard === i ? -1 : i"
                 @mouseenter="pauseAutoAdvance"
                 @mouseleave="resumeAutoAdvance">
              <span class="card-num">{{ String(i + 1).padStart(2, '0') }}</span>

              <!-- Per-tool animated visual -->
              <div class="card-visual">
                <!-- Analytics: line chart with drawing animation -->
                <div v-if="f.visual === 'chart'" class="viz viz-chart">
                  <div class="viz-stat">
                    <div class="viz-stat-value">{{ f.metric.value }}</div>
                    <div class="viz-stat-meta">
                      <span class="viz-stat-label">{{ f.metric.label }}</span>
                      <span class="viz-stat-delta up">{{ f.metric.delta }}</span>
                    </div>
                  </div>
                  <svg class="chart-svg" viewBox="0 0 220 70" preserveAspectRatio="none">
                    <defs>
                      <linearGradient :id="'g-' + i" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stop-color="#131718" stop-opacity="0.35"/>
                        <stop offset="100%" stop-color="#131718" stop-opacity="0"/>
                      </linearGradient>
                    </defs>
                    <path class="chart-area" :d="buildAreaPath(f.chart)" :fill="'url(#g-' + i + ')'" />
                    <path class="chart-line" :d="buildLinePath(f.chart)" fill="none" stroke="#131718" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
                    <circle class="chart-pulse" :cx="220" :cy="lastY(f.chart)" r="3" fill="#131718"/>
                  </svg>
                </div>

                <!-- Heatmaps: pulsing radial hotspots -->
                <div v-else-if="f.visual === 'heatmap'" class="viz viz-heatmap">
                  <div class="viz-stat">
                    <div class="viz-stat-value">{{ f.metric.value }}</div>
                    <div class="viz-stat-meta">
                      <span class="viz-stat-label">{{ f.metric.label }}</span>
                      <span class="viz-stat-delta">{{ f.metric.delta }}</span>
                    </div>
                  </div>
                  <div class="heatmap-canvas">
                    <div class="heatmap-cursor"></div>
                    <div
                      v-for="(h, hi) in f.hotspots"
                      :key="hi"
                      class="heat-blob"
                      :style="{
                        left: h.x + '%',
                        top: h.y + '%',
                        width: h.size + 'px',
                        height: h.size + 'px',
                        animationDelay: h.delay + 's',
                        opacity: h.intensity,
                      }"
                    ></div>
                  </div>
                </div>

                <!-- Keywords: animated rank bars -->
                <div v-else-if="f.visual === 'keywords'" class="viz viz-keywords">
                  <div class="viz-stat">
                    <div class="viz-stat-value">{{ f.metric.value }}</div>
                    <div class="viz-stat-meta">
                      <span class="viz-stat-label">{{ f.metric.label }}</span>
                      <span class="viz-stat-delta up">{{ f.metric.delta }}</span>
                    </div>
                  </div>
                  <div class="kw-list">
                    <div
                      v-for="(k, ki) in f.keywords"
                      :key="k.term"
                      class="kw-row"
                      :style="{ animationDelay: (0.15 + ki * 0.12) + 's' }"
                    >
                      <span class="kw-rank">#{{ k.rank }}</span>
                      <span class="kw-term">{{ k.term }}</span>
                      <span class="kw-bar">
                        <span class="kw-bar-fill" :style="{ width: k.score + '%', animationDelay: (0.25 + ki * 0.12) + 's' }"></span>
                      </span>
                      <span class="kw-delta">
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5">
                          <path d="M5 8V2M2 5l3-3 3 3"/>
                        </svg>
                        {{ k.prev - k.rank }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Lead ID: stacked company chips sliding in -->
                <div v-else-if="f.visual === 'leads'" class="viz viz-leads">
                  <div class="viz-stat">
                    <div class="viz-stat-value">{{ f.metric.value }}</div>
                    <div class="viz-stat-meta">
                      <span class="viz-stat-label">{{ f.metric.label }}</span>
                      <span class="viz-stat-delta up">{{ f.metric.delta }}</span>
                    </div>
                  </div>
                  <div class="lead-list">
                    <div
                      v-for="(l, li) in f.leads"
                      :key="l.domain"
                      class="lead-row"
                      :style="{ animationDelay: (0.2 + li * 0.14) + 's' }"
                    >
                      <div class="lead-avatar" :style="{ background: leadColors[li % leadColors.length] }">
                        {{ l.name[0] }}
                      </div>
                      <div class="lead-meta">
                        <div class="lead-name">{{ l.name }}</div>
                        <div class="lead-domain">{{ l.domain }}</div>
                      </div>
                      <span class="lead-score" :class="{ hot: l.hot }">{{ l.score }}</span>
                    </div>
                  </div>
                </div>

                <!-- LLM Ranking: provider visibility bars -->
                <div v-else-if="f.visual === 'llm'" class="viz viz-llm">
                  <div class="viz-stat">
                    <div class="viz-stat-value">{{ metricFor(f, i) }}</div>
                    <div class="viz-stat-meta">
                      <span class="viz-stat-label">{{ f.metric.label }}</span>
                      <span class="viz-stat-delta up">{{ f.metric.delta }}</span>
                    </div>
                  </div>
                  <div class="llm-list">
                    <div
                      v-for="(p, pi) in f.providers"
                      :key="p.name"
                      class="llm-row"
                      :style="{ animationDelay: (0.15 + pi * 0.12) + 's' }"
                    >
                      <span class="llm-icon">{{ p.icon }}</span>
                      <span class="llm-name">{{ p.name }}</span>
                      <span class="llm-bar">
                        <span class="llm-bar-fill" :class="p.tier" :style="{ width: p.score + '%', animationDelay: (0.25 + pi * 0.12) + 's' }"></span>
                      </span>
                      <span class="llm-score">{{ p.score }}%</span>
                    </div>
                  </div>
                </div>

                <!-- Fallback: icon -->
                <div v-else class="card-icon" v-html="f.icon"></div>
              </div>

              <h3 class="card-title">{{ f.title }}</h3>
              <div class="card-expand" :class="{ 'card-expand--open': activeCard === i }">
                <span class="card-arrow">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 12L12 4M12 4H5M12 4v7"/></svg>
                </span>
                <p class="card-desc">{{ f.desc }}</p>
                <span class="card-replaces">{{ f.replaces }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Nav arrows -->
        <div class="carousel-nav wrap">
          <button class="cn-btn" @click="scrollCarousel(-1)" :disabled="trackOffset >= 0">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M11 14L6 9l5-5"/></svg>
          </button>
          <span class="cn-counter">{{ Math.floor(-trackOffset / cardStep) + 1 }} / {{ features.length }}</span>
          <button class="cn-btn" @click="scrollCarousel(1)" :disabled="trackOffset <= -(features.length - visibleCards) * cardStep">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M7 4l5 5-5 5"/></svg>
          </button>
        </div>
      </div>
    </section>

    <!-- ═══ Our Tools For — Framer-style tool carousel ═══ -->
    <section class="tools-for" id="tools">
      <div class="wrap">
        <div class="tools-head">
          <span class="tools-eyebrow">OUR TOOLS FOR</span>
          <div class="tools-tabs" role="tablist">
            <button
              v-for="(tab, i) in toolTabs"
              :key="tab.id"
              :class="['tools-tab', { 'tools-tab-active': toolTab === i }]"
              type="button"
              @click="toolTab = i"
            >{{ tab.label }}</button>
          </div>
        </div>

        <div class="tools-grid">
          <article
            v-for="(card, i) in toolCards"
            :key="card.id"
            :class="['tool-card', `tool-card-${card.accent}`, { 'tool-card-active': toolIndex === i }]"
            @click="toolIndex = i"
          >
            <header class="tool-card-head">
              <span class="tool-num">{{ String(i + 1).padStart(2, '0') }}</span>
              <span class="tool-label">{{ card.label }}</span>
            </header>

            <div class="tool-metric">
              <div class="tool-metric-num">{{ card.mainValue }}</div>
              <div class="tool-metric-sub">{{ card.mainLabel }}</div>
              <span v-if="card.badge" :class="['tool-badge', card.badgeTone]">{{ card.badge }}</span>
            </div>

            <!-- Custom visual per card -->
            <div v-if="card.kind === 'keywords'" class="tool-viz tool-viz-list">
              <div v-for="k in card.items" :key="k.term" class="kw-row">
                <span :class="['kw-pos', posClass(k.pos)]">#{{ k.pos }}</span>
                <span class="kw-term">{{ k.term }}</span>
                <span class="kw-delta">{{ k.delta }}</span>
              </div>
            </div>

            <div v-else-if="card.kind === 'leads'" class="tool-viz tool-viz-list">
              <div v-for="c in card.items" :key="c.name" class="lead-row">
                <span class="lead-avatar">{{ c.name[0] }}</span>
                <span class="lead-meta">
                  <span class="lead-name">{{ c.name }}</span>
                  <span class="lead-domain">{{ c.domain }}</span>
                </span>
                <span :class="['lead-score', scoreTone(c.score)]">{{ c.score }}</span>
              </div>
            </div>

            <div v-else-if="card.kind === 'spark'" class="tool-viz tool-viz-spark">
              <svg viewBox="0 0 220 52" preserveAspectRatio="none" class="spark-svg">
                <path :d="card.path" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                <path :d="card.area" :fill="card.fill" opacity="0.1" />
              </svg>
            </div>

            <div v-else-if="card.kind === 'dots'" class="tool-viz tool-viz-dots">
              <span
                v-for="(d, di) in card.dots"
                :key="di"
                class="viz-dot"
                :style="{ top: d.y + '%', left: d.x + '%', transform: `scale(${d.size})` }"
              />
            </div>
          </article>
        </div>

        <div class="tools-bottom">
          <div class="tool-caption">
            <p class="tool-desc">{{ toolCards[toolIndex].desc }}</p>
            <span class="tool-replace">Replaces <strong>{{ toolCards[toolIndex].replaces }}</strong></span>
          </div>
          <div class="tool-pager">
            <button class="tool-arrow" type="button" @click="toolIndex = (toolIndex - 1 + toolCards.length) % toolCards.length" aria-label="Previous">
              <svg width="14" height="14" viewBox="0 0 16 16"><path d="M10 3L5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <span class="tool-count">{{ toolIndex + 1 }} / {{ toolCards.length }}</span>
            <button class="tool-arrow" type="button" @click="toolIndex = (toolIndex + 1) % toolCards.length" aria-label="Next">
              <svg width="14" height="14" viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ How It Works ═══ -->
    <section class="how" id="how">
      <div class="wrap">
        <h2 class="sec-h anim" data-anim="fade-up">Up and running<br/><em>in 3 minutes.</em></h2>
        <div class="steps">
          <div v-for="(s, i) in steps" :key="i" class="step anim" data-anim="fade-up" :data-delay="i * 80">
            <div class="step-num">{{ i + 1 }}</div>
            <h3>{{ s.title }}</h3>
            <p>{{ s.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Pricing ═══ -->
    <section class="pricing" id="pricing">
      <div class="wrap">
        <h2 class="sec-h anim" data-anim="fade-up">Simple pricing,<br/><em>no surprises.</em></h2>
        <div class="price-grid">
          <div v-for="(plan, i) in plans" :key="plan.name"
               class="price-card anim" data-anim="fade-up" :data-delay="i * 80"
               :class="{ featured: plan.featured }">
            <div class="pop" v-if="plan.featured">Popular</div>
            <h3>{{ plan.name }}</h3>
            <div class="price-amount">
              <span class="price-big">{{ plan.price }}</span>
              <span class="price-per" v-if="plan.per">/{{ plan.per }}</span>
            </div>
            <p class="price-desc">{{ plan.desc }}</p>
            <ul>
              <li v-for="f in plan.features" :key="f">{{ f }}</li>
            </ul>
            <router-link to="/register" class="price-btn" :class="{ dark: plan.featured }">{{ plan.cta }}</router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Final CTA ═══ -->
    <section class="final-cta anim" data-anim="fade-up">
      <div class="wrap cta-inner">
        <h2>Ready to grow <em>smarter?</em></h2>
        <p>Start your AI visibility audit in minutes.</p>
        <router-link to="/register" class="btn-primary">Get Started</router-link>
      </div>
    </section>

    <!-- ═══ Footer ═══ -->
    <footer class="footer">
      <div class="wrap footer-row">
        <div class="footer-brand">
          <img src="/images/fb-logo.png" alt="FetchBot" class="footer-logo" />
          <span>FetchBot</span>
        </div>
        <span class="footer-copy">2026 FetchBot. Privacy. Terms.</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const scrolled = ref(false)
const activeCard = ref(0)
const activeCat = ref(0)
const trackOffset = ref(0)
const trackRef = ref(null)

/* ── "Our tools for" section ── */
const toolTab = ref(3) // default to "SEO Intelligence" active
const toolTabs = [
  { id: 'seo', label: 'SEO' },
  { id: 'growth', label: 'Growth' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'seo-intel', label: 'SEO Intelligence' },
]

const toolIndex = ref(3) // default highlight "Lead ID"
const toolCards = [
  {
    id: 'analytics',
    label: 'Analytics',
    accent: 'blue',
    mainValue: '2,847',
    mainLabel: 'Visitors today',
    badge: '+18%',
    badgeTone: 'tone-pos',
    kind: 'spark',
    path: 'M0,40 L20,34 L40,32 L60,28 L80,30 L100,22 L120,18 L140,22 L160,14 L180,12 L200,8 L220,6',
    area: 'M0,40 L20,34 L40,32 L60,28 L80,30 L100,22 L120,18 L140,22 L160,14 L180,12 L200,8 L220,6 L220,52 L0,52 Z',
    fill: '#0a1f3d',
    desc: 'Track every visit, session, and source in real time — see what works without sampling.',
    replaces: 'Google Analytics',
  },
  {
    id: 'heatmaps',
    label: 'Heatmaps',
    accent: 'coral',
    mainValue: '4,132',
    mainLabel: 'Clicks tracked',
    badge: '12 hotspots',
    badgeTone: 'tone-neutral',
    kind: 'dots',
    dots: [
      { x: 22, y: 30, size: 1.4 },
      { x: 48, y: 22, size: 1.1 },
      { x: 72, y: 38, size: 1.8 },
      { x: 30, y: 60, size: 1.2 },
      { x: 60, y: 68, size: 2.2 },
      { x: 82, y: 58, size: 1 },
      { x: 12, y: 76, size: 0.9 },
      { x: 44, y: 80, size: 1.3 },
    ],
    desc: 'See exactly where users click, scroll, and hesitate. Ship UI changes with proof.',
    replaces: 'Hotjar',
  },
  {
    id: 'keywords',
    label: 'Keywords',
    accent: 'green',
    mainValue: '87',
    mainLabel: 'Tracked keywords',
    badge: '+4 new #1s',
    badgeTone: 'tone-pos',
    kind: 'keywords',
    items: [
      { pos: 3, term: 'ai analytics', delta: '4' },
      { pos: 1, term: 'visitor tracking', delta: '1' },
      { pos: 5, term: 'heatmap tool', delta: '6' },
      { pos: 2, term: 'lead scoring saas', delta: '2' },
    ],
    desc: 'Monitor rankings daily, catch movement before competitors, and own the SERP.',
    replaces: 'Ahrefs',
  },
  {
    id: 'lead-id',
    label: 'Lead ID',
    accent: 'rausch',
    mainValue: '23',
    mainLabel: 'Companies today',
    badge: '4 hot leads',
    badgeTone: 'tone-accent',
    kind: 'leads',
    items: [
      { name: 'Acme Corp', domain: 'acme.com', score: 94 },
      { name: 'Vector Labs', domain: 'vectorlabs.io', score: 81 },
      { name: 'Northwind Ltd', domain: 'northwind.co', score: 67 },
    ],
    desc: 'Identify companies visiting your site with behavioral scoring and company intel.',
    replaces: 'Clearbit',
  },
]

function posClass(pos) {
  if (pos === 1) return 'pos-1'
  if (pos <= 3) return 'pos-3'
  return 'pos-5'
}
function scoreTone(score) {
  if (score >= 90) return 'score-hot'
  if (score >= 75) return 'score-warm'
  return 'score-cool'
}

/* Typewriter refs */
const twLine1 = ref(null)
const twLine2 = ref(null)
const twLine3 = ref(null)
const twDone = ref(false)

const cardStep = 280
const visibleCards = 4
let cycleTimer = null
let featureTimer = null
const featureDwellMs = 4200

const leadColors = ['#131718', '#C65A2F', '#4A7FB0', '#5E6B73']

// ── Chart path helpers ──
const CHART_W = 220
const CHART_H = 70
function chartPoints(series) {
  const max = Math.max(...series, 1)
  const stepX = CHART_W / (series.length - 1 || 1)
  return series.map((v, i) => [i * stepX, CHART_H - (v / max) * (CHART_H - 6) - 3])
}
function buildLinePath(series) {
  const pts = chartPoints(series)
  if (!pts.length) return ''
  return pts.reduce((acc, [x, y], i) => acc + (i === 0 ? `M${x},${y}` : ` L${x},${y}`), '')
}
function buildAreaPath(series) {
  const line = buildLinePath(series)
  if (!line) return ''
  return `${line} L${CHART_W},${CHART_H} L0,${CHART_H} Z`
}
function lastY(series) {
  const pts = chartPoints(series)
  return pts.length ? pts[pts.length - 1][1] : CHART_H
}

function startFeatureAutoAdvance() {
  stopFeatureAutoAdvance()
  featureTimer = setInterval(() => {
    activeCard.value = (activeCard.value + 1) % features.length
  }, featureDwellMs)
}
function stopFeatureAutoAdvance() {
  if (featureTimer) { clearInterval(featureTimer); featureTimer = null }
}
function pauseAutoAdvance() { stopFeatureAutoAdvance() }
function resumeAutoAdvance() { startFeatureAutoAdvance() }

function scrollCarousel(dir) {
  const maxOffset = -(features.length - visibleCards) * cardStep
  trackOffset.value = Math.max(maxOffset, Math.min(0, trackOffset.value - dir * cardStep))
}

function startCycle() {
  cycleTimer = setInterval(() => {
    activeCat.value = (activeCat.value + 1) % categories.length
  }, 2800)
}

function resetCycle() {
  clearInterval(cycleTimer)
  startCycle()
}

/* Typewriter engine */
function typeWriter(el, text, speed = 65) {
  return new Promise(resolve => {
    let idx = 0
    function tick() {
      if (!el) { resolve(); return }
      if (idx <= text.length) {
        el.textContent = text.slice(0, idx)
        idx++
        setTimeout(tick, speed)
      } else {
        resolve()
      }
    }
    tick()
  })
}

async function runTypewriter() {
  await new Promise(r => setTimeout(r, 400)) // initial pause
  await typeWriter(twLine1.value, 'MARKETING', 80)
  await new Promise(r => setTimeout(r, 200))
  await typeWriter(twLine2.value, 'INTELLIGENCE,', 70)
  await new Promise(r => setTimeout(r, 200))
  await typeWriter(twLine3.value, 'SIMPLIFIED.', 70)
  await new Promise(r => setTimeout(r, 400))
  twDone.value = true
}

onMounted(() => {
  const onScroll = () => { scrolled.value = window.scrollY > 40 }
  window.addEventListener('scroll', onScroll, { passive: true })

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const d = parseInt(e.target.dataset.delay || '0')
        setTimeout(() => e.target.classList.add('in'), d)
        obs.unobserve(e.target)
      }
    })
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' })

  document.querySelectorAll('.anim').forEach(el => obs.observe(el))
  startCycle()
  runTypewriter()
  startFeatureAutoAdvance()

  onUnmounted(() => {
    window.removeEventListener('scroll', onScroll)
    obs.disconnect()
    clearInterval(cycleTimer)
    stopFeatureAutoAdvance()
  })
})

const categories = ['Growth', 'Analytics', 'SEO', 'Intelligence']

const features = [
  {
    title: 'Analytics',
    desc: 'Real-time visitors, pageviews, conversions, and user flow — with AI anomaly detection.',
    replaces: 'Replaces Mixpanel',
    tint: 'tint-peach',
    visual: 'chart',
    metric: { value: '2,847', label: 'Visitors today', delta: '+18%' },
    chart: [12, 28, 22, 40, 34, 56, 48, 70, 64, 82, 74, 96],
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M3 20V10l4-4 4 4 4-4 4 4v10" stroke-linejoin="round"/></svg>'
  },
  {
    title: 'Heatmaps',
    desc: 'See exactly where visitors click, scroll, and engage on every page of your website.',
    replaces: 'Replaces Hotjar',
    tint: 'tint-blue',
    visual: 'heatmap',
    metric: { value: '4,132', label: 'Clicks tracked', delta: '12 hotspots' },
    hotspots: [
      { x: 22, y: 30, size: 42, delay: 0,    intensity: 0.9 },
      { x: 62, y: 22, size: 28, delay: 0.35, intensity: 0.7 },
      { x: 78, y: 58, size: 50, delay: 0.7,  intensity: 1.0 },
      { x: 35, y: 70, size: 32, delay: 1.05, intensity: 0.55 },
      { x: 50, y: 48, size: 22, delay: 1.4,  intensity: 0.6 },
    ],
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="9" r="2"/><circle cx="16" cy="9" r="1.5" opacity=".5"/><circle cx="12" cy="15" r="2.5"/></svg>'
  },
  {
    title: 'Keywords',
    desc: 'AI keyword scoring, rank tracking, and Google Trends integration for every page.',
    replaces: 'Replaces Semrush',
    tint: 'tint-yellow',
    visual: 'keywords',
    metric: { value: '87', label: 'Tracked keywords', delta: '+4 new #1s' },
    keywords: [
      { term: 'ai analytics', rank: 3, prev: 7,  score: 92 },
      { term: 'visitor tracking', rank: 1, prev: 2, score: 88 },
      { term: 'heatmap tool', rank: 5, prev: 11, score: 74 },
      { term: 'lead scoring saas', rank: 2, prev: 4, score: 81 },
    ],
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg>'
  },
  {
    title: 'Lead ID',
    desc: 'Identify companies visiting your site with behavioral scoring and company intel.',
    replaces: 'Replaces Clearbit',
    tint: 'tint-peach',
    visual: 'leads',
    metric: { value: '23', label: 'Companies today', delta: '4 hot leads' },
    leads: [
      { name: 'Acme Corp',      domain: 'acme.com',    score: 94, hot: true },
      { name: 'Vector Labs',    domain: 'vectorlabs.io', score: 81, hot: true },
      { name: 'Northwind Ltd',  domain: 'northwind.co',  score: 67, hot: false },
    ],
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="12" cy="7" r="4"/><path d="M5.5 21c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/></svg>'
  },
  {
    title: 'LLM Ranking',
    desc: 'Audit your AI visibility across ChatGPT, Claude, Gemini & more — see if LLMs recommend your brand.',
    replaces: 'Nothing like it exists',
    tint: 'tint-violet',
    visual: 'llm',
    scene: 'aurora',
    metric: { value: '72', label: 'AI Visibility Score', delta: '+12 pts' },
    providers: [
      { name: 'ChatGPT',    icon: '🟢', score: 85, tier: 'tier-high' },
      { name: 'Claude',     icon: '🟣', score: 72, tier: 'tier-high' },
      { name: 'Gemini',     icon: '🔵', score: 58, tier: 'tier-mid' },
      { name: 'Perplexity', icon: '🟠', score: 41, tier: 'tier-low' },
    ],
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>'
  },
]

const steps = [
  { title: 'Add Your Website', desc: 'Enter your domain and we generate a tracking pixel instantly.' },
  { title: 'Install the Pixel', desc: 'Copy one line of JavaScript into your site header — takes 30 seconds.' },
  { title: 'Watch Insights Flow', desc: 'Real-time analytics and AI insights appear immediately.' },
]

const plans = [
  {
    name: 'Starter',
    price: '$39',
    per: 'mo',
    desc: 'For small companies & individuals.',
    features: [
      '5 websites',
      '100,000 pageviews/mo',
      'Full analytics + AI',
      'Heatmaps & funnels',
      'Lead identification',
      'Keyword tracking & SEO',
      '5-day free trial',
    ],
    cta: 'Start Free Trial',
    featured: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    per: '',
    desc: 'For teams & agencies.',
    features: [
      'Everything in Starter',
      'Unlimited projects & pageviews',
      'Unlimited AI credits',
      'SSO / SAML',
      'Full API access',
      'White-label reports',
      'Dedicated support & SLA',
    ],
    cta: 'Contact Sales',
    featured: false,
  },
]
</script>

<style scoped>
/* ═══════════════════════════════════
   FetchBot — Travel Lab style
   White bg · DM Serif Display headlines
   Horizontal numbered card carousel
   Typewriter hero · word cycler
   ═══════════════════════════════════ */

/* ── Animations ── */
.anim {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.65s cubic-bezier(0.22, 1, 0.36, 1),
              transform 0.65s cubic-bezier(0.22, 1, 0.36, 1);
}
.anim.in { opacity: 1; transform: none; }

/* ── Base ── */
.lp {
  background: #ffffff;
  color: #131718;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 1200px; margin: 0 auto; padding: 0 32px; }
em { color: #5B8DEF; font-style: italic; }
.hide-m {}

/* ── Nav ── */
.nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  padding: 16px 0;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  transition: all 0.3s ease;
}
.nav.scrolled { background: rgba(255,255,255,0.96); box-shadow: 0 1px 0 rgba(0,0,0,0.06); }
.nav-row { display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; }
.brand-logo { width: 36px; height: 36px; object-fit: contain; }
.brand-name { font-family: 'DM Serif Display', Georgia, serif; font-size: 20px; color: #131718; letter-spacing: -0.02em; }
.brand-beta {
  display: inline-block;
  background: #131718;
  color: #fcd34d;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-weight: 800;
  font-size: 10px;
  letter-spacing: 0.1em;
  padding: 3px 8px;
  border-radius: 999px;
  vertical-align: middle;
}
.hero-beta-note {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #475569;
  background: #fffbeb;
  border: 1px solid #fde68a;
  padding: 8px 14px;
  border-radius: 999px;
  margin: 18px 0 8px;
}
.nav-links { display: flex; gap: 32px; }
.nav-links a { font-size: 13px; font-weight: 500; color: #6e6a65; text-decoration: none; transition: color 0.2s; }
.nav-links a:hover { color: #131718; }
.nav-right { display: flex; align-items: center; gap: 8px; }
.nav-link-text { font-size: 13px; font-weight: 600; color: #6e6a65; padding: 8px 16px; text-decoration: none; transition: color 0.2s; }
.nav-link-text:hover { color: #131718; }
.nav-cta {
  font-size: 13px; font-weight: 700; color: #fff;
  background: #131718; padding: 9px 24px;
  border-radius: 999px; text-decoration: none;
  transition: all 0.25s;
}
.nav-cta:hover { background: #2a2d2e; transform: translateY(-1px); }

/* ── Hero ── */
.hero { padding: 160px 0 80px; }
.hero-h {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400; font-size: clamp(2.8rem, 6vw, 5.5rem);
  line-height: 1.05; letter-spacing: -0.03em;
  text-transform: uppercase;
  margin-bottom: 24px;
  min-height: 3.3em; /* prevent layout shift during typewriter */
}

/* Typewriter cursor */
.tw-line {
  display: inline;
}
.tw-cursor {
  display: inline-block;
  font-weight: 300;
  color: #5B8DEF;
  animation: tw-blink 0.6s step-end infinite;
  margin-left: 2px;
}
.tw-cursor--done {
  animation: tw-blink 1.2s step-end infinite;
  opacity: 0.5;
}
@keyframes tw-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.hero-p { font-size: 16px; color: #6e6a65; line-height: 1.7; max-width: 480px; margin-bottom: 32px; }
.hero-ctas { display: flex; gap: 12px; }
.btn-primary {
  padding: 14px 32px; background: #131718; color: #fff;
  border-radius: 999px; font-weight: 700; font-size: 14px;
  text-decoration: none; border: none; cursor: pointer;
  transition: all 0.25s;
}
.btn-primary:hover { background: #2a2d2e; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.12); }
.btn-ghost {
  padding: 14px 32px; background: transparent; color: #131718;
  border: 1.5px solid rgba(0,0,0,0.12); border-radius: 999px;
  font-weight: 700; font-size: 14px; text-decoration: none;
  transition: all 0.25s;
}
.btn-ghost:hover { border-color: #131718; }

/* ═══ Features Carousel — Travel Lab Style ═══ */
.features-section { padding: 64px 0 80px; }
.feat-full { background: #FFF6C6; border-radius: 24px; margin: 0 32px; padding: 48px 0 40px; overflow: hidden; }

.feat-header { display: flex; align-items: baseline; gap: 40px; margin-bottom: 36px; flex-wrap: wrap; }
.feat-headline {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: clamp(1.8rem, 3.5vw, 3rem);
  font-weight: 400; text-transform: uppercase;
  letter-spacing: -0.02em;
  display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap;
  line-height: 1.2;
}

/* ── Framer-style word cycler ── */
.feat-word-cycler {
  display: inline-flex;
  position: relative;
  min-width: 240px;
  height: 1.25em;
  vertical-align: baseline;
  overflow: hidden;
  align-items: flex-end;
}
.feat-word {
  display: inline-block;
  position: absolute;
  left: 0; bottom: 0;
  color: #5B8DEF;
  font-style: italic;
  white-space: nowrap;
  line-height: 1.2;
}
.feat-word-glow {
  position: absolute; bottom: -4px; left: 0; right: 0;
  height: 3px; background: #5B8DEF;
  border-radius: 2px;
  box-shadow: 0 0 12px rgba(91, 141, 239, 0.5), 0 0 24px rgba(91, 141, 239, 0.2);
  animation: glow-pulse 2.8s ease-in-out infinite;
}
@keyframes glow-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* Word cycle transition — slide up with blur */
.word-cycle-enter-active {
  transition: all 0.55s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.word-cycle-leave-active {
  transition: all 0.35s cubic-bezier(0.55, 0, 1, 0.45);
  position: absolute;
}
.word-cycle-enter-from {
  opacity: 0; transform: translateY(100%) scale(0.9);
  filter: blur(6px);
}
.word-cycle-enter-to {
  opacity: 1; transform: translateY(0) scale(1);
  filter: blur(0);
}
.word-cycle-leave-from {
  opacity: 1; transform: translateY(0) scale(1);
  filter: blur(0);
}
.word-cycle-leave-to {
  opacity: 0; transform: translateY(-80%) scale(0.9);
  filter: blur(6px);
}

.feat-tabs { display: flex; gap: 24px; }
.feat-tab {
  background: none; border: none; cursor: pointer;
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: clamp(1rem, 1.8vw, 1.3rem);
  font-style: italic; color: #94a3b8;
  padding: 0; transition: all 0.3s;
  position: relative;
}
.feat-tab.active {
  color: #5B8DEF;
  text-decoration: none;
}
.feat-tab.active::after {
  content: '';
  position: absolute;
  bottom: -4px; left: 0; right: 0;
  height: 2px;
  background: #5B8DEF;
  border-radius: 1px;
  animation: tab-slide-in 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes tab-slide-in {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}
.feat-tab:hover { color: #131718; }

/* Carousel track */
.carousel-wrap { overflow: hidden; padding: 0 32px; }
.carousel-track {
  display: flex; gap: 12px;
  transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

/* Individual card */
.carousel-card {
  flex: 0 0 260px; min-height: 320px;
  border-radius: 16px; padding: 24px 20px;
  cursor: pointer; position: relative;
  display: flex; flex-direction: column;
  transition: flex 0.45s cubic-bezier(0.22, 1, 0.36, 1),
              transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.3s ease;
  overflow: hidden;
  animation: card-entrance 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes card-entrance {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
.carousel-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}
.carousel-card.expanded {
  flex: 0 0 420px;
  min-height: 360px;
  box-shadow: 0 18px 48px rgba(0,0,0,0.14);
  transform: translateY(-4px);
}

/* ── Per-tool animated visuals ── */
.viz {
  position: relative;
  margin-bottom: auto;
  width: 100%;
}
.viz-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 10px;
}
.viz-stat-value {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400;
  font-size: 30px;
  color: #131718;
  line-height: 1;
  letter-spacing: -0.02em;
}
.viz-stat-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.viz-stat-label { color: #131718; opacity: 0.6; font-weight: 600; }
.viz-stat-delta {
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(19,23,24,0.08);
  color: #131718;
  font-weight: 700;
}
.viz-stat-delta.up { background: rgba(24,110,58,0.14); color: #186E3A; }

/* Chart (Analytics) */
.viz-chart { padding-right: 4px; }
.chart-svg {
  width: 100%;
  height: 70px;
  overflow: visible;
  display: block;
}
.chart-line {
  stroke-dasharray: 600;
  stroke-dashoffset: 600;
  transition: stroke-dashoffset 0s;
}
.chart-area { opacity: 0; }
.chart-pulse { opacity: 0; }
.is-playing .chart-line {
  animation: chart-draw 1.5s cubic-bezier(0.22, 1, 0.36, 1) 0.1s forwards;
}
.is-playing .chart-area {
  animation: fade-in 0.9s ease 0.9s forwards;
}
.is-playing .chart-pulse {
  animation: pulse-dot 1.4s ease-in-out 1.6s infinite;
}
@keyframes chart-draw {
  to { stroke-dashoffset: 0; }
}
@keyframes fade-in {
  to { opacity: 1; }
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); transform-origin: center; }
  50% { opacity: 0.25; transform: scale(1.8); }
}

/* Heatmap */
.viz-heatmap { }
.heatmap-canvas {
  position: relative;
  width: 100%;
  height: 110px;
  border-radius: 10px;
  background:
    repeating-linear-gradient(90deg, rgba(19,23,24,0.05) 0 1px, transparent 1px 36px),
    repeating-linear-gradient(0deg,  rgba(19,23,24,0.05) 0 1px, transparent 1px 24px),
    rgba(255,255,255,0.35);
  overflow: hidden;
}
.heat-blob {
  position: absolute;
  border-radius: 50%;
  transform: translate(-50%, -50%) scale(0.4);
  background: radial-gradient(circle, rgba(220,82,48,0.9) 0%, rgba(245,166,35,0.5) 45%, rgba(245,166,35,0) 75%);
  filter: blur(2px);
  opacity: 0;
  pointer-events: none;
}
.is-playing .heat-blob {
  animation: heat-pulse 2.1s ease-in-out infinite;
}
@keyframes heat-pulse {
  0%   { transform: translate(-50%, -50%) scale(0.4); opacity: 0; }
  30%  { opacity: 0.9; }
  60%  { transform: translate(-50%, -50%) scale(1.1); opacity: 0.9; }
  100% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
}
.heatmap-cursor {
  position: absolute;
  width: 10px; height: 10px;
  border-radius: 50%;
  border: 1.5px solid #131718;
  top: 25%; left: 15%;
  opacity: 0;
}
.is-playing .heatmap-cursor {
  animation: cursor-move 6s ease-in-out infinite;
}
@keyframes cursor-move {
  0%   { top: 25%;  left: 15%; opacity: 0; }
  10%  { opacity: 1; }
  25%  { top: 22%;  left: 62%; }
  50%  { top: 58%;  left: 78%; }
  75%  { top: 70%;  left: 35%; }
  95%  { top: 48%;  left: 50%; opacity: 1; }
  100% { top: 48%;  left: 50%; opacity: 0; }
}

/* Keywords */
.kw-list { display: flex; flex-direction: column; gap: 6px; }
.kw-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #131718;
  opacity: 0;
  transform: translateX(-8px);
}
.is-playing .kw-row {
  animation: kw-slide-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes kw-slide-in {
  to { opacity: 1; transform: translateX(0); }
}
.kw-rank {
  width: 24px;
  font-weight: 700;
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: 13px;
  letter-spacing: -0.02em;
}
.kw-term {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}
.kw-bar {
  position: relative;
  flex: 0 0 70px;
  height: 4px;
  border-radius: 2px;
  background: rgba(19,23,24,0.12);
  overflow: hidden;
}
.kw-bar-fill {
  display: block;
  height: 100%;
  background: #131718;
  border-radius: 2px;
  transform: scaleX(0);
  transform-origin: left center;
}
.is-playing .kw-bar-fill {
  animation: kw-bar-grow 0.9s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes kw-bar-grow {
  to { transform: scaleX(1); }
}
.kw-delta {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 10px;
  font-weight: 700;
  color: #186E3A;
  background: rgba(24,110,58,0.12);
  padding: 2px 5px;
  border-radius: 4px;
}

/* Lead ID */
.lead-list { display: flex; flex-direction: column; gap: 6px; }
.lead-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255,255,255,0.55);
  border: 1px solid rgba(19,23,24,0.06);
  opacity: 0;
  transform: translateY(8px);
}
.is-playing .lead-row {
  animation: lead-slide-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes lead-slide-in {
  to { opacity: 1; transform: translateY(0); }
}
.lead-avatar {
  width: 26px; height: 26px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 11px;
  flex-shrink: 0;
}
.lead-meta { flex: 1; min-width: 0; }
.lead-name { font-size: 12px; font-weight: 700; color: #131718; line-height: 1.2; }
.lead-domain { font-size: 10px; color: #131718; opacity: 0.55; }
.lead-score {
  font-size: 11px;
  font-weight: 800;
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(19,23,24,0.08);
  color: #131718;
}
.lead-score.hot {
  background: #DC5230;
  color: #fff;
  box-shadow: 0 0 0 0 rgba(220,82,48,0.7);
}
.is-playing .lead-score.hot {
  animation: lead-hot-pulse 1.8s ease-in-out 0.8s infinite;
}
@keyframes lead-hot-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220,82,48,0.6); }
  50%      { box-shadow: 0 0 0 6px rgba(220,82,48,0); }
}

/* Card tints — Travel Lab branding */
.carousel-card.tint-peach   { background: #FEC29F; }
.carousel-card.tint-blue    { background: #D1E6F6; }
.carousel-card.tint-yellow  { background: #FFF6C6; border: 1px solid rgba(0,0,0,0.06); }
.carousel-card.tint-pink    { background: #FFDAE4; }

/* Card inner elements */
.card-num {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: 2.2rem; font-weight: 400;
  color: #131718; line-height: 1;
  margin-bottom: 16px;
}
.card-visual { margin-bottom: auto; }
.card-icon {
  color: #131718; opacity: 0.7;
  transition: transform 0.3s ease;
}
.carousel-card:hover .card-icon {
  transform: scale(1.1);
}
.card-title {
  font-size: 18px; font-weight: 800;
  color: #131718; letter-spacing: -0.01em;
  margin-top: auto;
}

/* Expanded card details — smooth reveal */
.card-expand {
  margin-top: 0;
  max-height: 0;
  opacity: 0;
  overflow: hidden;
  transition: max-height 0.45s cubic-bezier(0.22, 1, 0.36, 1),
              opacity 0.35s ease,
              margin-top 0.35s ease;
}
.card-expand--open {
  max-height: 200px;
  opacity: 1;
  margin-top: 10px;
}
.card-arrow { display: flex; justify-content: flex-end; margin-bottom: 8px; }
.card-desc { font-size: 12px; color: #131718; opacity: 0.75; line-height: 1.5; margin-bottom: 10px; }
.card-replaces { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #131718; opacity: 0.4; }

/* Carousel nav */
.carousel-nav { display: flex; align-items: center; gap: 16px; margin-top: 28px; }
.cn-btn {
  width: 44px; height: 44px; border-radius: 50%;
  border: 1.5px solid #131718; background: transparent;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: #131718;
  transition: all 0.2s;
}
.cn-btn:hover { background: #131718; color: #fff; }
.cn-btn:disabled { opacity: 0.25; cursor: default; }
.cn-btn:disabled:hover { background: transparent; color: #131718; }
.cn-counter { font-size: 13px; font-weight: 600; color: #6e6a65; }

/* ── Section Headings ── */
.sec-h {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400; font-size: clamp(1.6rem, 3.5vw, 2.6rem);
  line-height: 1.1; margin-bottom: 48px;
}

/* ── How It Works ── */
.how { padding: 96px 0; background: #ffffff; }
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.step {
  background: #fff; border: 1px solid rgba(0,0,0,0.06);
  border-radius: 20px; padding: 32px 24px;
  transition: all 0.3s;
}
.step:hover { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(0,0,0,0.05); }
.step-num {
  width: 36px; height: 36px; border-radius: 50%;
  background: #131718; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 14px; margin-bottom: 16px;
}
.step h3 { font-size: 16px; font-weight: 800; margin-bottom: 6px; }
.step p { font-size: 13px; color: #6e6a65; line-height: 1.6; }

/* ── Pricing ── */
.pricing { padding: 96px 0; }
.price-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; max-width: 800px; margin: 0 auto; }
.price-card {
  display: flex; flex-direction: column;
  background: #fff; border: 1px solid rgba(0,0,0,0.06);
  border-radius: 20px; padding: 32px 24px;
  position: relative; transition: all 0.3s;
}
.price-card:hover { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(0,0,0,0.05); }
.price-card.featured { border-color: #5B8DEF; box-shadow: 0 4px 20px rgba(91,141,239,0.1); }
.pop {
  position: absolute; top: -11px; left: 50%; transform: translateX(-50%);
  padding: 3px 14px; background: #5B8DEF; color: #fff;
  border-radius: 999px; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.price-card h3 { font-size: 17px; font-weight: 800; margin-bottom: 8px; }
.price-big { font-family: 'DM Serif Display', Georgia, serif; font-size: 2.6rem; line-height: 1; }
.price-per { font-size: 13px; color: #a09a93; }
.price-desc { font-size: 12px; color: #6e6a65; margin: 6px 0 20px; }
.price-card ul { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 6px; margin-bottom: 24px; flex-grow: 1; }
.price-card li { font-size: 12px; color: #6e6a65; }
.price-btn {
  display: block; text-align: center; padding: 12px;
  border-radius: 999px; font-size: 13px; font-weight: 700;
  text-decoration: none; border: 1.5px solid rgba(0,0,0,0.1);
  color: #131718; transition: all 0.25s;
}
.price-btn:hover { border-color: #5B8DEF; color: #5B8DEF; }
.price-btn.dark { background: #131718; border-color: #131718; color: #fff; }
.price-btn.dark:hover { background: #2a2d2e; transform: translateY(-1px); }

/* ── Final CTA ── */
.final-cta { padding: 48px 0 80px; }
.cta-inner {
  text-align: center; background: #D1E6F6;
  border: none; border-radius: 24px;
  padding: 72px 40px;
}
.cta-inner h2 {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400; font-size: clamp(1.6rem, 3vw, 2.2rem);
  margin-bottom: 10px;
}
.cta-inner p { font-size: 15px; color: #6e6a65; margin-bottom: 28px; }

/* ── Footer ── */
.footer { padding: 24px 0; border-top: 1px solid rgba(0,0,0,0.06); }
.footer-row { display: flex; align-items: center; justify-content: space-between; }
.footer-brand { display: flex; align-items: center; gap: 8px; font-family: 'DM Serif Display', Georgia, serif; font-size: 16px; }
.footer-logo { width: 28px; height: 28px; object-fit: contain; }
.footer-copy { font-size: 11px; color: #a09a93; }

/* ── Responsive ── */
@media (max-width: 900px) {
  .nav-links { display: none; }
  .steps, .price-grid { grid-template-columns: 1fr; }
  .feat-header { flex-direction: column; gap: 16px; }
  .feat-full { margin: 0 16px; }
  .carousel-card { flex: 0 0 220px; min-height: 260px; }
  .carousel-card.expanded { flex: 0 0 280px; }
  .hide-m { display: none; }
  .feat-word-cycler { min-width: 160px; }
}
@media (max-width: 640px) {
  .hero-h { font-size: 2.4rem; min-height: auto; }
  .hero-ctas { flex-direction: column; align-items: flex-start; }
}

/* ──────────────────────────────────────────────────
   "Our Tools For" section — Airbnb-style cards
   Warm neutrals + per-card accent borders (rausch, coral,
   teal/babu, sky). Fonts: Geist + Inter.
   ────────────────────────────────────────────────── */
.tools-for {
  --ab-fg: #222222;
  --ab-fg-muted: #6a6a6a;
  --ab-fg-subtle: #b0b0b0;
  --ab-bg: #f7f7f7;
  --ab-card: #ffffff;
  --ab-hairline: #ebebeb;
  --ab-hairline-strong: #dddddd;
  --ab-rausch: #ff385c;
  --ab-coral: #e07856;
  --ab-babu: #00a699;
  --ab-sky: #428bca;
  --ab-arches: #fc642d;
  padding: 120px 0 100px;
  background: var(--ab-bg);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: var(--ab-fg);
}
.tools-for .wrap { max-width: 1200px; margin: 0 auto; padding: 0 24px; }

.tools-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  margin-bottom: 56px;
  flex-wrap: wrap;
}

.tools-eyebrow {
  font-family: 'Geist', 'Inter', system-ui, sans-serif;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.14em;
  color: var(--ab-fg-muted);
  text-transform: uppercase;
}

.tools-tabs {
  display: inline-flex;
  gap: 2px;
  padding: 4px;
  background: #ffffff;
  border: 1px solid var(--ab-hairline);
  border-radius: 999px;
}

.tools-tab {
  appearance: none;
  border: none;
  background: transparent;
  padding: 9px 18px;
  border-radius: 999px;
  font-family: 'Inter', sans-serif;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--ab-fg-muted);
  cursor: pointer;
  transition: all 0.18s ease;
}
.tools-tab:hover { color: var(--ab-fg); background: #f7f7f7; }
.tools-tab-active {
  background: var(--ab-fg);
  color: #ffffff;
}
.tools-tab-active:hover { background: var(--ab-fg); color: #ffffff; }

.tools-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
  margin-bottom: 48px;
}

/* Base tool card */
.tool-card {
  --accent: var(--ab-fg);
  --accent-soft: #f7f7f7;
  --accent-strong: #222222;
  position: relative;
  background: var(--ab-card);
  border: 1px solid var(--ab-hairline);
  border-radius: 16px;
  padding: 22px 22px 26px;
  cursor: pointer;
  transition: all 0.22s cubic-bezier(0.22, 1, 0.36, 1);
  min-height: 340px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.04);
}
.tool-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: var(--accent);
  border-top-left-radius: 16px;
  border-top-right-radius: 16px;
  opacity: 0.9;
}
.tool-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
  border-color: var(--accent);
}
.tool-card-active {
  border-color: var(--accent);
  box-shadow: 0 12px 32px -10px color-mix(in srgb, var(--accent) 28%, transparent), 0 2px 6px rgba(0, 0, 0, 0.06);
}
.tool-card-active::before { height: 6px; opacity: 1; }

/* Per-tool accents */
.tool-card-rausch { --accent: var(--ab-rausch); --accent-soft: #fff1f3; --accent-strong: #c01e3c; }
.tool-card-coral  { --accent: var(--ab-coral);  --accent-soft: #fdf2ec; --accent-strong: #a55436; }
.tool-card-green  { --accent: var(--ab-babu);   --accent-soft: #e6f6f4; --accent-strong: #007a72; }
.tool-card-blue   { --accent: var(--ab-sky);    --accent-soft: #eef4fb; --accent-strong: #2e63a1; }

.tool-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.tool-num {
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: var(--accent-strong);
  background: var(--accent-soft);
  padding: 3px 9px;
  border-radius: 6px;
}
.tool-label {
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--ab-fg-muted);
  text-transform: uppercase;
}

.tool-metric { margin-bottom: 18px; }
.tool-metric-num {
  font-family: 'Geist', 'Inter', sans-serif;
  font-size: 40px;
  font-weight: 500;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--ab-fg);
  margin-bottom: 4px;
}
.tool-metric-sub {
  font-size: 13.5px;
  color: var(--ab-fg-muted);
  margin-bottom: 10px;
}
.tool-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-family: 'Inter', sans-serif;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.tool-badge.tone-pos {
  background: #e6f6f4;
  color: #007a72;
}
.tool-badge.tone-neutral {
  background: #f2f2f2;
  color: #555555;
}
.tool-badge.tone-accent {
  background: var(--accent-soft);
  color: var(--accent-strong);
}

/* ── Keyword list ── */
.tool-viz-list { margin-top: auto; display: flex; flex-direction: column; gap: 6px; }
.kw-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  background: #fafafa;
  border: 1px solid var(--ab-hairline);
  border-radius: 8px;
  font-size: 12.5px;
}
.kw-pos {
  font-family: 'Geist', sans-serif;
  font-weight: 500;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  min-width: 26px;
  text-align: center;
  letter-spacing: 0.02em;
}
.kw-pos.pos-1 { background: #e6f6f4; color: #007a72; }
.kw-pos.pos-3 { background: #eef4fb; color: #2e63a1; }
.kw-pos.pos-5 { background: #f2f2f2; color: #555555; }
.kw-term { color: #333333; font-size: 12.5px; }
.kw-delta {
  font-family: 'Geist', sans-serif;
  font-size: 11px;
  color: var(--ab-fg-subtle);
}

/* ── Lead rows ── */
.lead-row {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  background: #fafafa;
  border: 1px solid var(--ab-hairline);
  border-radius: 8px;
}
.lead-avatar {
  display: inline-flex;
  width: 26px;
  height: 26px;
  align-items: center;
  justify-content: center;
  background: var(--ab-rausch);
  color: #ffffff;
  font-family: 'Geist', sans-serif;
  font-weight: 500;
  font-size: 11px;
  border-radius: 6px;
}
.lead-meta { display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }
.lead-name { font-size: 12.5px; font-weight: 600; color: var(--ab-fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lead-domain { font-size: 11px; color: var(--ab-fg-subtle); }
.lead-score {
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  min-width: 30px;
  text-align: center;
}
.lead-score.score-hot  { background: #fff1f3; color: var(--ab-rausch); }
.lead-score.score-warm { background: #fdf2ec; color: var(--ab-arches); }
.lead-score.score-cool { background: #f2f2f2; color: #555555; }

/* ── Sparkline (Analytics) ── */
.tool-viz-spark { margin-top: auto; color: var(--accent); }
.spark-svg { width: 100%; height: 52px; display: block; }

/* ── Heatmap dots (Heatmaps) ── */
.tool-viz-dots {
  position: relative;
  margin-top: auto;
  height: 80px;
  background: #fafafa;
  border: 1px solid var(--ab-hairline);
  border-radius: 8px;
  overflow: hidden;
}
.viz-dot {
  position: absolute;
  width: 10px;
  height: 10px;
  margin-left: -5px;
  margin-top: -5px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: 0 0 14px color-mix(in srgb, var(--accent) 55%, transparent);
  opacity: 0.85;
}

/* ── Bottom caption + pager ── */
.tools-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  padding-top: 28px;
  border-top: 1px solid var(--ab-hairline);
}
.tool-caption { max-width: 680px; }
.tool-desc {
  font-family: 'Inter', sans-serif;
  font-size: 17px;
  line-height: 1.5;
  font-weight: 500;
  color: var(--ab-fg);
  margin: 0 0 8px;
  letter-spacing: -0.01em;
}
.tool-replace {
  font-size: 12.5px;
  color: var(--ab-fg-muted);
  letter-spacing: 0.01em;
}
.tool-replace strong {
  color: var(--ab-fg);
  font-family: 'Geist', sans-serif;
  font-weight: 500;
}

.tool-pager {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.tool-count {
  font-family: 'Geist', sans-serif;
  font-size: 13px;
  font-weight: 500;
  color: var(--ab-fg);
  min-width: 40px;
  text-align: center;
  letter-spacing: 0.01em;
}
.tool-arrow {
  appearance: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #ffffff;
  border: 1px solid var(--ab-hairline-strong);
  color: var(--ab-fg);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.18s ease;
}
.tool-arrow:hover {
  background: var(--ab-fg);
  color: #ffffff;
  border-color: var(--ab-fg);
}

@media (max-width: 1024px) {
  .tools-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .tools-for { padding: 80px 0 72px; }
  .tools-grid { grid-template-columns: 1fr; gap: 14px; }
  .tool-card { min-height: auto; }
  .tools-head { flex-direction: column; align-items: flex-start; gap: 20px; }
  .tools-bottom { flex-direction: column; align-items: flex-start; gap: 18px; }
}
</style>
