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
      <div class="wrap hero-grid">
        <div class="hero-left">
          <span class="hero-eyebrow anim" data-anim="fade-up">Generative Engine Optimization</span>
          <h1 class="hero-h anim" data-anim="fade-up">
            <span class="tw-line" ref="twLine1"></span><br/>
            <span class="tw-line" ref="twLine2"></span><br/>
            <em><span class="tw-line" ref="twLine3"></span></em>
            <span class="tw-cursor" :class="{ 'tw-cursor--done': twDone }">|</span>
          </h1>
          <p class="hero-p anim" data-anim="fade-up" data-delay="60">
            See how often
            <span class="hero-word-cycler">
              <TransitionGroup name="word-cycle">
                <span class="hero-word" :key="categories[activeCat]">{{ categories[activeCat] }}</span>
              </TransitionGroup>
            </span>
            mentions your brand. Find the prompts you're missing from. Generate the
            content to close the gap.
          </p>
          <div class="hero-ctas anim" data-anim="fade-up" data-delay="120">
            <router-link to="/register" class="btn-primary">Run a free audit</router-link>
            <router-link to="/login" class="btn-ghost">Sign in</router-link>
          </div>
          <ul class="hero-bullets anim" data-anim="fade-up" data-delay="160">
            <li><span class="hero-bullet-dot"></span> Multi-LLM probing across Claude, GPT-4, Gemini, Perplexity</li>
            <li><span class="hero-bullet-dot"></span> Source-level citation tracking — see where the AI gets its answers</li>
            <li><span class="hero-bullet-dot"></span> Brand-fact verification + AI-drafted content to close gaps</li>
          </ul>
        </div>

        <!-- Framer-style animated visualisation -->
        <div class="hero-right anim" data-anim="fade-up" data-delay="220">
          <div class="hero-viz">
            <div class="hero-viz-head">
              <span class="hero-viz-dot is-anthropic"></span>
              <span class="hero-viz-dot is-openai"></span>
              <span class="hero-viz-dot is-google"></span>
              <span class="hero-viz-dot is-perplexity"></span>
              <span class="hero-viz-title">Live audit · 4 providers</span>
              <span class="hero-viz-tag">+12 pts</span>
            </div>
            <div class="hero-viz-body">
              <div
                v-for="(p, idx) in heroProviders"
                :key="p.name"
                class="hero-viz-row"
                :style="{ animationDelay: (0.2 + idx * 0.18) + 's' }"
              >
                <div class="hero-viz-row-head">
                  <span class="hero-viz-provider">
                    <span class="hero-viz-dot" :class="'is-' + p.key"></span>
                    {{ p.name }}
                  </span>
                  <span class="hero-viz-pct">{{ p.pct }}%</span>
                </div>
                <div class="hero-viz-bar">
                  <div
                    class="hero-viz-bar-fill"
                    :class="'is-' + p.key"
                    :style="{ '--target-w': p.pct + '%', animationDelay: (0.3 + idx * 0.18) + 's' }"
                  ></div>
                </div>
                <div class="hero-viz-meta">{{ p.cited }} citations · {{ p.sources }}</div>
              </div>
            </div>
            <div class="hero-viz-foot">
              <span class="hero-viz-pulse"></span>
              <span>Brand mentioned in 38% of category prompts</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Background blur orbs ═══ -->
    <div class="orb orb-1" aria-hidden="true"></div>
    <div class="orb orb-2" aria-hidden="true"></div>
    <div class="orb orb-3" aria-hidden="true"></div>

    <!-- ═══ Trust strip ═══ -->
    <section class="trust anim" data-anim="fade-up">
      <div class="marquee">
        <div class="marquee-track">
          <span class="marquee-item is-label">Trusted Probes</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">Anthropic Claude</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">OpenAI GPT-4</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">Google Gemini</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">Perplexity</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">DeepSeek (synthesis)</span>
          <span class="marquee-sep">·</span>
          <!-- duplicate for seamless loop -->
          <span class="marquee-item is-label">Trusted Probes</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">Anthropic Claude</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">OpenAI GPT-4</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">Google Gemini</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">Perplexity</span>
          <span class="marquee-sep">·</span>
          <span class="marquee-item">DeepSeek (synthesis)</span>
          <span class="marquee-sep">·</span>
        </div>
      </div>
    </section>

    <!-- ═══ Stats / Why GEO matters ═══ -->
    <section class="stats anim" data-anim="fade-up" ref="statsSection">
      <div class="wrap">
        <h2 class="sec-h sec-h-grad anim" data-anim="fade-up">AI search is the new search.<br/><em>Your brand isn't ready for it.</em></h2>
        <p class="sec-sub anim" data-anim="fade-up" data-delay="60">
          ChatGPT and Perplexity already shape millions of buying decisions every day.
          The brands that show up in those answers are the ones writing the right things in the right places.
        </p>
        <div class="count-up-grid">
          <div class="count-up-card anim" data-anim="fade-up" data-delay="80">
            <div class="count-up-num">{{ stat0Display }}<span class="count-up-suffix">%</span></div>
            <div class="count-up-label">Buyers using LLMs to research</div>
            <div class="count-up-note">of B2B buyers say AI assistants influence their purchase research</div>
          </div>
          <div class="count-up-card anim" data-anim="fade-up" data-delay="160">
            <div class="count-up-num">{{ stat1Display }}<span class="count-up-suffix">x</span></div>
            <div class="count-up-label">Visibility gap</div>
            <div class="count-up-note">average gap between dominant brand and tail brand in LLM citations</div>
          </div>
          <div class="count-up-card anim" data-anim="fade-up" data-delay="240">
            <div class="count-up-num"><span class="count-up-prefix">&lt;</span>{{ stat2Display }}<span class="count-up-suffix">%</span></div>
            <div class="count-up-label">Tracking GEO</div>
            <div class="count-up-note">of brands actively measure their LLM presence today</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Feature showcase — alternating rows ═══ -->
    <section class="feature-showcase" id="features">
      <div class="wrap">
        <div
          v-for="(f, i) in showcaseFeatures"
          :key="f.key"
          class="feature-row anim"
          :class="{ 'is-reverse': i % 2 === 1 }"
          data-anim="fade-up"
        >
          <div class="feature-copy">
            <span class="feature-eyebrow">{{ f.eyebrow }}</span>
            <h2 class="feature-h">{{ f.headline }}</h2>
            <p class="feature-desc">{{ f.desc }}</p>
            <ul class="feature-bullets">
              <li v-for="b in f.bullets" :key="b"><span class="feature-bullet-dot"></span>{{ b }}</li>
            </ul>
          </div>
          <div class="feature-visual" :class="'is-' + f.key">
            <!-- PROMPT LIBRARY -->
            <div v-if="f.key === 'prompt'" class="mock-card">
              <div class="mock-search">
                <span class="mock-search-icon"></span>
                <span class="mock-search-text">best ai analytics tool for small saas</span>
                <span class="mock-search-caret">|</span>
              </div>
              <div class="mock-rows">
                <div v-for="(p, idx) in promptRows" :key="p.q" class="mock-prompt-row" :style="{ animationDelay: (0.2 + idx * 0.18) + 's' }">
                  <span class="mock-q">{{ p.q }}</span>
                  <span class="mock-chip" :class="'is-' + p.style">{{ p.style }}</span>
                  <div class="mock-trend">
                    <div class="mock-trend-bar" :style="{ '--target-w': p.trend + '%', animationDelay: (0.4 + idx * 0.18) + 's' }"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- MULTI-LLM PROBING -->
            <div v-else-if="f.key === 'probe'" class="mock-card mock-grid">
              <div v-for="(p, idx) in heroProviders" :key="p.key" class="mock-mini" :style="{ animationDelay: (0.15 + idx * 0.15) + 's' }">
                <div class="mock-mini-head">
                  <span class="hero-viz-dot" :class="'is-' + p.key"></span>
                  <span class="mock-mini-name">{{ p.name }}</span>
                  <span class="mock-mini-pct">{{ p.pct }}%</span>
                </div>
                <div class="hero-viz-bar">
                  <div class="hero-viz-bar-fill" :class="'is-' + p.key" :style="{ '--target-w': p.pct + '%', animationDelay: (0.3 + idx * 0.15) + 's' }"></div>
                </div>
                <div class="mock-mini-meta">{{ p.cited }} citations</div>
              </div>
            </div>

            <!-- SOURCE INFLUENCE -->
            <div v-else-if="f.key === 'source'" class="mock-card">
              <div class="mock-source-title">Source mix per provider</div>
              <div v-for="(s, idx) in sourceShares" :key="s.provider" class="mock-source-row" :style="{ animationDelay: (0.15 + idx * 0.12) + 's' }">
                <span class="mock-source-label">{{ s.provider }}</span>
                <div class="mock-stack">
                  <span v-for="seg in s.segments" :key="seg.cls" class="mock-seg" :class="'seg-' + seg.cls" :style="{ '--target-w': seg.pct + '%', animationDelay: (0.3 + idx * 0.12) + 's' }"></span>
                </div>
              </div>
              <div class="mock-source-legend">
                <span><i class="seg-reddit"></i>Reddit</span>
                <span><i class="seg-news"></i>News</span>
                <span><i class="seg-wiki"></i>Wikipedia</span>
                <span><i class="seg-blog"></i>Blogs</span>
                <span><i class="seg-own"></i>Your site</span>
              </div>
            </div>

            <!-- CONTENT STUDIO -->
            <div v-else-if="f.key === 'studio'" class="mock-card">
              <div class="mock-draft-head">
                <span class="mock-chip is-draft">Draft</span>
                <span class="mock-chip-prov">Claude</span>
              </div>
              <div class="mock-draft-title">How AI analytics tools rank for SMB SaaS in 2026</div>
              <div class="mock-draft-line w-95"></div>
              <div class="mock-draft-line w-88"></div>
              <div class="mock-draft-line w-92"></div>
              <div class="mock-draft-line w-70"></div>
              <div class="mock-draft-line w-85"></div>
              <div class="mock-draft-actions">
                <button class="mock-btn">Save</button>
                <button class="mock-btn">Approve</button>
                <button class="mock-btn is-primary">Publish</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Audit loop diagram ═══ -->
    <section class="loop-diagram anim" data-anim="fade-up">
      <div class="wrap">
        <h2 class="sec-h sec-h-grad anim" data-anim="fade-up">A closed loop,<br/><em>not a one-shot report.</em></h2>
        <p class="sec-sub anim" data-anim="fade-up" data-delay="60">
          Audit, fix, re-probe, attribute. Every step compounds the last.
        </p>
        <div class="loop-track">
          <div v-for="(step, i) in loopSteps" :key="step.label" class="loop-step anim" data-anim="fade-up" :data-delay="i * 70">
            <div class="loop-icon" v-html="step.icon"></div>
            <div class="loop-num">{{ i + 1 }}</div>
            <div class="loop-label">{{ step.label }}</div>
            <div class="loop-desc">{{ step.desc }}</div>
            <div v-if="i < loopSteps.length - 1" class="loop-arrow" aria-hidden="true">
              <svg viewBox="0 0 40 12" width="40" height="12"><path d="M0 6 H34 M28 1 L34 6 L28 11" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Quote / pilot ═══ -->
    <section class="pull-quote anim" data-anim="fade-up">
      <div class="wrap">
        <blockquote class="pq-text">
          <span class="pq-mark">&ldquo;</span>
          We were measuring SEO every week and missing the entire AI side of search.
          Within two weeks of running this we found three Reddit threads where
          competitors had locked us out &mdash; and shipped fixes.
        </blockquote>
        <div class="pq-attr">Internal pilot &middot; Q1 2026</div>
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

    <!-- ═══ FAQ ═══ -->
    <section class="faq anim" data-anim="fade-up">
      <div class="wrap faq-wrap">
        <h2 class="sec-h sec-h-grad anim" data-anim="fade-up">Questions,<br/><em>answered plainly.</em></h2>
        <div class="faq-list">
          <details v-for="(item, i) in faqItems" :key="i" class="faq-item anim" data-anim="fade-up" :data-delay="i * 60">
            <summary>
              <span>{{ item.q }}</span>
              <span class="faq-plus" aria-hidden="true"></span>
            </summary>
            <div class="faq-a">{{ item.a }}</div>
          </details>
        </div>
      </div>
    </section>

    <!-- ═══ Final CTA ═══ -->
    <section class="final-cta anim" data-anim="fade-up" ref="finalCtaSection">
      <div class="final-cta-glow" aria-hidden="true"></div>
      <div class="wrap cta-inner">
        <h2>Ready to grow <em>smarter?</em></h2>
        <p>Start your AI visibility audit in minutes.</p>
        <router-link to="/register" class="btn-primary">Get Started</router-link>
      </div>
    </section>

    <!-- ═══ Sticky CTA pill ═══ -->
    <transition name="sticky-cta">
      <router-link
        v-if="showStickyCta"
        to="/register"
        class="sticky-cta"
      >
        Run a free audit
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
      </router-link>
    </transition>

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
  await typeWriter(twLine1.value, 'AI VISIBILITY,', 80)
  await new Promise(r => setTimeout(r, 200))
  await typeWriter(twLine2.value, 'MEASURED.', 70)
  await new Promise(r => setTimeout(r, 200))
  await typeWriter(twLine3.value, 'OPTIMIZED.', 70)
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

  // Count-up stats observer
  let statsObs = null
  if (statsSection.value) {
    statsObs = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { animateStats(); statsObs && statsObs.disconnect() } })
    }, { threshold: 0.3 })
    statsObs.observe(statsSection.value)
  }

  // Sticky CTA: show after hero, hide on final CTA
  const heroEl = document.querySelector('.hero')
  let heroObs = null
  if (heroEl) {
    heroObs = new IntersectionObserver((entries) => {
      entries.forEach(e => { pastHero = !e.isIntersecting || e.intersectionRatio < 0.2; updateStickyCta() })
    }, { threshold: [0, 0.2, 0.5] })
    heroObs.observe(heroEl)
  }
  let finalObs = null
  if (finalCtaSection.value) {
    finalObs = new IntersectionObserver((entries) => {
      entries.forEach(e => { onFinalCta = e.isIntersecting; updateStickyCta() })
    }, { threshold: 0.2 })
    finalObs.observe(finalCtaSection.value)
  }

  onUnmounted(() => {
    window.removeEventListener('scroll', onScroll)
    obs.disconnect()
    statsObs && statsObs.disconnect()
    heroObs && heroObs.disconnect()
    finalObs && finalObs.disconnect()
    clearInterval(cycleTimer)
    stopFeatureAutoAdvance()
  })
})

