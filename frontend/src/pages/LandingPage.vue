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
          <router-link to="/login" class="nav-cta">Sign In</router-link>
        </div>
      </div>
    </nav>

    <!-- ═══ Hero ═══ -->
    <section class="hero">
      <div class="wrap">
        <h1 class="hero-h anim" data-anim="fade-up">
          Marketing intelligence,<br/>
          <em>simplified.</em>
        </h1>
        <p class="hero-p anim" data-anim="fade-up" data-delay="60">
          Track visitors, score leads, audit your site, and grow<br class="hide-m"/>
          with AI — all in one platform.
        </p>
        <p class="hero-beta-note anim" data-anim="fade-up" data-delay="90">
          <span class="brand-beta">BETA</span>
          <span class="beta-text">We're in private beta. New sign-ups are paused — existing users can sign in.</span>
        </p>
        <div class="hero-ctas anim" data-anim="fade-up" data-delay="120">
          <router-link to="/login" class="btn-primary">Sign In</router-link>
          <a href="#features" class="btn-ghost">Learn More</a>
        </div>
      </div>
    </section>

    <!-- ═══ Dashboard Preview — video bg with floating dashboard ═══ -->
    <section class="dash-preview anim" data-anim="fade-up">
      <div class="dash-preview-inner">
        <!-- Background video — plays silently, edges visible around dashboard -->
        <video class="dash-video" autoplay muted loop playsinline>
          <source src="/videos/background-vid.mp4" type="video/mp4" />
        </video>
        <div class="dash-video-overlay"></div>
        <!-- Dashboard mockup floating on top -->
        <div class="dash-mockup">
          <img src="/images/hero-dashboard.png" alt="FetchBot Dashboard" class="dash-img" />
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
              <Transition name="word-cycle" mode="out-in">
                <span class="feat-word" :key="categories[activeCat]">
                  {{ categories[activeCat] }}
                  <span class="feat-word-glow"></span>
                </span>
              </Transition>
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
                 :style="{ '--card-stagger': i * 80 + 'ms' }"
                 @click="activeCard = activeCard === i ? -1 : i"
                 @mousemove="onCardMouseMove($event, i)"
                 @mouseenter="onCardMouseEnter(i)"
                 @mouseleave="onCardMouseLeave($event, i)">
              <span class="card-num">{{ String(i + 1).padStart(2, '0') }}</span>

              <!-- Per-tool animated visual -->
              <div class="card-visual">
                <!-- Analytics: line chart with drawing animation -->
                <div v-if="f.visual === 'chart'" class="viz viz-chart">
                  <div class="viz-stat">
                    <div class="viz-stat-value">{{ metricFor(f, i) }}</div>
                    <div class="viz-stat-meta">
                      <span class="viz-stat-label">{{ f.metric.label }}</span>
                      <span class="viz-stat-delta up">{{ f.metric.delta }}</span>
                    </div>
                  </div>
                  <svg class="chart-svg" viewBox="0 0 220 70" preserveAspectRatio="none">
                    <defs>
                      <linearGradient :id="'g-' + i" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stop-color="#F97316" stop-opacity="0.30"/>
                        <stop offset="100%" stop-color="#F97316" stop-opacity="0"/>
                      </linearGradient>
                    </defs>
                    <path class="chart-area" :d="buildAreaPath(f.chart)" :fill="'url(#g-' + i + ')'" />
                    <path class="chart-line" :d="buildLinePath(f.chart)" fill="none" stroke="#F97316" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                    <circle class="chart-pulse" :cx="220" :cy="lastY(f.chart)" r="3" fill="#F97316"/>
                  </svg>
                </div>

                <!-- Heatmaps: pulsing radial hotspots -->
                <div v-else-if="f.visual === 'heatmap'" class="viz viz-heatmap">
                  <div class="viz-stat">
                    <div class="viz-stat-value">{{ metricFor(f, i) }}</div>
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
                    <div class="viz-stat-value">{{ metricFor(f, i) }}</div>
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
                    <div class="viz-stat-value">{{ metricFor(f, i) }}</div>
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
            <router-link to="/login" class="price-btn" :class="{ dark: plan.featured }">{{ plan.cta }}</router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Final CTA ═══ -->
    <section class="final-cta anim" data-anim="fade-up">
      <div class="wrap cta-inner">
        <video class="cta-video" autoplay muted loop playsinline>
          <source src="/videos/background-vid.mp4" type="video/mp4" />
        </video>
        <div class="cta-video-overlay"></div>
        <div class="cta-content">
          <h2>Ready to grow <em>smarter?</em></h2>
          <p>FetchBot is in private beta. Existing users — sign in below.</p>
          <router-link to="/login" class="btn-primary cta-btn-white">Sign In</router-link>
        </div>
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
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'

