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
          <span class="tw-line" ref="twLine1"></span><br/>
          <span class="tw-line" ref="twLine2"></span><br/>
          <em><span class="tw-line" ref="twLine3"></span></em>
          <span class="tw-cursor" :class="{ 'tw-cursor--done': twDone }">|</span>
        </h1>
        <p class="hero-p anim" data-anim="fade-up" data-delay="60">
          Track visitors, score leads, audit your site, and grow<br class="hide-m"/>
          with AI — all in one platform.
        </p>
        <p class="hero-beta-note anim" data-anim="fade-up" data-delay="90">
          <span class="brand-beta">BETA</span>
          We're in private beta. New sign-ups are paused — existing users can sign in.
        </p>
        <div class="hero-ctas anim" data-anim="fade-up" data-delay="120">
          <router-link to="/login" class="btn-primary">Sign In</router-link>
          <a href="#features" class="btn-ghost">Learn More</a>
        </div>
      </div>
    </section>

    <!-- ═══ Trusted by row ═══ -->
    <section class="trusted-by anim" data-anim="fade-up">
      <p class="trusted-by-label">Trusted by</p>
      <div class="trusted-logos">
        <div v-for="logo in trustedLogos" :key="logo" class="trusted-logo-slot">{{ logo }}</div>
      </div>
    </section>

    <!-- ═══ Turn AI traffic into revenue — Bear-style feature blocks ═══ -->
    <section class="bear-revenue" id="revenue">
      <div class="wrap">
        <div class="bear-intro anim" data-anim="fade-up">
          <h2 class="bear-headline">Turn AI traffic into revenue.</h2>
          <p class="bear-sub">
            FetchBot offers the tools to convert traffic from AI Agents into customers.
          </p>
        </div>

        <div v-for="(block, i) in bearBlocks" :key="block.eyebrow"
             class="bear-block anim" data-anim="fade-up" :data-delay="i * 80">
          <div class="bear-text">
            <div class="bear-eyebrow">{{ block.eyebrow }}</div>
            <h3 class="bear-block-title">{{ block.title }}</h3>
            <p class="bear-block-desc">{{ block.desc }}</p>
          </div>

          <div class="bear-visual">
            <!-- Placeholder painterly background. Swap for a real oil-painting
                 asset when you have one; the overlay card stays as-is. -->
            <div class="painterly-bg" :class="'painterly-' + block.scene">
              <span class="painterly-tag">Painterly placeholder</span>
            </div>

            <!-- Floating UI mockup per block -->
            <div class="bear-overlay" v-if="block.scene === 'floral'">
              <div class="bear-overlay-header">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/>
                </svg>
                <span><strong>New leads</strong> &nbsp;(23)</span>
              </div>
              <div v-for="lead in block.leads" :key="lead.name" class="bear-lead-row">
                <span class="bear-avatar" :style="{ background: lead.bg }">{{ lead.initials }}</span>
                <div class="bear-lead-meta">
                  <div class="bear-lead-name">{{ lead.name }}</div>
                  <div class="bear-lead-role">{{ lead.role }}</div>
                </div>
                <span class="bear-arrow">→</span>
              </div>
            </div>

            <div class="bear-overlay" v-else-if="block.scene === 'mountain'">
              <div class="bear-overlay-header">
                <span class="bear-star">✦</span>
                <strong>Blog Agent</strong>
              </div>
              <div class="bear-agent-progress">
                <div class="bear-agent-bar"><span :style="{ width: '62%' }"></span></div>
              </div>
              <div v-for="step in block.steps" :key="step.label" class="bear-step-row">
                <span class="bear-step-label">{{ step.label }}</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0F766E" stroke-width="2.5">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
            </div>

            <div class="bear-overlay" v-else-if="block.scene === 'meadow'">
              <div v-for="src in block.sources" :key="src.host" class="bear-source-row">
                <div class="bear-source-accent" :style="{ background: src.accent }"></div>
                <div class="bear-source-meta">
                  <div class="bear-source-host">{{ src.host }}</div>
                  <div class="bear-source-url">{{ src.url }}</div>
                  <div class="bear-source-cites">{{ src.cites }}</div>
                </div>
                <button class="bear-outreach-btn">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M4 4h16c1 0 2 1 2 2v12c0 1-1 2-2 2H4c-1 0-2-1-2-2V6c0-1 1-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                  </svg>
                  Outreach
                </button>
              </div>
            </div>
          </div>
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
        <h2>Ready to grow <em>smarter?</em></h2>
        <p>FetchBot is in private beta. Existing users — sign in below.</p>
        <router-link to="/login" class="btn-primary">Sign In</router-link>
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
]