const categories = ['ChatGPT', 'Claude', 'Gemini', 'Perplexity']
const heroProviders = [
  { key: 'anthropic',  name: 'Claude',     pct: 47, cited: 12, sources: 'Reddit · TechCrunch · Wikipedia' },
  { key: 'openai',     name: 'GPT-4',      pct: 38, cited:  8, sources: 'Wikipedia · Medium · NYT' },
  { key: 'google',     name: 'Gemini',     pct: 52, cited: 15, sources: 'BBC · Bloomberg · gov sites' },
  { key: 'perplexity', name: 'Perplexity', pct: 64, cited: 21, sources: 'Reddit · Quora · Stack Overflow' },
]

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

/* ── Showcase features (alternating rows) ── */
const showcaseFeatures = [
  {
    key: 'prompt',
    eyebrow: 'PROMPT LIBRARY',
    headline: 'Test what your customers actually ask AI.',
    desc: "We mine real demand from Reddit, Quora, and search trends, then let DeepSeek paraphrase variations. Your audit set looks like real user questions, not SEO listicles.",
    bullets: [
      'Real demand mined from Reddit, Quora, and Google Trends',
      'DeepSeek-generated paraphrase variants for coverage',
      'Style + length chips to match how buyers actually search',
    ],
  },
  {
    key: 'probe',
    eyebrow: 'MULTI-LLM PROBING',
    headline: 'Run the same prompts across Claude, GPT-4, Gemini, and Perplexity in one audit.',
    desc: "We fan out asynchronously, capture the raw responses, and extract every brand mention, citation, and claim. One score, four perspectives.",
    bullets: [
      'Async fan-out across all four target LLMs',
      'Extract brand mentions, citations, and claims',
      'One unified visibility score, four perspectives',
    ],
  },
  {
    key: 'source',
    eyebrow: 'SOURCE INFLUENCE',
    headline: 'See exactly where each LLM gets its answers in your category.',
    desc: "Perplexity reads from Reddit. Gemini leans on news. Claude favours Wikipedia. Knowing which source a model trusts is half the battle.",
    bullets: [
      'Per-provider source mix breakdown',
      'Citation confidence scoring',
      'Spot which Reddit threads or articles dominate',
    ],
  },
  {
    key: 'studio',
    eyebrow: 'CONTENT STUDIO',
    headline: 'Auto-draft the content that closes your gaps. Publish in one click.',
    desc: "We turn each visibility gap into a brief, draft it grounded in your verified Brand Vault facts, and publish to WordPress / Webflow / Shopify / HubSpot. Re-probe in 14 days, attribute the lift.",
    bullets: [
      'Brand Vault-grounded drafts (no hallucinations)',
      'One-click publish to WordPress, Webflow, Shopify, HubSpot',
      'Re-probe in 14 days to attribute the lift',
    ],
  },
]

