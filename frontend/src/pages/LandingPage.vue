<template>
  <div class="lp">
    <!-- ═══ Nav ═══ -->
    <nav class="nav" :class="{ scrolled }">
      <div class="wrap nav-row">
        <router-link to="/" class="brand">
          <svg width="32" height="32" viewBox="0 0 28 28" fill="none"><circle cx="14" cy="14" r="14" fill="#131718"/><path d="M9 10h4v8H9z M15 7h4v11h-4z" fill="#fff"/></svg>
          <span class="brand-name">FetchBot</span>
        </router-link>
        <div class="nav-links">
          <a href="#features">Features</a>
          <a href="#how">How It Works</a>
          <a href="#pricing">Pricing</a>
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
          MARKETING<br/>INTELLIGENCE,<br/><em>SIMPLIFIED.</em>
        </h1>
        <p class="hero-p anim" data-anim="fade-up" data-delay="60">
          Track visitors, score leads, audit your site, and grow<br class="hide-m"/>
          with AI — all in one platform.
        </p>
        <div class="hero-ctas anim" data-anim="fade-up" data-delay="120">
          <router-link to="/register" class="btn-primary">Start Free</router-link>
          <a href="#features" class="btn-ghost">Learn More</a>
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
                 class="carousel-card" :class="[f.tint, { expanded: activeCard === i }]"
                 @click="activeCard = activeCard === i ? -1 : i">
              <span class="card-num">{{ String(i + 1).padStart(2, '0') }}</span>
              <div class="card-visual">
                <div class="card-icon" v-html="f.icon"></div>
              </div>
              <h3 class="card-title">{{ f.title }}</h3>
              <div class="card-expand" v-if="activeCard === i">
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
            <router-link to="/register" class="price-btn" :class="{ dark: plan.featured }">{{ plan.cta }}</router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Final CTA ═══ -->
    <section class="final-cta anim" data-anim="fade-up">
      <div class="wrap cta-inner">
        <h2>Ready to grow <em>smarter?</em></h2>
        <p>Join thousands of businesses using FetchBot.</p>
        <router-link to="/register" class="btn-primary">Start Free — No Credit Card</router-link>
      </div>
    </section>

    <!-- ═══ Footer ═══ -->
    <footer class="footer">
      <div class="wrap footer-row">
        <div class="footer-brand">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none"><circle cx="14" cy="14" r="14" fill="#131718"/><path d="M9 10h4v8H9z M15 7h4v11h-4z" fill="#fff"/></svg>
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
const activeCard = ref(1)
const activeCat = ref(0)
const trackOffset = ref(0)
const trackRef = ref(null)

const cardStep = 280
const visibleCards = 4
let cycleTimer = null

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

  onUnmounted(() => {
    window.removeEventListener('scroll', onScroll)
    obs.disconnect()
    clearInterval(cycleTimer)
  })
})

const categories = ['Growth', 'Analytics', 'SEO', 'Intelligence']

const features = [
  {
    title: 'Analytics',
    desc: 'Real-time visitors, pageviews, conversions, and user flow — with AI anomaly detection.',
    replaces: 'Replaces Mixpanel',
    tint: 'tint-peach',
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M3 20V10l4-4 4 4 4-4 4 4v10" stroke-linejoin="round"/></svg>'
  },
  {
    title: 'Heatmaps',
    desc: 'See exactly where visitors click, scroll, and engage on every page of your website.',
    replaces: 'Replaces Hotjar',
    tint: 'tint-blue',
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="9" r="2"/><circle cx="16" cy="9" r="1.5" opacity=".5"/><circle cx="12" cy="15" r="2.5"/></svg>'
  },
  {
    title: 'Keywords',
    desc: 'AI keyword scoring, rank tracking, and Google Trends integration for every page.',
    replaces: 'Replaces Semrush',
    tint: 'tint-yellow',
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg>'
  },
  {
    title: 'Lead ID',
    desc: 'Identify companies visiting your site with behavioral scoring and company intel.',
    replaces: 'Replaces Clearbit',
    tint: 'tint-peach',
    icon: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="12" cy="7" r="4"/><path d="M5.5 21c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/></svg>'
  },
]

const steps = [
  { title: 'Add Your Website', desc: 'Enter your domain and we generate a tracking pixel instantly.' },
  { title: 'Install the Pixel', desc: 'Copy one line of JavaScript into your site header — takes 30 seconds.' },
  { title: 'Watch Insights Flow', desc: 'Real-time analytics and AI insights appear immediately.' },
]

const plans = [
  { name: 'Starter', price: 'Free', per: '', desc: 'For side projects.', features: ['1 website', '1,000 pageviews/mo', 'Keyword tracking (10)'], cta: 'Start Free', featured: false },
  { name: 'Growth', price: '$29', per: 'mo', desc: 'For growing businesses.', features: ['5 websites', '50,000 pageviews/mo', 'Full analytics + AI', 'Heatmaps & funnels', 'Lead identification'], cta: 'Start Free Trial', featured: true },
  { name: 'Scale', price: '$99', per: 'mo', desc: 'For agencies.', features: ['50 websites', '500,000 pageviews/mo', 'Everything in Growth', 'API access'], cta: 'Contact Sales', featured: false },
]
</script>

<style scoped>
/* ═══════════════════════════════════
   FetchBot — Travel Lab style
   White bg · League Gothic/DM Serif headlines
   Horizontal numbered card carousel
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
.brand-name { font-family: 'DM Serif Display', Georgia, serif; font-size: 20px; color: #131718; letter-spacing: -0.02em; }
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
  line-height: 0.95; letter-spacing: -0.03em;
  text-transform: uppercase;
  margin-bottom: 24px;
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
}

/* ── Framer-style word cycler ── */
.feat-word-cycler {
  display: inline-block; position: relative;
  min-width: 180px; height: 1.1em;
  vertical-align: baseline; overflow: hidden;
}
.feat-word {
  display: inline-block; position: absolute;
  left: 0; bottom: 0;
  color: #5B8DEF; font-style: italic;
  white-space: nowrap;
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
}
.feat-tab.active { color: #5B8DEF; text-decoration: underline; text-underline-offset: 4px; text-decoration-color: #5B8DEF; }
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
  transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  overflow: hidden;
}
.carousel-card.expanded {
  flex: 0 0 340px;
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
.card-icon { color: #131718; opacity: 0.7; }
.card-title {
  font-size: 18px; font-weight: 800;
  color: #131718; letter-spacing: -0.01em;
  margin-top: auto;
}

/* Expanded card details */
.card-expand { margin-top: 10px; }
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
.price-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
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
}
@media (max-width: 640px) {
  .hero-h { font-size: 2.4rem; }
  .hero-ctas { flex-direction: column; align-items: flex-start; }
}
</style>