const scrolled = ref(false)
const activeCard = ref(0)
const activeCat = ref(0)
const trackOffset = ref(0)
const trackRef = ref(null)



const cardStep = 280
const visibleCards = 4
let cycleTimer = null
let featureTimer = null
const featureDwellMs = 4200

// Restrained, ink-leaning avatar palette — no brights.
const leadColors = ['#0F172A', '#475569', '#334155', '#64748B']

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

// ── Framer-style mouse tilt + parallax ──
// We write transforms to CSS vars on the card element, throttled by rAF.
// CSS handles the spring smoothing via transition + cubic-bezier.
const TILT_MAX = 6        // max degrees
const PARALLAX_MAX = 6    // max px shift for inner content
const tiltRaf = new Map()

function onCardMouseEnter(i) {
  stopFeatureAutoAdvance()
  activeCard.value = i
}

function onCardMouseLeave(ev, i) {
  startFeatureAutoAdvance()
  const card = ev.currentTarget
  if (tiltRaf.has(i)) { cancelAnimationFrame(tiltRaf.get(i)); tiltRaf.delete(i) }
  card.style.setProperty('--tx', '0deg')
  card.style.setProperty('--ty', '0deg')
  card.style.setProperty('--px', '0px')
  card.style.setProperty('--py', '0px')
  card.style.setProperty('--gx', '50%')
  card.style.setProperty('--gy', '50%')
}

function onCardMouseMove(ev, i) {
  const card = ev.currentTarget
  if (tiltRaf.has(i)) cancelAnimationFrame(tiltRaf.get(i))
  // rAF the read+write so we don't fight the browser
  tiltRaf.set(i, requestAnimationFrame(() => {
    const rect = card.getBoundingClientRect()
    const x = (ev.clientX - rect.left) / rect.width  // 0..1
    const y = (ev.clientY - rect.top)  / rect.height // 0..1
    const tx = (y - 0.5) * -2 * TILT_MAX  // tilt UP when mouse is at top
    const ty = (x - 0.5) *  2 * TILT_MAX  // tilt RIGHT when mouse is at right
    const px = (x - 0.5) * PARALLAX_MAX
    const py = (y - 0.5) * PARALLAX_MAX
    card.style.setProperty('--tx', tx.toFixed(2) + 'deg')
    card.style.setProperty('--ty', ty.toFixed(2) + 'deg')
    card.style.setProperty('--px', px.toFixed(2) + 'px')
    card.style.setProperty('--py', py.toFixed(2) + 'px')
    card.style.setProperty('--gx', (x * 100).toFixed(1) + '%')
    card.style.setProperty('--gy', (y * 100).toFixed(1) + '%')
  }))
}

// ── Count-up animation for the active card's headline number ──
// Stored as a map { cardIndex: displayString } so non-active cards
// keep their final value (we only count the active card up).
const animatedMetrics = ref({})
let countUpRaf = null

function formatLikeOriginal(n, original) {
  const s = String(original)
  if (/[,]/.test(s)) return Math.round(n).toLocaleString()
  return String(Math.round(n))
}

function startCountUp(targetCardIdx) {
  if (countUpRaf) cancelAnimationFrame(countUpRaf)
  if (targetCardIdx < 0) return
  const target = features[targetCardIdx]?.metric?.value
  if (!target) return
  const cleaned = String(target).replace(/[^\d.]/g, '')
  const final = parseFloat(cleaned) || 0
  const startTs = performance.now()
  const duration = 900
  const tick = (now) => {
    const t = Math.min(1, (now - startTs) / duration)
    // ease-out cubic — matches Framer's default "easeOut"
    const eased = 1 - Math.pow(1 - t, 3)
    const current = final * eased
    animatedMetrics.value = {
      ...animatedMetrics.value,
      [targetCardIdx]: formatLikeOriginal(current, target),
    }
    if (t < 1) countUpRaf = requestAnimationFrame(tick)
    else {
      animatedMetrics.value = { ...animatedMetrics.value, [targetCardIdx]: target }
      countUpRaf = null
    }
  }
  countUpRaf = requestAnimationFrame(tick)
}

function metricFor(card, i) {
  return animatedMetrics.value[i] ?? card.metric.value
}