const promptRows = [
  { q: 'best ai analytics tool for small saas', style: 'comparison', trend: 82 },
  { q: 'how to track llm visibility in 2026', style: 'how-to', trend: 64 },
  { q: 'fetchbot vs bluefish alternatives', style: 'vs', trend: 47 },
]

const sourceShares = [
  { provider: 'Claude',     segments: [{cls:'reddit',pct:18},{cls:'news',pct:14},{cls:'wiki',pct:38},{cls:'blog',pct:20},{cls:'own',pct:10}] },
  { provider: 'GPT-4',      segments: [{cls:'reddit',pct:12},{cls:'news',pct:24},{cls:'wiki',pct:30},{cls:'blog',pct:24},{cls:'own',pct:10}] },
  { provider: 'Gemini',     segments: [{cls:'reddit',pct:10},{cls:'news',pct:42},{cls:'wiki',pct:18},{cls:'blog',pct:22},{cls:'own',pct:8}] },
  { provider: 'Perplexity', segments: [{cls:'reddit',pct:38},{cls:'news',pct:16},{cls:'wiki',pct:12},{cls:'blog',pct:22},{cls:'own',pct:12}] },
]

/* ── Audit loop diagram ── */
const loopSteps = [
  { label: 'Search', desc: 'Mine real prompts',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>' },
  { label: 'Audit', desc: 'Probe four LLMs',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>' },
  { label: 'Extract', desc: 'Pull citations',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>' },
  { label: 'Verify', desc: 'Brand Vault check',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l8 4v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6z"/><path d="M9 12l2 2 4-4"/></svg>' },
  { label: 'Generate', desc: 'Draft + publish',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 1 1 3 3L7 19l-4 1 1-4z"/></svg>' },
  { label: 'Re-probe', desc: 'Attribute the lift',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>' },
]

/* ── FAQ items ── */
const faqItems = [
  { q: 'Is this just SEO with extra steps?',
    a: 'No. SEO measures Google rankings; we measure how often AI assistants like ChatGPT mention you in their answers. Separate signal, separate playbook.' },
  { q: 'How is this different from Bluefish or Evertune?',
    a: 'We measure AND generate the content to close gaps. They diagnose, you hire writers. We give you SMB-friendly pricing and the full loop.' },
  { q: 'Will using DeepSeek for synthesis affect the audit results?',
    a: 'No. Audits run only against the four target LLMs (Claude, GPT-4, Gemini, Perplexity). DeepSeek is used purely for cheap offline tooling.' },
  { q: 'Do I need to install a tracking pixel?',
    a: 'No. We probe LLMs directly via API. Connect your website URL and we crawl it for Brand Vault facts, but no script lives on your site.' },
  { q: 'How accurate are the citations?',
    a: 'Perplexity and Gemini grounded mode return native citations, so 100% accurate there. Claude and GPT-4 are extracted via regex + LLM-assisted parsing; we mark each citation with a confidence score.' },
]

/* ── Animated count-up stats ── */
const STAT_TARGETS = [74, 3.2, 10]
const stat0 = ref(0)
const stat1 = ref(0)
const stat2 = ref(0)
const stat0Display = computed(() => Math.round(stat0.value).toString())
const stat1Display = computed(() => stat1.value.toFixed(1))
const stat2Display = computed(() => Math.round(stat2.value).toString())
const statsSection = ref(null)
let statsAnimated = false

function animateStats() {
  if (statsAnimated) return
  statsAnimated = true
  const start = performance.now()
  const dur = 1600
  function frame(t) {
    const p = Math.min(1, (t - start) / dur)
    const eased = 1 - Math.pow(1 - p, 3)
    stat0.value = STAT_TARGETS[0] * eased
    stat1.value = STAT_TARGETS[1] * eased
    stat2.value = STAT_TARGETS[2] * eased
    if (p < 1) requestAnimationFrame(frame)
  }
  requestAnimationFrame(frame)
}

/* ── Sticky CTA visibility ── */
const showStickyCta = ref(false)
const finalCtaSection = ref(null)
let pastHero = false
let onFinalCta = false

function updateStickyCta() {
  showStickyCta.value = pastHero && !onFinalCta
}
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
.hero { padding: 140px 0 80px; }
.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  gap: 64px;
  align-items: center;
}
@media (max-width: 980px) {
  .hero-grid { grid-template-columns: 1fr; gap: 40px; }
}
.hero-eyebrow {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--brand-accent, #c9a050);
  background: rgba(201, 160, 80, 0.12);
  padding: 6px 12px;
  border-radius: 9999px;
  margin-bottom: 18px;
}
.hero-word-cycler {
  display: inline-block;
  position: relative;
  min-width: 7.5em;
  vertical-align: baseline;
}
.hero-word {
  display: inline-block;
  color: var(--brand-accent, #c9a050);
  font-weight: 600;
}
.hero-bullets {
  list-style: none;
  margin: 28px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  font-size: 14px;
  color: #6e6a65;
}
.hero-bullets li { display: flex; align-items: center; gap: 10px; }
.hero-bullet-dot {
  width: 6px; height: 6px; border-radius: 9999px;
  background: var(--brand-accent, #c9a050);
  flex-shrink: 0;
}

/* Framer-style hero visualisation */
.hero-viz {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 22px;
  padding: 22px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 24px 60px rgba(15, 23, 42, 0.10);
  position: relative;
  overflow: hidden;
}
.hero-viz::before {
  content: '';
  position: absolute;
  inset: -40%;
  background: radial-gradient(ellipse at top right, rgba(201, 160, 80, 0.10), transparent 60%);
  pointer-events: none;
}
.hero-viz-head {
  display: flex; align-items: center; gap: 6px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  margin-bottom: 16px;
}
.hero-viz-title {
  margin-left: 8px;
  font-size: 12px;
  color: #6e6a65;
  font-weight: 500;
}
.hero-viz-tag {
  margin-left: auto;
  display: inline-flex; align-items: center;
  padding: 3px 10px;
  border-radius: 9999px;
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
  font-size: 12px;
  font-weight: 600;
}
.hero-viz-dot {
  width: 8px; height: 8px; border-radius: 9999px;
  flex-shrink: 0;
  background: #cbd5e1;
}
.hero-viz-dot.is-anthropic  { background: #d97706; }
.hero-viz-dot.is-openai     { background: #10b981; }
.hero-viz-dot.is-google     { background: #4285f4; }
.hero-viz-dot.is-perplexity { background: #5b6cff; }

.hero-viz-row {
  margin-bottom: 16px;
  opacity: 0;
  transform: translateY(6px);
  animation: hero-row-in 0.5s ease-out forwards;
}
.hero-viz-row:last-child { margin-bottom: 0; }
@keyframes hero-row-in {
  to { opacity: 1; transform: translateY(0); }
}
.hero-viz-row-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 6px;
}
.hero-viz-provider {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 600; color: #1f2937;
}
.hero-viz-pct {
  font-size: 13px; font-weight: 600; color: #1f2937;
  font-variant-numeric: tabular-nums;
}
.hero-viz-bar {
  position: relative;
  height: 8px;
  background: rgba(15, 23, 42, 0.06);
  border-radius: 9999px;
  overflow: hidden;
}
.hero-viz-bar-fill {
  position: absolute;
  inset: 0 auto 0 0;
  width: 0;
  border-radius: 9999px;
  animation: hero-bar-fill 1.1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.hero-viz-bar-fill.is-anthropic  { background: linear-gradient(90deg, #fbbf24, #d97706); }
.hero-viz-bar-fill.is-openai     { background: linear-gradient(90deg, #34d399, #059669); }
.hero-viz-bar-fill.is-google     { background: linear-gradient(90deg, #60a5fa, #2563eb); }
.hero-viz-bar-fill.is-perplexity { background: linear-gradient(90deg, #818cf8, #4338ca); }
@keyframes hero-bar-fill {
  to { width: var(--target-w); }
}
.hero-viz-meta {
  margin-top: 6px;
  font-size: 11.5px;
  color: #94a3b8;
}
.hero-viz-foot {
  display: flex; align-items: center; gap: 8px;
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
  font-size: 12.5px;
  color: #6e6a65;
}
.hero-viz-pulse {
  width: 8px; height: 8px;
  border-radius: 9999px;
  background: #10b981;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.55);
  animation: hero-pulse 1.6s ease-out infinite;
  flex-shrink: 0;
}
@keyframes hero-pulse {
  70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

/* word-cycle transition (reused from the deleted features section) */
.word-cycle-enter-active, .word-cycle-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
  display: inline-block;
}
.word-cycle-enter-from { opacity: 0; transform: translateY(8px); }
.word-cycle-leave-to   { opacity: 0; transform: translateY(-8px); position: absolute; }
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

/* ═════════════════════════════════════════
   Framer-style enhancements
   Trust strip · Stats · Feature showcase
   Loop diagram · Quote · FAQ · Sticky CTA
   ═════════════════════════════════════════ */

/* ── Smooth scroll (global, unscoped) ── */
</style>
<style>
:root { scroll-behavior: smooth; }
</style>
<style scoped>

/* ── Section heading shared ── */
.sec-sub {
  max-width: 640px;
  margin: 14px auto 48px;
  text-align: center;
  font-size: 17px;
  line-height: 1.55;
  color: #5e6b73;
}
.sec-h-grad {
  background: linear-gradient(110deg, #131718 0%, #131718 55%, var(--brand-accent, #c9a050) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
  font-weight: 600;
}

/* ── Background blur orbs ── */
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.32;
  pointer-events: none;
  z-index: 0;
  background: radial-gradient(circle, var(--brand-accent, #c9a050) 0%, rgba(201,160,80,0) 70%);
}
.orb-1 { width: 520px; height: 520px; top: 600px; left: -180px; animation: orbDrift 22s ease-in-out infinite; }
.orb-2 { width: 420px; height: 420px; top: 1900px; right: -160px; opacity: 0.24; animation: orbDrift 28s ease-in-out -8s infinite reverse; }
.orb-3 { width: 460px; height: 460px; top: 3400px; left: 40%; opacity: 0.18; animation: orbDrift 32s ease-in-out -14s infinite; }
@keyframes orbDrift {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(40px, -30px) scale(1.08); }
}

/* ── Trust strip / marquee ── */
.trust {
  position: relative;
  padding: 32px 0 12px;
  overflow: hidden;
  z-index: 1;
}
.marquee {
  position: relative;
  overflow: hidden;
  mask-image: linear-gradient(90deg, transparent 0, #000 12%, #000 88%, transparent 100%);
  -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 12%, #000 88%, transparent 100%);
}
.marquee-track {
  display: inline-flex;
  align-items: center;
  gap: 24px;
  white-space: nowrap;
  animation: marqueeRoll 30s linear infinite;
  will-change: transform;
}
.marquee:hover .marquee-track { animation-play-state: paused; }
.marquee-item {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: #5e6b73;
  font-family: 'Geist', 'Plus Jakarta Sans', sans-serif;
}
.marquee-item.is-label {
  color: var(--brand-accent, #c9a050);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.18em;
  font-size: 12px;
}
.marquee-sep { color: #c9c2b6; font-size: 14px; }
@keyframes marqueeRoll {
  from { transform: translateX(0%); }
  to   { transform: translateX(-50%); }
}

/* ── Stats / count-up ── */
.stats {
  position: relative;
  padding: 96px 0 80px;
  z-index: 1;
}
.count-up-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-top: 12px;
}
.count-up-card {
  background: #ffffff;
  border: 1px solid #ece6da;
  border-radius: 18px;
  padding: 36px 28px;
  text-align: left;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.count-up-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 40px -24px rgba(20, 23, 24, 0.18);
  border-color: #d9cfbb;
}
.count-up-num {
  font-family: 'DM Serif Display', 'Plus Jakarta Sans', serif;
  font-size: 64px;
  line-height: 1;
  color: #131718;
  letter-spacing: -0.03em;
  display: flex;
  align-items: baseline;
  gap: 2px;
}
.count-up-prefix, .count-up-suffix {
  font-size: 36px;
  color: var(--brand-accent, #c9a050);
}
.count-up-label {
  margin-top: 18px;
  font-size: 15px;
  font-weight: 600;
  color: #131718;
  letter-spacing: -0.01em;
}
.count-up-note {
  margin-top: 6px;
  font-size: 13.5px;
  color: #6b7680;
  line-height: 1.5;
}

/* ── Feature showcase ── */
.feature-showcase {
  position: relative;
  padding: 80px 0 40px;
  z-index: 1;
}
.feature-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  align-items: center;
  padding: 70px 0;
  min-height: 60vh;
}
.feature-row.is-reverse .feature-copy { order: 2; }
.feature-row.is-reverse .feature-visual { order: 1; }
.feature-eyebrow {
  font-family: 'Geist', sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.22em;
  color: var(--brand-accent, #c9a050);
  text-transform: uppercase;
}
.feature-h {
  margin: 16px 0 18px;
  font-size: 38px;
  line-height: 1.12;
  font-weight: 600;
  letter-spacing: -0.025em;
  color: #131718;
}
.feature-desc {
  max-width: 36rem;
  font-size: 16.5px;
  line-height: 1.6;
  color: #4a5560;
}
.feature-bullets {
  list-style: none;
  padding: 0;
  margin: 22px 0 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.feature-bullets li {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 14.5px;
  color: #2d3640;
}
.feature-bullet-dot {
  width: 8px; height: 8px;
  margin-top: 7px;
  border-radius: 50%;
  background: var(--brand-accent, #c9a050);
  flex-shrink: 0;
  box-shadow: 0 0 0 4px rgba(201, 160, 80, 0.12);
}

/* Mock visuals shared */
.feature-visual {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}
.mock-card {
  width: 100%;
  max-width: 460px;
  background: #ffffff;
  border: 1px solid #ece6da;
  border-radius: 18px;
  padding: 22px;
  box-shadow: 0 30px 60px -32px rgba(20, 23, 24, 0.22);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.mock-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 36px 70px -32px rgba(20, 23, 24, 0.28);
}
.mock-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8f4ec;
  border: 1px solid #ece6da;
  font-size: 13.5px;
  color: #2d3640;
}
.mock-search-icon {
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 1.6px solid #8a8275;
  position: relative;
}
.mock-search-icon::after {
  content: ''; position: absolute;
  width: 6px; height: 1.6px;
  background: #8a8275;
  bottom: -3px; right: -3px;
  transform: rotate(45deg);
}
.mock-search-text { flex: 1; }
.mock-search-caret {
  color: var(--brand-accent, #c9a050);
  animation: caretBlink 1s steps(1) infinite;
}
@keyframes caretBlink { 50% { opacity: 0; } }

.mock-rows { margin-top: 14px; display: flex; flex-direction: column; gap: 10px; }
.mock-prompt-row {
  display: grid;
  grid-template-columns: 1fr auto 80px;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fbf8f1;
  border: 1px solid #f0e9d9;
  opacity: 0;
  animation: fadeSlide 0.55s ease forwards;
}
@keyframes fadeSlide { from { opacity:0; transform: translateY(6px);} to {opacity:1; transform:none;} }
.mock-q { font-size: 13px; color: #2d3640; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.mock-chip {
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(201,160,80,0.14);
  color: #8a6d2a;
}
.mock-chip.is-comparison { background: rgba(74,127,176,0.14); color: #345f86; }
.mock-chip.is-how-to { background: rgba(110,165,110,0.16); color: #3f6b3f; }
.mock-chip.is-vs { background: rgba(198,90,47,0.14); color: #8a3d18; }
.mock-trend {
  height: 6px; border-radius: 4px;
  background: #ece6da;
  overflow: hidden;
}
.mock-trend-bar {
  width: 0; height: 100%;
  background: linear-gradient(90deg, var(--brand-accent, #c9a050), #d9b770);
  border-radius: 4px;
  animation: barFill 1.1s cubic-bezier(0.22,1,0.36,1) forwards;
}
@keyframes barFill { to { width: var(--target-w, 50%); } }

/* Probe mini grid */
.mock-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.mock-mini {
  background: #fbf8f1;
  border: 1px solid #f0e9d9;
  border-radius: 12px;
  padding: 12px;
  opacity: 0;
  animation: fadeSlide 0.55s ease forwards;
}
.mock-mini-head { display:flex; align-items:center; gap:8px; font-size: 12.5px; }
.mock-mini-name { flex: 1; font-weight: 600; color: #2d3640; }
.mock-mini-pct { color: var(--brand-accent, #c9a050); font-weight: 600; }
.mock-mini-meta { margin-top: 8px; font-size: 11.5px; color: #6b7680; }

/* Source bars */
.mock-source-title {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #8a8275;
  margin-bottom: 12px;
  font-weight: 600;
}
.mock-source-row {
  display: grid;
  grid-template-columns: 86px 1fr;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  opacity: 0;
  animation: fadeSlide 0.55s ease forwards;
}
.mock-source-label { font-size: 13px; color: #2d3640; font-weight: 500; }
.mock-stack {
  display: flex;
  height: 14px;
  border-radius: 6px;
  overflow: hidden;
  background: #f0e9d9;
}
.mock-seg {
  width: 0;
  height: 100%;
  display: block;
  animation: barFill 1.1s cubic-bezier(0.22,1,0.36,1) forwards;
}
.seg-reddit { background: #c65a2f; }
.seg-news   { background: #4a7fb0; }
.seg-wiki   { background: #6b7680; }
.seg-blog   { background: #d9b770; }
.seg-own    { background: var(--brand-accent, #c9a050); }
.mock-source-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
  font-size: 11.5px;
  color: #6b7680;
}
.mock-source-legend i {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 3px;
  margin-right: 6px;
  vertical-align: -1px;
}

/* Studio draft mock */
.mock-draft-head { display:flex; gap: 8px; align-items:center; margin-bottom: 10px; }
.mock-chip.is-draft { background: rgba(20,23,24,0.08); color: #2d3640; }
.mock-chip-prov {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(201,160,80,0.14);
  color: #8a6d2a;
  font-weight: 600;
}
.mock-draft-title {
  font-family: 'DM Serif Display', serif;
  font-size: 19px;
  line-height: 1.25;
  color: #131718;
  margin: 4px 0 16px;
}
.mock-draft-line {
  height: 8px;
  border-radius: 4px;
  background: #f0e9d9;
  margin-bottom: 8px;
}
.mock-draft-line.w-95 { width: 95%; }
.mock-draft-line.w-88 { width: 88%; }
.mock-draft-line.w-92 { width: 92%; }
.mock-draft-line.w-70 { width: 70%; }
.mock-draft-line.w-85 { width: 85%; }
.mock-draft-actions {
  display: flex; gap: 8px; margin-top: 16px;
}
.mock-btn {
  border: 1px solid #ece6da;
  background: #fff;
  color: #2d3640;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  padding: 7px 14px;
  cursor: pointer;
  transition: all 0.18s ease;
}
.mock-btn:hover { background: #f8f4ec; }
.mock-btn.is-primary {
  background: #131718;
  color: #fff;
  border-color: #131718;
}

/* ── Loop diagram ── */
.loop-diagram {
  position: relative;
  padding: 96px 0 80px;
  z-index: 1;
}
.loop-track {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.loop-step {
  flex: 1 1 140px;
  min-width: 140px;
  position: relative;
  background: #ffffff;
  border: 1px solid #ece6da;
  border-radius: 14px;
  padding: 18px 16px 16px;
  text-align: center;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.loop-step:hover { transform: translateY(-2px); box-shadow: 0 18px 40px -24px rgba(20,23,24,0.2); }
.loop-icon {
  display: inline-flex;
  width: 38px; height: 38px;
  border-radius: 10px;
  background: rgba(201,160,80,0.12);
  color: var(--brand-accent, #c9a050);
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}
.loop-num {
  position: absolute;
  top: 10px; right: 12px;
  font-size: 11px;
  font-weight: 700;
  color: #c0b8a6;
  letter-spacing: 0.1em;
}
.loop-label { font-size: 14.5px; font-weight: 700; color: #131718; }
.loop-desc { margin-top: 4px; font-size: 12.5px; color: #6b7680; }
.loop-arrow {
  position: absolute;
  right: -22px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--brand-accent, #c9a050);
  opacity: 0.7;
  animation: arrowPulse 2.4s ease-in-out infinite;
}
@keyframes arrowPulse { 0%,100% { opacity: 0.4; transform: translate(-2px,-50%);} 50% { opacity: 0.95; transform: translate(2px,-50%);} }

/* ── Pull quote ── */
.pull-quote {
  position: relative;
  padding: 80px 0;
  z-index: 1;
}
.pq-text {
  max-width: 880px;
  margin: 0 auto;
  font-family: 'DM Serif Display', serif;
  font-size: 32px;
  line-height: 1.35;
  color: #131718;
  letter-spacing: -0.015em;
  text-align: center;
  position: relative;
}
.pq-mark {
  display: block;
  font-size: 80px;
  line-height: 0.4;
  color: var(--brand-accent, #c9a050);
  margin-bottom: 18px;
}
.pq-attr {
  margin-top: 24px;
  text-align: center;
  font-size: 13px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #8a8275;
  font-weight: 600;
}

/* ── FAQ ── */
.faq {
  position: relative;
  padding: 80px 0;
  z-index: 1;
}
.faq-wrap { max-width: 880px; }
.faq-list { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
.faq-item {
  background: #ffffff;
  border: 1px solid #ece6da;
  border-radius: 14px;
  padding: 4px 4px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.faq-item[open] { border-color: #d9cfbb; box-shadow: 0 18px 40px -28px rgba(20,23,24,0.18); }
.faq-item summary {
  list-style: none;
  cursor: pointer;
  padding: 18px 22px;
  font-size: 16px;
  font-weight: 600;
  color: #131718;
  display: flex;
  align-items: center;
  justify-content: space-between;
  letter-spacing: -0.01em;
}
.faq-item summary::-webkit-details-marker { display: none; }
.faq-plus {
  position: relative;
  width: 16px; height: 16px;
  flex-shrink: 0;
}
.faq-plus::before, .faq-plus::after {
  content: '';
  position: absolute;
  background: var(--brand-accent, #c9a050);
  border-radius: 1px;
  transition: transform 0.25s ease;
}
.faq-plus::before { left: 0; right: 0; top: 7px; height: 2px; }
.faq-plus::after  { top: 0; bottom: 0; left: 7px; width: 2px; }
.faq-item[open] .faq-plus::after { transform: scaleY(0); }
.faq-a {
  padding: 0 22px 20px;
  font-size: 15px;
  line-height: 1.6;
  color: #4a5560;
}

/* ── Final CTA glow ── */
.final-cta { position: relative; overflow: hidden; }
.final-cta-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 50%, rgba(201,160,80,0.18) 0%, rgba(245,239,230,0) 60%);
  pointer-events: none;
}
.final-cta .cta-inner { position: relative; z-index: 1; }
.final-cta h2 { font-size: 56px; }

/* ── Sticky CTA pill ── */
.sticky-cta {
  position: fixed;
  bottom: 22px;
  right: 22px;
  z-index: 60;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  border-radius: 999px;
  background: #131718;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.005em;
  text-decoration: none;
  box-shadow: 0 16px 40px -12px rgba(20,23,24,0.42), 0 0 0 1px rgba(255,255,255,0.04) inset;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.sticky-cta:hover {
  transform: translateY(-2px);
  box-shadow: 0 24px 50px -14px rgba(20,23,24,0.5);
}
.sticky-cta-enter-from, .sticky-cta-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
.sticky-cta-enter-active, .sticky-cta-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .count-up-grid { grid-template-columns: 1fr; }
  .feature-row { grid-template-columns: 1fr; gap: 40px; padding: 50px 0; min-height: 0; }
  .feature-row.is-reverse .feature-copy { order: 1; }
  .feature-row.is-reverse .feature-visual { order: 2; }
  .feature-h { font-size: 30px; }
  .pq-text { font-size: 24px; }
  .loop-arrow { display: none; }
  .final-cta h2 { font-size: 40px; }
}
</style>