const steps = [
  { title: 'Add Your Website', desc: 'Enter your domain and we generate a tracking pixel instantly.' },
  { title: 'Install the Pixel', desc: 'Copy one line of JavaScript into your site header — takes 30 seconds.' },
  { title: 'Watch Insights Flow', desc: 'Real-time analytics and AI insights appear immediately.' },
]

// ── "Trusted by" row — placeholder text slots. Replace with real logos
// (<img> or inline SVG) when you have partner brand assets. ──
const trustedLogos = [
  'BLE', 'PEERSPACE', 'MEDAL', 'GROWW', 'FLOW', 'PARTNER',
]

// ── Bear-style feature blocks — content lifted from usebear.ai, reworded
// for our product. Each block ships with its own overlay card rendered as
// real HTML so it reads as a live mockup, not a static image. ──
const bearBlocks = [
  {
    eyebrow: 'LEAD GENERATION',
    title: 'Turn AI Traffic Into Leads',
    desc: 'FetchBot helps you identify users coming from ChatGPT and other AI sources — so you can convert their high-intent visits.',
    scene: 'floral',
    leads: [
      { name: 'Rick Deckard',   role: 'CEO, Polarbear AI',          initials: 'RD', bg: '#4B5563' },
      { name: 'Niander Wallace', role: 'CEO, Wallace Corporation',  initials: 'NW', bg: '#334155' },
      { name: 'Alina Ward',     role: 'Head of Marketing, Leno',    initials: 'AW', bg: '#0F172A' },
      { name: 'Kevin Nguyen',   role: 'CEO, Tyrell Corp',           initials: 'KN', bg: '#475569' },
    ],
  },
  {
    eyebrow: 'CONTENT OPTIMIZATION',
    title: 'Create Content that AI Agents Crawl',
    desc: 'Generate structured, AI-ready content designed to be easily ingested, cited, and recommended by LLMs.',
    scene: 'mountain',
    steps: [
      { label: 'Found 49 URLs to analyze for brand voice  ·  16m 33s' },
      { label: 'Scraping existing blogs (20%)              ·  16m 33s' },
      { label: 'Fetching competitors (30%)                 ·  17m 7s'  },
      { label: 'Querying knowledge base (35%)              ·  17m 8s'  },
      { label: 'Analyzing brand voice (40%)                ·  17m 9s'  },
    ],
  },
  {
    eyebrow: 'OUTREACH WORKFLOW',
    title: 'Automate PR',
    desc: 'Find the third-party and UGC sources cited by LLMs and get mentioned on them automatically.',
    scene: 'meadow',
    sources: [
      { host: 'Forbes',   url: 'forbes.com/business/thth7a...',      cites: '254 citations', accent: '#D97706' },
      { host: 'Reddit',   url: 'reddit.com/r/aeo/why-is...',          cites: '312 citations', accent: '#DC2626' },
      { host: 'LinkedIn', url: 'linkedin.com/pulse/how...',           cites: '133 mentions',  accent: '#2563EB' },
    ],
  },
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
/* ─────────────────────────────────────────────────────────────────
   Trusted by row
   ───────────────────────────────────────────────────────────────── */
.trusted-by {
  padding: 48px 32px 32px;
  background: #FAF9F7;
  text-align: center;
}
.trusted-by-label {
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: rgba(15, 23, 42, 0.45);
  margin: 0 0 20px;
}
.trusted-logos {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: clamp(24px, 5vw, 64px);
  flex-wrap: wrap;
}
.trusted-logo-slot {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400;
  font-size: clamp(20px, 2.5vw, 28px);
  color: rgba(15, 23, 42, 0.55);
  letter-spacing: -0.02em;
  transition: color 0.2s ease;
}
.trusted-logo-slot:hover { color: rgba(15, 23, 42, 0.85); }

/* ─────────────────────────────────────────────────────────────────
   Bear-style "Turn AI traffic into revenue" section
   ───────────────────────────────────────────────────────────────── */
.bear-revenue {
  background: #FAF9F7;
  padding: 80px 0 96px;
}
.bear-intro {
  text-align: center;
  max-width: 720px;
  margin: 0 auto 56px;
}
.bear-headline {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400;
  font-size: clamp(2rem, 4.5vw, 3.4rem);
  letter-spacing: -0.03em;
  color: #0F172A;
  line-height: 1.1;
  margin: 0 0 14px;
}
.bear-sub {
  font-size: clamp(14px, 1.5vw, 17px);
  color: rgba(15, 23, 42, 0.65);
  line-height: 1.55;
  margin: 0;
}

.bear-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  align-items: stretch;
  background: #FFFFFF;
  border-radius: 20px;
  overflow: hidden;
  margin-bottom: 24px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 12px 32px rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.05);
}
.bear-block:last-child { margin-bottom: 0; }
@media (max-width: 860px) {
  .bear-block { grid-template-columns: 1fr; }
}