watch(activeCard, (idx) => startCountUp(idx))

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
    scene: 'floral',
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
    scene: 'mountain',
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
    scene: 'meadow',
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
    scene: 'floral',
    metric: { value: '23', label: 'Companies today', delta: '4 hot leads' },
    leads: [
      { name: 'Acme Corp',      domain: 'acme.com',    score: 94, hot: true },
      { name: 'Vector Labs',    domain: 'vectorlabs.io', score: 81, hot: true },
      { name: 'Northwind Ltd',  domain: 'northwind.co',  score: 67, hot: false },
    ],
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="12" cy="7" r="4"/><path d="M5.5 21c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/></svg>'
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
em { color: #F97316; font-style: italic; }
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
  color: #FFFFFF;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-weight: 800;
  font-size: 9px;
  letter-spacing: 0.1em;
  padding: 2px 7px;
  border-radius: 999px;
  vertical-align: middle;
  background: #F97316;
}
.hero-beta-note {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: rgba(15, 23, 42, 0.5);
  background: transparent;
  border: none;
  padding: 0;
  margin: 14px 0 4px;
}
.beta-text {
  font-size: 11px;
  color: rgba(15, 23, 42, 0.45);
  font-weight: 400;
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
.hero { padding: 160px 0 80px; text-align: center; }
.hero .wrap { display: flex; flex-direction: column; align-items: center; }
.hero-h {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400;
  font-size: clamp(2.6rem, 5.5vw, 4.5rem);
  line-height: 1.12;
  letter-spacing: -0.03em;
  color: #0F172A;
  margin-bottom: 24px;
  animation: hero-float 6s ease-in-out infinite;
}
@keyframes hero-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.hero-h em {
  font-style: italic;
  color: #F97316;
}

.hero-p {
  font-size: 17px; color: #475569; line-height: 1.65; max-width: 520px;
  margin-bottom: 20px; text-align: center;
}
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

/* ═══ Dashboard Preview — video background with floating mockup ═══ */
.dash-preview {
  padding: 0 32px 80px;
  background: #FFFFFF;
}
.dash-preview-inner {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  border-radius: 24px;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  box-shadow:
    0 2px 4px rgba(15, 23, 42, 0.04),
    0 24px 64px rgba(15, 23, 42, 0.10);
}
.dash-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}
.dash-video-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: rgba(250, 249, 247, 0.15);
  pointer-events: none;
}
.dash-mockup {
  position: absolute;
  z-index: 2;
  top: 5%;
  left: 5%;
  right: 5%;
  bottom: 5%;
  border-radius: 16px;
  overflow: hidden;
  box-shadow:
    0 2px 8px rgba(15, 23, 42, 0.08),
    0 16px 48px rgba(15, 23, 42, 0.12);
  background: #FFFFFF;
}
.dash-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top left;
  display: block;
}

@media (max-width: 768px) {
  .dash-preview { padding: 0 16px 48px; }
  .dash-preview-inner { aspect-ratio: 4 / 3; border-radius: 16px; }
  .dash-mockup { top: 4%; left: 4%; right: 4%; bottom: 4%; border-radius: 10px; }
}

/* ═══ Features Carousel — Travel Lab Style ═══ */


/* Features section — clean gray background */
.features-section {
  padding: 64px 0 80px;
  position: relative;
  overflow: hidden;
  background: #F5F5F5;
}
.feat-full { background: transparent; border-radius: 0; margin: 0; padding: 48px 32px 40px; overflow: visible; position: relative; z-index: 1; }