.bear-text {
  padding: 56px 56px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 360px;
}
.bear-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: rgba(15, 23, 42, 0.5);
  margin-bottom: 20px;
}
.bear-block-title {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400;
  font-size: clamp(22px, 2.2vw, 30px);
  letter-spacing: -0.025em;
  color: #0F172A;
  line-height: 1.2;
  margin: 0 0 14px;
}
.bear-block-desc {
  font-size: 14px;
  color: rgba(15, 23, 42, 0.65);
  line-height: 1.6;
  margin: 0;
  max-width: 440px;
}
.bear-visual {
  position: relative;
  min-height: 360px;
  overflow: hidden;
}

/* ─────────────────────────────────────────────────────────────────
   Painterly background placeholders (pure CSS — swap for real oil
   painting assets when available). Each scene uses layered radial
   gradients to approximate an impressionist oil-paint surface, with
   a subtle noise/grain filter for texture.
   ───────────────────────────────────────────────────────────────── */
.painterly-bg {
  position: absolute;
  inset: 0;
  filter: saturate(1.05);
}
.painterly-bg::after {
  /* Grain layer — tiny SVG noise to fake the painterly texture. */
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' seed='5'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.35 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  opacity: 0.22;
  mix-blend-mode: overlay;
  pointer-events: none;
}
.painterly-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 3px 8px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(15, 23, 42, 0.55);
  background: rgba(255, 255, 255, 0.8);
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(4px);
  z-index: 2;
}