.feat-header { display: flex; align-items: baseline; gap: 40px; margin-bottom: 36px; flex-wrap: wrap; }
.feat-headline {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: clamp(1.8rem, 3.5vw, 3rem);
  font-weight: 400;
  letter-spacing: -0.025em;
  color: #0F172A;
  display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap;
  line-height: 1.15;
  text-transform: none;
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
  color: #0F172A;
  font-style: italic;
  white-space: nowrap;
  line-height: 1.2;
}
.feat-word-glow {
  position: absolute; bottom: -2px; left: 0; right: 0;
  height: 2px; background: #0F172A;
  border-radius: 1px;
  opacity: 0.5;
}
@keyframes glow-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* Word cycle transition — smooth slide-up, no flicker */
.word-cycle-enter-active {
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}
.word-cycle-leave-active {
  transition: all 0.25s cubic-bezier(0.55, 0, 1, 0.45);
}
.word-cycle-enter-from {
  opacity: 0; transform: translateY(60%) scale(0.95);
  filter: blur(4px);
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
  opacity: 0; transform: translateY(-50%) scale(0.95);
  filter: blur(4px);
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
  color: #0F172A;
  text-decoration: none;
}
.feat-tab.active::after {
  content: '';
  position: absolute;
  bottom: -4px; left: 0; right: 0;
  height: 1px;
  background: #0F172A;
  border-radius: 0;
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
/* ── Framer-style card: 3D tilt, spring entrance, layered shadow ── */
.carousel-card {
  --tx: 0deg;
  --ty: 0deg;
  --px: 0px;
  --py: 0px;
  --gx: 50%;
  --gy: 50%;
  flex: 0 0 260px; min-height: 320px;
  border-radius: 18px; padding: 24px 20px;
  cursor: pointer; position: relative;
  display: flex; flex-direction: column;
  overflow: hidden;
  transform-style: preserve-3d;
  perspective: 800px;
  /* Two-layer shadow: tight near + soft far. Driven by --shadow-* in active state. */
  box-shadow:
    0 1px 3px rgba(19,23,24,0.06),
    0 8px 24px rgba(19,23,24,0.05);
  /* Spring-eased motion (Framer's classic overshoot curve). The transform
     is driven by mouse-move CSS vars so we only animate when settling. */
  transform:
    perspective(900px)
    rotateX(var(--tx))
    rotateY(var(--ty))
    translateZ(0)
    scale(var(--card-scale, 1));
  transition:
    flex 0.5s cubic-bezier(0.34, 1.56, 0.64, 1),
    transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1),
    box-shadow 0.45s cubic-bezier(0.22, 1, 0.36, 1),
    --card-scale 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
  /* Stagger-in on first paint */
  animation: card-spring-in 0.85s cubic-bezier(0.34, 1.56, 0.64, 1) var(--card-stagger, 0ms) both;
  will-change: transform, box-shadow;
}

/* Subtle cursor spotlight — much softer than before so it doesn't compete
   with the content. Only visible on the active card. */
.carousel-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background: radial-gradient(
    320px circle at var(--gx) var(--gy),
    rgba(15, 23, 42, 0.04),
    rgba(15, 23, 42, 0) 60%
  );
  opacity: 0;
  transition: opacity 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  z-index: 1;
}
.carousel-card.is-playing::before { opacity: 1; }

/* Inner content above the glow layer */
.carousel-card > * { position: relative; z-index: 2; }

@keyframes card-spring-in {
  0%   { opacity: 0; transform: perspective(900px) translateY(28px) scale(0.92) rotateX(8deg); }
  60%  { opacity: 1; transform: perspective(900px) translateY(-4px) scale(1.02) rotateX(-1deg); }
  100% { opacity: 1; transform: perspective(900px) translateY(0)    scale(1)    rotateX(0deg); }
}

.carousel-card:hover {
  --card-scale: 1.015;
  border-color: rgba(15, 23, 42, 0.12);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 12px 28px rgba(15, 23, 42, 0.06);
}

.carousel-card.expanded,
.carousel-card.is-playing {
  flex: 0 0 420px;
  min-height: 360px;
  --card-scale: 1.025;
  background: #ffffff;
  border-color: rgba(15, 23, 42, 0.16);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 16px 40px rgba(15, 23, 42, 0.08);
}

/* Inner-content parallax — chart/visual shifts opposite to tilt */
.carousel-card .card-visual,
.carousel-card .card-title {
  transform: translate3d(var(--px), var(--py), 0);
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.carousel-card .card-num {
  transform: translate3d(calc(var(--px) * 0.6), calc(var(--py) * 0.6), 0);
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@media (prefers-reduced-motion: reduce) {
  .carousel-card,
  .carousel-card .card-visual,
  .carousel-card .card-title,
  .carousel-card .card-num {
    animation: none !important;
    transition: opacity 0.3s ease, flex 0.3s ease;
    transform: none !important;
  }
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
  font-variant-numeric: tabular-nums;
  display: inline-block;
}
.is-playing .viz-stat-value {
  animation: stat-pop-in 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes stat-pop-in {
  0%   { opacity: 0; transform: translateY(8px) scale(0.92); filter: blur(2px); }
  60%  { opacity: 1; transform: translateY(-1px) scale(1.04); filter: blur(0); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}
.is-playing .viz-stat-meta {
  animation: stat-meta-fade 0.6s cubic-bezier(0.22, 1, 0.36, 1) 0.15s both;
}
@keyframes stat-meta-fade {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.viz-stat-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.viz-stat-label { color: rgba(15, 23, 42, 0.5); font-weight: 500; letter-spacing: 0.04em; }
.viz-stat-delta {
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(249, 115, 22, 0.08);
  color: rgba(15, 23, 42, 0.65);
  font-weight: 600;
}
.viz-stat-delta.up { background: rgba(249, 115, 22, 0.12); color: #EA580C; }

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
  background: radial-gradient(circle, rgba(249, 115, 22, 0.55) 0%, rgba(249, 115, 22, 0.22) 45%, rgba(249, 115, 22, 0) 75%);
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
  background: linear-gradient(90deg, #F97316 0%, #FB923C 100%);
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
  font-weight: 600;
  color: rgba(15, 23, 42, 0.65);
  background: rgba(15, 23, 42, 0.05);
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
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.06);
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
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 11px;
  flex-shrink: 0;
}
.lead-meta { flex: 1; min-width: 0; }
.lead-name { font-size: 12px; font-weight: 600; color: #0F172A; line-height: 1.2; }
.lead-domain { font-size: 10px; color: rgba(15, 23, 42, 0.5); }
.lead-score {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  color: #0F172A;
  font-variant-numeric: tabular-nums;
}
.lead-score.hot {
  background: #F97316;
  color: #fff;
  box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.30);
}
.is-playing .lead-score.hot {
  animation: lead-hot-pulse 1.8s ease-in-out 0.8s infinite;
}
@keyframes lead-hot-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.30); }
  50%      { box-shadow: 0 0 0 5px rgba(249, 115, 22, 0); }
}

.carousel-card.tint-peach,
.carousel-card.tint-blue,
.carousel-card.tint-yellow,
.carousel-card.tint-pink {
  background: #FFFFFF;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow:
    0 1px 3px rgba(19,23,24,0.06),
    0 8px 24px rgba(19,23,24,0.08);
}

/* Card inner elements */
.card-num {
  /* Bear-style monospace numeric label, not the loud serif. Smaller,
     muted, uppercase, lots of letter-spacing. */
  font-family: 'SF Mono', 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: rgba(15, 23, 42, 0.4);
  line-height: 1;
  margin-bottom: 18px;
}
.card-visual { margin-bottom: auto; }
.card-icon {
  color: rgba(15, 23, 42, 0.5);
  transition: transform 0.3s ease;
}
.carousel-card:hover .card-icon {
  transform: scale(1.05);
}
.card-title {
  /* Lighter weight, tighter tracking — Bear's serif headline pattern. */
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: 22px;
  font-weight: 400;
  color: #0F172A;
  letter-spacing: -0.025em;
  line-height: 1.15;
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
.card-desc { font-size: 13px; color: #475569; line-height: 1.55; margin-bottom: 10px; font-weight: 400; }
.card-replaces { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(15, 23, 42, 0.45); }

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
.price-card.featured { border-color: #F97316; box-shadow: 0 4px 20px rgba(249,115,22,0.1); }
.pop {
  position: absolute; top: -11px; left: 50%; transform: translateX(-50%);
  padding: 3px 14px; background: #F97316; color: #fff;
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
.price-btn:hover { border-color: #F97316; color: #F97316; }
.price-btn.dark { background: #131718; border-color: #131718; color: #fff; }
.price-btn.dark:hover { background: #2a2d2e; transform: translateY(-1px); }

/* ── Final CTA ── */
.final-cta { padding: 48px 0 80px; }
.cta-inner {
  position: relative;
  text-align: center;
  border: none; border-radius: 24px;
  padding: 0;
  overflow: hidden;
  min-height: 340px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cta-video {
  position: absolute;
  inset: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  z-index: 0;
}
.cta-video-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(2px);
  pointer-events: none;
}
.cta-content {
  position: relative;
  z-index: 2;
  padding: 72px 40px;
}
.cta-inner h2 {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400; font-size: clamp(1.6rem, 3vw, 2.4rem);
  margin-bottom: 10px;
  color: #FFFFFF;
}
.cta-inner h2 em { color: #FB923C; }
.cta-inner p { font-size: 15px; color: rgba(255,255,255,0.7); margin-bottom: 28px; }
.cta-btn-white {
  background: #FFFFFF !important;
  color: #0F172A !important;
}
.cta-btn-white:hover {
  background: #F8FAFC !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}

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
</style>