/* Floral — pink + green impressionist */
.painterly-floral {
  background:
    radial-gradient(ellipse 60% 40% at 20% 30%, rgba(245,200,200,0.9) 0%, transparent 60%),
    radial-gradient(circle at 75% 20%, rgba(221,110,127,0.55) 0%, transparent 35%),
    radial-gradient(circle at 15% 85%, rgba(180,205,170,0.8) 0%, transparent 45%),
    radial-gradient(ellipse at 60% 70%, rgba(155,180,190,0.85) 0%, transparent 55%),
    radial-gradient(circle at 90% 90%, rgba(239,143,164,0.5) 0%, transparent 40%),
    linear-gradient(160deg, #DCE5DD 0%, #C9D5D0 50%, #B9C7C5 100%);
}
/* Mountain — blue + white + pine */
.painterly-mountain {
  background:
    radial-gradient(ellipse 80% 50% at 50% 25%, rgba(240,244,246,0.85) 0%, transparent 60%),
    radial-gradient(ellipse 40% 30% at 25% 40%, rgba(169,189,204,0.85) 0%, transparent 55%),
    radial-gradient(ellipse 60% 40% at 80% 50%, rgba(120,155,155,0.7) 0%, transparent 50%),
    radial-gradient(ellipse 70% 40% at 50% 85%, rgba(112,125,120,0.85) 0%, transparent 55%),
    radial-gradient(circle at 70% 80%, rgba(85,120,105,0.6) 0%, transparent 40%),
    linear-gradient(175deg, #C8D5D8 0%, #AFBEC1 55%, #8F9A99 100%);
}
/* Meadow — warm gold + green */
.painterly-meadow {
  background:
    radial-gradient(ellipse 80% 50% at 50% 25%, rgba(210,210,210,0.8) 0%, transparent 55%),
    radial-gradient(ellipse 70% 30% at 40% 55%, rgba(212,199,175,0.85) 0%, transparent 60%),
    radial-gradient(ellipse 90% 40% at 60% 80%, rgba(178,168,130,0.9) 0%, transparent 60%),
    radial-gradient(circle at 80% 90%, rgba(100,90,65,0.6) 0%, transparent 40%),
    linear-gradient(175deg, #D5D8D4 0%, #C2B996 55%, #A59A72 100%);
}

/* ─────────────────────────────────────────────────────────────────
   Floating overlay cards (real HTML mockups on top of painterly bg)
   ───────────────────────────────────────────────────────────────── */
.bear-overlay {
  position: absolute;
  background: #FFFFFF;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  box-shadow:
    0 1px 3px rgba(15, 23, 42, 0.06),
    0 12px 28px rgba(15, 23, 42, 0.10);
  padding: 16px;
  z-index: 3;
  top: 50%;
  left: 8%;
  transform: translateY(-50%);
  min-width: 300px;
  max-width: 88%;
  backdrop-filter: blur(6px);
}
.bear-overlay-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #0F172A;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}
.bear-lead-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  font-size: 12px;
}
.bear-avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 10px;
  flex-shrink: 0;
  letter-spacing: 0.02em;
}
.bear-lead-meta { flex: 1; min-width: 0; }
.bear-lead-name { font-weight: 600; color: #0F172A; font-size: 13px; line-height: 1.2; }
.bear-lead-role { font-size: 11px; color: rgba(15, 23, 42, 0.55); margin-top: 2px; }
.bear-arrow {
  color: rgba(15, 23, 42, 0.35);
  font-size: 14px;
  padding-left: 6px;
}

.bear-agent-progress { margin: 4px 0 14px; }
.bear-agent-bar {
  height: 4px;
  border-radius: 2px;
  background: rgba(15, 23, 42, 0.08);
  overflow: hidden;
}
.bear-agent-bar span {
  display: block;
  height: 100%;
  background: #0F172A;
  border-radius: 2px;
  animation: bear-bar-grow 1.4s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes bear-bar-grow {
  from { width: 0 !important; }
}
.bear-step-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  font-size: 11.5px;
  color: rgba(15, 23, 42, 0.75);
  border-top: 1px solid rgba(15, 23, 42, 0.04);
  font-variant-numeric: tabular-nums;
}
.bear-step-row:first-of-type { border-top: none; }
.bear-step-label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bear-star { color: #7C3AED; font-size: 14px; }

.bear-source-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
  font-size: 12px;
}
.bear-source-row:first-of-type { border-top: none; padding-top: 0; }
.bear-source-accent {
  width: 2px;
  align-self: stretch;
  border-radius: 1px;
  flex-shrink: 0;
}
.bear-source-meta { flex: 1; min-width: 0; }
.bear-source-host { font-weight: 700; color: #0F172A; font-size: 12px; }
.bear-source-url { font-size: 10.5px; color: rgba(15, 23, 42, 0.55); margin: 1px 0; font-family: 'SF Mono', monospace; }
.bear-source-cites { font-size: 10.5px; color: rgba(15, 23, 42, 0.55); }
.bear-outreach-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #FFFFFF;
  color: #0F172A;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  flex-shrink: 0;
}
.bear-outreach-btn:hover {
  background: #F8FAFC;
  border-color: rgba(15, 23, 42, 0.2);
}

.features-section { padding: 64px 0 80px; background: #FAF9F7; }
.feat-full { background: transparent; border-radius: 0; margin: 0; padding: 48px 32px 40px; overflow: visible; }

.feat-header { display: flex; align-items: baseline; gap: 40px; margin-bottom: 36px; flex-wrap: wrap; }
.feat-headline {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: clamp(1.8rem, 3.5vw, 3rem);
  font-weight: 400;
  letter-spacing: -0.025em;
  color: #0F172A;
  display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap;
  line-height: 1.15;
  /* Drop the all-caps treatment — Bear lets the serif type do the work. */
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
  /* Soft, no glow pulse — we're going for refined, not loud. */
  opacity: 0.5;
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
  background: rgba(15, 23, 42, 0.05);
  color: rgba(15, 23, 42, 0.65);
  font-weight: 600;
}
/* Up-delta uses ink rather than green so the palette stays restrained. */
.viz-stat-delta.up { background: rgba(15, 23, 42, 0.06); color: #0F172A; }

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
  /* Calm ink-based heatmap — no fluorescent red/orange. The pulse still
     reads as activity but doesn't fight the rest of the page. */
  background: radial-gradient(circle, rgba(15, 23, 42, 0.45) 0%, rgba(15, 23, 42, 0.18) 45%, rgba(15, 23, 42, 0) 75%);
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
/* Hot leads: an ink-coloured pill with a faint outline pulse, not a
   neon-orange shout. */
.lead-score.hot {
  background: #0F172A;
  color: #fff;
  box-shadow: 0 0 0 0 rgba(15, 23, 42, 0.25);
}
.is-playing .lead-score.hot {
  animation: lead-hot-pulse 1.8s ease-in-out 0.8s infinite;
}
@keyframes lead-hot-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(15, 23, 42, 0.30); }
  50%      { box-shadow: 0 0 0 5px rgba(15, 23, 42, 0); }
}

/* Card tints — Travel Lab branding */
/* Card surface: Bear-style neutral. All four cards share the same calm
   warm-white background; the only differentiator between cards is the
   active state (subtle border + shadow) and the visual content inside.
   No saturated tints. */
.carousel-card.tint-peach,
.carousel-card.tint-blue,
.carousel-card.tint-yellow,
.carousel-card.tint-pink {
  background: #FBFAF8;                                /* warm off-white */
  border: 1px solid rgba(15, 23, 42, 0.06);
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
</style>
