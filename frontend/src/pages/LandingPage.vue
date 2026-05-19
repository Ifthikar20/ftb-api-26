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
        </div>
        <div class="nav-right">
          <router-link to="/login" class="nav-link-text">Log In</router-link>
          <router-link to="/login" class="nav-cta">Get Started</router-link>
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
        </div>

        <!-- Framer-style animated visualisation -->
        <div class="hero-right anim" data-anim="fade-up" data-delay="220">
          <div class="probe">
            <!-- Prompt bar -->
            <div class="probe-prompt">
              <span class="probe-prompt-label">Prompt</span>
              <span class="probe-prompt-text">
                <span class="probe-typer">Best email marketing tool for D2C brands?</span>
                <span class="probe-caret"></span>
              </span>
            </div>

            <!-- Four streaming AI replies -->
            <div class="probe-grid">
              <div
                v-for="(p, idx) in probeReplies"
                :key="p.key"
                class="probe-card"
                :class="'is-' + p.key"
                :style="{ '--d': (idx * 0.45) + 's' }"
                @pointermove="onCardTilt"
                @pointerleave="onCardLeave"
              >
                <div class="probe-card-head">
                  <span
                    class="probe-logo"
                    :class="'is-' + p.key"
                    :aria-label="p.name + ' logo'"
                    v-html="providerLogo(p.key)"
                  ></span>
                  <span class="probe-name">{{ p.name }}</span>
                  <span class="probe-status">
                    <span class="probe-status-dot"></span>
                    <span class="probe-status-txt">answered</span>
                  </span>
                </div>
                <div class="probe-stream">
                  <span class="probe-stream-text">{{ p.before }}</span>
                  <mark class="probe-mark">{{ p.brand }}</mark>
                  <span class="probe-stream-text">{{ p.after }}</span>
                </div>
                <div class="probe-tags">
                  <span
                    v-for="src in p.sources"
                    :key="src.domain"
                    class="probe-tag"
                    :title="src.domain"
                  >
                    <img
                      class="probe-tag-fav"
                      :src="faviconFor(src.domain)"
                      :alt="''"
                      width="14" height="14"
                      loading="lazy"
                      referrerpolicy="no-referrer"
                      @error="(e) => e.target.style.display = 'none'"
                    />
                    {{ src.label }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Summary footer: ring + four count-up metric tiles -->
            <div class="probe-foot">
              <div class="probe-ring" aria-hidden="true">
                <svg viewBox="0 0 36 36">
                  <defs>
                    <linearGradient id="probe-ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%"  stop-color="#ff6b35"/>
                      <stop offset="100%" stop-color="#ff9d6b"/>
                    </linearGradient>
                  </defs>
                  <circle class="probe-ring-bg" cx="18" cy="18" r="15.9"/>
                  <circle class="probe-ring-fg" cx="18" cy="18" r="15.9"/>
                </svg>
                <span class="probe-ring-num">{{ animatedMetrics.visibility }}<i>%</i></span>
              </div>
              <div class="probe-foot-copy">
                <div class="probe-foot-h">Visibility score</div>
                <div class="probe-foot-sub">
                  Your brand surfaced in
                  <strong>{{ animatedMetrics.visibility }}%</strong>
                  of category prompts
                  <span class="probe-delta">{{ probeMetrics.visibility.delta }} this week</span>
                </div>
              </div>
            </div>

            <!-- New: live stats strip — four tiles, staggered fade-up. -->
            <div class="probe-stats">
              <div class="probe-stat" style="--d: 1.9s">
                <div class="probe-stat-h">Mentions</div>
                <div class="probe-stat-v">{{ animatedMetrics.mentions }}</div>
                <div class="probe-stat-d is-up">{{ probeMetrics.mentions.delta }}</div>
              </div>
              <div class="probe-stat" style="--d: 2.05s">
                <div class="probe-stat-h">Avg position</div>
                <div class="probe-stat-v">{{ animatedMetrics.avgPosition.toFixed(1) }}</div>
                <div class="probe-stat-d is-up">{{ probeMetrics.avgPosition.delta }}</div>
              </div>
              <div class="probe-stat" style="--d: 2.2s">
                <div class="probe-stat-h">Citations</div>
                <div class="probe-stat-v">{{ animatedMetrics.citations }}</div>
                <div class="probe-stat-d is-up">{{ probeMetrics.citations.delta }}</div>
              </div>
              <div
                class="probe-stat"
                style="--d: 2.35s"
                title="Position-Adjusted Word Count — paper eq. 3. Fraction of the AI response that cites your brand, weighted by sentence position."
              >
                <div class="probe-stat-h">Imp<sub>pwc</sub></div>
                <div class="probe-stat-v">{{ animatedMetrics.impPwc.toFixed(2) }}</div>
                <div class="probe-stat-d is-up">{{ probeMetrics.impPwc.delta }}</div>
              </div>
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

    <!-- ═══ Why you need this — ad-copy section ═══ -->
    <section class="why anim" data-anim="fade-up">
      <div class="wrap why-wrap">
        <span class="why-eyebrow">Why this exists</span>
        <h2 class="why-h">
          Your customers stopped Googling.<br/>
          <em>They started <span class="why-h-pop">asking.</span></em>
        </h2>
        <p class="why-sub">
          Every day, millions of buyers skip the search bar and ask ChatGPT, Claude,
          Gemini, or Perplexity instead. The AI gives them one answer, two competitors,
          and a recommendation. If your brand isn't in that answer — you weren't even in the room.
        </p>

        <div class="why-grid">
          <div class="why-card anim" data-anim="fade-up" data-delay="60">
            <div class="why-card-num">1</div>
            <div class="why-card-h">SEO ranks pages.<br/>AI ranks <em>brands.</em></div>
            <p>You can be #1 on Google and invisible inside ChatGPT's answer. Different game, different scoreboard.</p>
          </div>
          <div class="why-card anim" data-anim="fade-up" data-delay="140">
            <div class="why-card-num">2</div>
            <div class="why-card-h">Every missed mention<br/>is a <em>handed-over</em> sale.</div>
            <p>When the AI names your competitor and not you, the buyer takes the recommendation. No second click. No second chance.</p>
          </div>
          <div class="why-card anim" data-anim="fade-up" data-delay="220">
            <div class="why-card-num">3</div>
            <div class="why-card-h">You can't fix<br/>what you can't <em>see.</em></div>
            <p>Most brands have zero visibility into what the four major models say about them. We turn the lights on, week over week.</p>
          </div>
        </div>

        <div class="why-cta anim" data-anim="fade-up" data-delay="300">
          <span class="why-cta-line">The brands winning AI search are the ones <strong>measuring it</strong>.</span>
          <router-link to="/login" class="why-cta-btn">
            See where you stand
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
          </router-link>
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
            <!-- PROMPT LIBRARY — typewriter cycling through demand-side prompts -->
            <div v-if="f.key === 'prompt'" class="mock-card">
              <div class="mock-search">
                <span class="mock-search-icon"></span>
                <span class="mock-search-text">{{ typedPrompt }}</span>
                <span class="mock-search-caret">|</span>
              </div>
              <div class="mock-rows">
                <transition-group name="mock-row-stagger" tag="div">
                  <div
                    v-for="(p, idx) in visiblePromptRows"
                    :key="p.id"
                    class="mock-prompt-row"
                    :style="{ animationDelay: (0.05 + idx * 0.10) + 's' }"
                  >
                    <span class="mock-q">{{ p.q }}</span>
                    <span class="mock-chip" :class="'is-' + p.style">{{ p.style }}</span>
                    <div class="mock-trend">
                      <div class="mock-trend-bar" :style="{ '--target-w': p.trend + '%', animationDelay: (0.25 + idx * 0.10) + 's' }"></div>
                    </div>
                  </div>
                </transition-group>
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
            <router-link to="/login" class="price-btn" :class="{ dark: plan.featured }">{{ plan.cta }}</router-link>
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
      <video class="final-cta-video" autoplay muted loop playsinline aria-hidden="true">
        <source src="/videos/watercolor-main.mp4" type="video/mp4" />
      </video>
      <div class="final-cta-overlay" aria-hidden="true"></div>
      <div class="final-cta-glow" aria-hidden="true"></div>
      <div class="wrap cta-inner">
        <h2>Ready to grow <em>smarter?</em></h2>
        <p>Start your AI visibility audit in minutes.</p>
        <router-link to="/login" class="btn-primary">Get Started</router-link>
      </div>
    </section>

    <!-- ═══ Sticky CTA pill ═══ -->
    <transition name="sticky-cta">
      <router-link
        v-if="showStickyCta"
        to="/login"
        class="sticky-cta"
      >
        Run a free audit
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
      </router-link>
    </transition>

    <!-- ═══ Footer ═══ -->
    <footer class="footer">
      <div class="wrap">
        <!-- Top row: brand + 4 link columns -->
        <div class="footer-grid">
          <div class="footer-brand-col">
            <div class="footer-brand">
              <img src="/images/fb-logo.png" alt="FetchBot" class="footer-logo" />
              <span>FetchBot</span>
            </div>
            <p class="footer-tagline">
              Generative Engine Optimization for brands that want to be found
              by AI assistants. Measure, verify, and close the gap.
            </p>
            <div class="footer-socials">
              <a href="https://twitter.com/fetchbot" target="_blank" rel="noopener" aria-label="Twitter / X" class="footer-social">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              </a>
              <a href="https://linkedin.com/company/fetchbot" target="_blank" rel="noopener" aria-label="LinkedIn" class="footer-social">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.94v5.67H9.37V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.26 2.37 4.26 5.45zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45C23.21 24 24 23.23 24 22.28V1.72C24 .77 23.21 0 22.22 0z"/></svg>
              </a>
              <a href="https://github.com/fetchbot" target="_blank" rel="noopener" aria-label="GitHub" class="footer-social">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58v-2.04c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.74.08-.73.08-.73 1.21.09 1.85 1.24 1.85 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.66-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.66.25 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.62-5.49 5.92.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.83.58A12.01 12.01 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
              </a>
            </div>
          </div>

          <div class="footer-col">
            <div class="footer-col-title">Product</div>
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <a href="#pricing">Pricing</a>
            <a href="#faq">FAQ</a>
          </div>

          <div class="footer-col">
            <div class="footer-col-title">Resources</div>
            <router-link to="/docs">Documentation</router-link>
            <router-link to="/blog">Blog</router-link>
            <router-link to="/changelog">Changelog</router-link>
            <router-link to="/status">Status</router-link>
          </div>

          <div class="footer-col">
            <div class="footer-col-title">Company</div>
            <router-link to="/about">About</router-link>
            <router-link to="/contact">Contact us</router-link>
            <a href="mailto:hello@fetchbot.ai">hello@fetchbot.ai</a>
          </div>

          <div class="footer-col">
            <div class="footer-col-title">Legal</div>
            <router-link to="/terms">Terms of Service</router-link>
            <router-link to="/privacy">Privacy Policy</router-link>
            <router-link to="/dpa">Data Processing Agreement</router-link>
            <router-link to="/cookies">Cookie Policy</router-link>
            <router-link to="/ai-policy">Responsible AI Use</router-link>
          </div>
        </div>

        <!-- Bottom row: copy + meta links -->
        <div class="footer-bottom">
          <span class="footer-copy">© 2026 FetchBot, Inc. All rights reserved.</span>
          <div class="footer-meta">
            <span class="footer-meta-item">
              <span class="footer-status-dot"></span>
              All systems operational
            </span>
            <span class="footer-meta-divider">·</span>
            <span class="footer-meta-item">Made with care for the AI-search era</span>
          </div>
        </div>
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

// ── Hero metric count-up ─────────────────────────────────────────
// Framer-Motion-style spring-eased ramp from 0 → target on mount.
// Built without a dep — single rAF loop, easeOutCubic over 1.4s, kicks
// in 600ms after the card cascade ends so the eye lands on the new
// value just as the user finishes reading the prompt.
const animatedMetrics = ref({
  visibility: 0, mentions: 0, avgPosition: 0, citations: 0, impPwc: 0,
})
let _metricRaf = null

function _easeOutCubic(t) { return 1 - Math.pow(1 - t, 3) }

function _animateMetrics() {
  // probeMetrics is declared later in this script setup — read it
  // lazily inside the closure so the temporal-dead-zone doesn't bite.
  const targets = probeMetrics
  const start = performance.now() + 600
  const dur = 1400
  function tick(now) {
    const elapsed = Math.max(0, now - start)
    const t = Math.min(1, elapsed / dur)
    const e = _easeOutCubic(t)
    animatedMetrics.value = {
      visibility:  +(targets.visibility.value  * e).toFixed(0),
      mentions:    +(targets.mentions.value    * e).toFixed(0),
      avgPosition: +(targets.avgPosition.value * e).toFixed(1),
      citations:   +(targets.citations.value   * e).toFixed(0),
      impPwc:      +(targets.impPwc.value      * e).toFixed(2),
    }
    if (t < 1) _metricRaf = requestAnimationFrame(tick)
  }
  _metricRaf = requestAnimationFrame(tick)
}

// Magnetic-tilt for the four AI reply cards. CSS-only transform —
// JS just sets two custom props off pointer position so the
// transform stays on the compositor and never invalidates layout.
function onCardTilt(ev) {
  const el = ev.currentTarget
  const r = el.getBoundingClientRect()
  const x = (ev.clientX - r.left) / r.width  - 0.5
  const y = (ev.clientY - r.top)  / r.height - 0.5
  el.style.setProperty('--tx', `${x * 6}deg`)
  el.style.setProperty('--ty', `${-y * 6}deg`)
}
function onCardLeave(ev) {
  const el = ev.currentTarget
  el.style.setProperty('--tx', '0deg')
  el.style.setProperty('--ty', '0deg')
}

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
  _animateMetrics()

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
    if (_metricRaf) cancelAnimationFrame(_metricRaf)
    if (_promptCycleStop) _promptCycleStop()
  })

  // Demand-prompt cycler — kicks in after the page hydrates so the search
  // bar starts typing the first example almost immediately.
  setTimeout(startPromptCycle, 400)
})

const categories = ['ChatGPT', 'Claude', 'Gemini', 'Perplexity']
const heroProviders = [
  { key: 'anthropic',  name: 'Claude',     pct: 47, cited: 12, sources: 'Reddit · TechCrunch · Wikipedia' },
  { key: 'openai',     name: 'GPT-4',      pct: 38, cited:  8, sources: 'Wikipedia · Medium · NYT' },
  { key: 'google',     name: 'Gemini',     pct: 52, cited: 15, sources: 'BBC · Bloomberg · gov sites' },
  { key: 'perplexity', name: 'Perplexity', pct: 64, cited: 21, sources: 'Reddit · Quora · Stack Overflow' },
]

// Hero "probe" animation — shows the FetchBot loop: ask a prompt,
// four AIs answer, your brand surfaces in each reply.
// `sources` is `{label, domain}` so we can render the real favicon
// for each citation chip via Google's favicon CDN.
const probeReplies = [
  {
    key: 'anthropic', name: 'Claude',
    before: 'For D2C teams under 50k subscribers I usually point people to ',
    brand: 'Tidewater',
    after: '. Deliverability is solid and the segmentation builder is forgiving.',
    sources: [
      { label: 'Reddit',     domain: 'reddit.com' },
      { label: 'TechCrunch', domain: 'techcrunch.com' },
      { label: 'Wikipedia',  domain: 'wikipedia.org' },
    ],
  },
  {
    key: 'openai', name: 'GPT-4',
    before: 'A solid pick for direct-to-consumer ESPs is ',
    brand: 'Tidewater',
    after: ' — Shopify-native, AMP-email support, fair tiered pricing.',
    sources: [
      { label: 'NYT',       domain: 'nytimes.com' },
      { label: 'Medium',    domain: 'medium.com' },
      { label: 'Wikipedia', domain: 'wikipedia.org' },
    ],
  },
  {
    key: 'google', name: 'Gemini',
    before: 'Most 2026 marketing benchmarks single out ',
    brand: 'Tidewater',
    after: ' for brands that need flow automation without a vendor lock-in.',
    sources: [
      { label: 'Bloomberg', domain: 'bloomberg.com' },
      { label: 'BBC',       domain: 'bbc.com' },
      { label: 'gov',       domain: 'usa.gov' },
    ],
  },
  {
    key: 'perplexity', name: 'Perplexity',
    before: 'Top community recommendation is ',
    brand: 'Tidewater',
    after: '. Cited often for cleaner SMS hand-off and post-purchase flows.',
    sources: [
      { label: 'Quora',          domain: 'quora.com' },
      { label: 'Stack Overflow', domain: 'stackoverflow.com' },
      { label: 'Reddit',         domain: 'reddit.com' },
    ],
  },
]

// Live metrics for the hero footer — drives the stats strip + ring.
// Each tile shows a count-up animation on first mount via `useCountUp`.
const probeMetrics = {
  visibility:   { value: 38,   suffix: '%',  label: 'Visibility',  delta: '+12' },
  mentions:     { value: 56,   suffix: '',   label: 'Mentions',    delta: '+9'  },
  avgPosition:  { value: 1.4,  suffix: '',   label: 'Avg position', delta: '−0.3', deltaPositive: true },
  citations:    { value: 23,   suffix: '',   label: 'Citations',   delta: '+5'  },
  impPwc:       { value: 0.42, suffix: '',   label: 'Imp pwc',     delta: '+0.08' },
}

// Provider logo registry — inline SVGs of each AI's actual brand
// mark. Pure SVG so we don't need to ship any image asset.
const providerLogos = {
  anthropic: `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M14.8 3h-3.1L7.2 21h3.2l.95-4h4.55l.95 4h3.2L15.6 3h-.8zm-2.9 11.3 1.5-6 1.5 6h-3z"/>
  </svg>`,
  openai: `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M21.55 10.04a5.42 5.42 0 0 0-.47-4.46 5.5 5.5 0 0 0-5.92-2.63 5.42 5.42 0 0 0-4.07-1.82 5.5 5.5 0 0 0-5.25 3.81 5.42 5.42 0 0 0-3.63 2.63 5.5 5.5 0 0 0 .68 6.45 5.42 5.42 0 0 0 .47 4.46 5.5 5.5 0 0 0 5.92 2.63 5.42 5.42 0 0 0 4.08 1.82 5.5 5.5 0 0 0 5.25-3.82 5.42 5.42 0 0 0 3.62-2.63 5.5 5.5 0 0 0-.68-6.44zm-8.18 11.42a4.07 4.07 0 0 1-2.62-.95l.13-.07 4.4-2.55a.72.72 0 0 0 .37-.62v-6.23l1.86 1.08c.02 0 .03.03.03.05v5.16a4.08 4.08 0 0 1-4.17 4.13zm-8.78-3.74a4.07 4.07 0 0 1-.49-2.74l.13.08 4.4 2.55c.23.13.51.13.74 0l5.38-3.1v2.14a.07.07 0 0 1-.03.06l-4.45 2.57a4.08 4.08 0 0 1-5.58-1.49zM3.43 8.45a4.07 4.07 0 0 1 2.13-1.79V11.94a.71.71 0 0 0 .36.62l5.36 3.1-1.86 1.08a.07.07 0 0 1-.07 0L4.9 14.16a4.08 4.08 0 0 1-1.49-5.7zm15.27 3.55-5.38-3.13 1.86-1.07a.07.07 0 0 1 .07 0l4.45 2.57a4.08 4.08 0 0 1-.62 7.36V12.6a.72.72 0 0 0-.38-.62zM20.55 9c-.02-.02-.07-.05-.13-.08l-4.4-2.55a.71.71 0 0 0-.74 0l-5.38 3.1V7.32a.06.06 0 0 1 .03-.05l4.45-2.57a4.07 4.07 0 0 1 6.17 4.3zm-11.65 4.04L7.04 12c-.02-.01-.03-.04-.03-.06V6.78a4.07 4.07 0 0 1 6.68-3.13l-.13.08-4.4 2.55a.72.72 0 0 0-.37.62v6.14h.11zm1-2.18 2.4-1.39 2.4 1.39v2.76l-2.4 1.39-2.4-1.39v-2.76z"/>
  </svg>`,
  google: `<svg viewBox="0 0 24 24" aria-hidden="true">
    <defs>
      <linearGradient id="g-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%"  stop-color="#4285f4"/>
        <stop offset="50%" stop-color="#9b72cb"/>
        <stop offset="100%" stop-color="#d96570"/>
      </linearGradient>
    </defs>
    <path fill="url(#g-grad)" d="M12 2 13.6 8.2 19.8 9.8 13.6 11.4 12 17.6 10.4 11.4 4.2 9.8 10.4 8.2zM18.2 13.6 19 16.6 22 17.4 19 18.2 18.2 21.2 17.4 18.2 14.4 17.4 17.4 16.6z"/>
  </svg>`,
  perplexity: `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M12 2 4 7v10l8 5 8-5V7l-8-5zm0 2.34L17.55 8 12 11.66 6.45 8 12 4.34zM6 9.7l5 3.3v6.7l-5-3.13V9.7zm12 0v6.87l-5 3.13V13l5-3.3z"/>
  </svg>`,
}

function providerLogo(key) {
  return providerLogos[key] || ''
}

// Favicon URL via Google's public favicon CDN — same trick we use on
// the Source Influence page. sz=64 keeps it sharp on retina.
function faviconFor(domain) {
  if (!domain) return ''
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`
}

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
    title: 'LLM Dashboard',
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

// Demand-side prompt examples — the typed search bar cycles through
// these one at a time; each becomes a row beneath with a category chip
// + animated trend bar.
const PROMPT_EXAMPLES = [
  { q: 'best ai analytics tool for small saas',     style: 'comparison', trend: 82 },
  { q: 'how to track llm visibility in 2026',       style: 'how-to',     trend: 64 },
  { q: 'fetchbot vs bluefish alternatives',         style: 'vs',         trend: 47 },
  { q: 'why does perplexity keep mentioning notion',style: 'question',   trend: 71 },
  { q: 'cheapest geo platform for an indie founder',style: 'local',      trend: 58 },
  { q: 'is there a free chatgpt visibility tracker',style: 'question',   trend: 76 },
]

const typedPrompt = ref('')
const visiblePromptRows = ref([])

let _promptCycleStop = null
function startPromptCycle() {
  if (_promptCycleStop) return
  let idx = 0
  let cancelled = false
  let timer = null
  const tickIn = (text, target, speed) => new Promise(resolve => {
    let i = target.length
    typedPrompt.value = text
    const t = setInterval(() => {
      if (cancelled) { clearInterval(t); resolve(); return }
      i--
      typedPrompt.value = target.slice(0, i)
      if (i <= 0) { clearInterval(t); resolve() }
    }, speed)
  })
  const typeIn = (target, speed) => new Promise(resolve => {
    let i = 0
    typedPrompt.value = ''
    const t = setInterval(() => {
      if (cancelled) { clearInterval(t); resolve(); return }
      i++
      typedPrompt.value = target.slice(0, i)
      if (i >= target.length) { clearInterval(t); resolve() }
    }, speed)
  })
  const wait = (ms) => new Promise(r => { timer = setTimeout(r, ms) })

  const loop = async () => {
    while (!cancelled) {
      const ex = PROMPT_EXAMPLES[idx]
      // Type into the search bar
      await typeIn(ex.q, 45)
      if (cancelled) break
      await wait(420)
      // Push a new row at the top, keep last 3
      const row = { ...ex, id: 'r-' + Date.now() + '-' + idx }
      visiblePromptRows.value = [row, ...visiblePromptRows.value].slice(0, 3)
      await wait(1500)
      if (cancelled) break
      // Backspace before the next prompt
      await tickIn(ex.q, ex.q, 18)
      if (cancelled) break
      await wait(120)
      idx = (idx + 1) % PROMPT_EXAMPLES.length
    }
  }
  loop()
  _promptCycleStop = () => { cancelled = true; if (timer) clearTimeout(timer) }
}

const sourceShares = [
  { provider: 'Claude',     segments: [{cls:'reddit',pct:18},{cls:'news',pct:14},{cls:'wiki',pct:38},{cls:'blog',pct:20},{cls:'own',pct:10}] },
  { provider: 'GPT-4',      segments: [{cls:'reddit',pct:12},{cls:'news',pct:24},{cls:'wiki',pct:30},{cls:'blog',pct:24},{cls:'own',pct:10}] },
  { provider: 'Gemini',     segments: [{cls:'reddit',pct:10},{cls:'news',pct:42},{cls:'wiki',pct:18},{cls:'blog',pct:22},{cls:'own',pct:8}] },
  { provider: 'Perplexity', segments: [{cls:'reddit',pct:38},{cls:'news',pct:16},{cls:'wiki',pct:12},{cls:'blog',pct:22},{cls:'own',pct:12}] },
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
  width: 100%;
  max-width: 100vw;
  overflow-x: clip;
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
.brand-name { font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 20px; color: #131718; letter-spacing: -0.02em; }
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
  color: var(--brand-accent, #ff6b35);
  background: rgba(255, 107, 53, 0.12);
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
  color: var(--brand-accent, #ff6b35);
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
  background: var(--brand-accent, #ff6b35);
  flex-shrink: 0;
}

/* Framer-style hero visualisation */
/* Shared dot + bar utilities (reused in feature mockups) */
.hero-viz-dot {
  width: 8px; height: 8px; border-radius: 9999px;
  flex-shrink: 0;
  background: #cbd5e1;
  display: inline-block;
}
.hero-viz-dot.is-anthropic  { background: #d97706; }
.hero-viz-dot.is-openai     { background: #10b981; }
.hero-viz-dot.is-google     { background: #4285f4; }
.hero-viz-dot.is-perplexity { background: #5b6cff; }
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

/* ─── Hero "probe" animation — Framer-style narrative ─── */
.probe {
  position: relative;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  padding: 20px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 30px 70px rgba(15, 23, 42, 0.12);
  overflow: hidden;
}
.probe::before {
  content: '';
  position: absolute; inset: -40%;
  background: radial-gradient(ellipse at top right, rgba(255, 107, 53, 0.10), transparent 60%);
  pointer-events: none;
}

/* Prompt typing bar */
.probe-prompt {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: linear-gradient(180deg, #fbfaf7 0%, #ffffff 100%);
  margin-bottom: 14px;
}
.probe-prompt-label {
  font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: #ff6b35;
  padding: 4px 8px; border-radius: 6px;
  background: rgba(255, 107, 53, 0.10);
  flex-shrink: 0;
}
.probe-prompt-text {
  font-size: 14px; color: #1f2937; font-weight: 500;
  display: inline-flex; align-items: center; min-width: 0;
}
.probe-typer {
  display: inline-block;
  white-space: nowrap; overflow: hidden;
  border-right: none;
  width: 0;
  animation: probe-type 7s steps(26) infinite;
}
.probe-caret {
  display: inline-block;
  width: 2px; height: 16px;
  background: #ff6b35;
  margin-left: 2px;
  animation: probe-blink 1s step-end infinite;
}
@keyframes probe-type {
  0%        { width: 0; }
  35%, 80%  { width: 26ch; }
  90%, 100% { width: 0; }
}
@keyframes probe-blink {
  50% { opacity: 0; }
}

/* 2x2 reply grid */
.probe-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 14px;
}
.probe-card {
  position: relative;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background: #fff;
  opacity: 0;
  transform: translateY(8px);
  animation: probe-card-in 0.55s cubic-bezier(0.16, 1, 0.3, 1) var(--d, 0s) forwards;
  overflow: hidden;
}
@keyframes probe-card-in {
  to { opacity: 1; transform: translateY(0); }
}
.probe-card::after {
  /* sweeping highlight that runs once when the card lands */
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(105deg, transparent 30%, rgba(255, 107, 53, 0.18) 50%, transparent 70%);
  transform: translateX(-100%);
  animation: probe-sweep 1.2s ease-out var(--d, 0s) forwards;
  pointer-events: none;
}
@keyframes probe-sweep {
  to { transform: translateX(100%); }
}

.probe-card-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
}
.probe-logo {
  width: 22px; height: 22px; border-radius: 6px;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  /* Brand mark uses currentColor; container provides the tinted bg. */
  color: #fff;
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.probe-logo svg {
  width: 14px; height: 14px;
  display: block;
}
.probe-card:hover .probe-logo { transform: scale(1.12) rotate(-3deg); }
.probe-logo.is-anthropic  { background: #d97706; color: #fff; }
.probe-logo.is-openai     { background: #0f1212; color: #fff; }
/* Gemini logo is a gradient — keep container white so the gradient shows. */
.probe-logo.is-google     { background: #ffffff; border: 1px solid rgba(15,23,42,0.08); }
.probe-logo.is-perplexity { background: #1fb8a8; color: #fff; }
.probe-name {
  font-size: 13px; font-weight: 600; color: #1f2937;
  flex: 1;
}
.probe-status {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 10.5px; font-weight: 600; color: #059669;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.probe-status-dot {
  width: 6px; height: 6px; border-radius: 9999px;
  background: #10b981;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5);
  animation: probe-pulse 1.8s ease-out infinite;
}
@keyframes probe-pulse {
  70%  { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.probe-stream {
  font-size: 12.5px; line-height: 1.5; color: #4b5563;
  margin-bottom: 8px;
}
.probe-mark {
  background: linear-gradient(120deg, rgba(255, 107, 53, 0.0) 0%, rgba(255, 107, 53, 0.30) 50%, rgba(255, 107, 53, 0.0) 100%);
  background-size: 220% 100%;
  background-position: 100% 0;
  color: #1f2937;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 4px;
  animation: probe-highlight 4s ease-in-out infinite;
}
@keyframes probe-highlight {
  0%, 30%   { background-position: 100% 0; box-shadow: 0 0 0 rgba(255, 107, 53, 0); }
  55%, 85%  { background-position: 0% 0;   box-shadow: 0 0 18px rgba(255, 107, 53, 0.35); }
  100%      { background-position: -100% 0; box-shadow: 0 0 0 rgba(255, 107, 53, 0); }
}

.probe-tags {
  display: flex; flex-wrap: wrap; gap: 4px;
}
.probe-tag {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 10.5px; font-weight: 600;
  padding: 2px 8px 2px 4px;
  border-radius: 9999px;
  background: rgba(15, 23, 42, 0.05);
  color: #4b5563;
  transition: background 0.2s ease, transform 0.2s ease;
}
.probe-tag:hover {
  background: rgba(15, 23, 42, 0.09);
  transform: translateY(-1px);
}
.probe-tag-fav {
  width: 14px; height: 14px; border-radius: 3px;
  background: #fff;
  object-fit: contain;
  flex-shrink: 0;
}

/* Footer score ring */
.probe-foot {
  display: flex; align-items: center; gap: 14px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
  background: linear-gradient(180deg, #fbfaf7 0%, #ffffff 100%);
}
.probe-ring {
  position: relative;
  width: 56px; height: 56px;
  flex-shrink: 0;
}
.probe-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.probe-ring-bg {
  fill: none; stroke: rgba(15, 23, 42, 0.08); stroke-width: 3;
}
.probe-ring-fg {
  fill: none;
  stroke: url(#probe-ring-grad);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-dasharray: 100;
  stroke-dashoffset: 100;
  filter: drop-shadow(0 0 6px rgba(255, 107, 53, 0.35));
  animation: probe-ring-fill 2s cubic-bezier(0.16, 1, 0.3, 1) 1.4s forwards;
}
@keyframes probe-ring-fill {
  /* End offset = 100 − target % (visibility). Keep in sync with
     probeMetrics.visibility.value in the script section. */
  to { stroke-dashoffset: 62; }  /* 100 − 38 = 62 */
}
.probe-ring-num {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; color: #1f2937;
  font-variant-numeric: tabular-nums;
}
.probe-ring-num i { font-style: normal; font-size: 10px; color: #6e6a65; margin-left: 1px; }
.probe-foot-copy { min-width: 0; }
.probe-foot-h { font-size: 13px; font-weight: 700; color: #1f2937; }
.probe-foot-sub { font-size: 11.5px; color: #6e6a65; margin-top: 2px; line-height: 1.4; }
.probe-delta {
  display: inline-block;
  margin-left: 4px;
  padding: 1px 7px;
  border-radius: 9999px;
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
  font-weight: 600; font-size: 10.5px;
}

/* ── Framer-style magnetic tilt on the four reply cards ─────────── */
.probe-card {
  transform-style: preserve-3d;
  transform: perspective(900px) rotateY(var(--tx, 0deg)) rotateX(var(--ty, 0deg));
  transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1),
              box-shadow 0.3s ease;
  will-change: transform;
}
.probe-card:hover {
  box-shadow: 0 12px 32px -16px rgba(15, 23, 42, 0.25),
              0 0 0 1px rgba(255, 107, 53, 0.18);
}

/* ── New: live stats strip under the footer ─────────────────────── */
.probe-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 10px;
}
.probe-stat {
  position: relative;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfaf7 100%);
  opacity: 0;
  transform: translateY(6px);
  animation: probe-stat-in 0.5s cubic-bezier(0.16, 1, 0.3, 1) var(--d, 0s) forwards;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.probe-stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px -10px rgba(15, 23, 42, 0.25);
}
@keyframes probe-stat-in {
  to { opacity: 1; transform: translateY(0); }
}
/* Subtle sheen sweep on entrance — same vocabulary as .probe-card. */
.probe-stat::after {
  content: "";
  position: absolute; inset: 0;
  background: linear-gradient(110deg,
    transparent 0%,
    rgba(255, 107, 53, 0.10) 45%,
    transparent 70%);
  transform: translateX(-100%);
  animation: probe-stat-sweep 1.4s cubic-bezier(0.16, 1, 0.3, 1) calc(var(--d, 0s) + 0.2s) forwards;
  pointer-events: none;
}
@keyframes probe-stat-sweep {
  to { transform: translateX(110%); }
}
.probe-stat-h {
  font-size: 10px; font-weight: 600;
  color: #6e6a65;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.probe-stat-h sub {
  font-size: 7.5px;
  vertical-align: baseline;
  position: relative; bottom: -1px;
  margin-left: 1px;
  letter-spacing: 0;
}
.probe-stat-v {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  margin: 2px 0 0;
  line-height: 1.1;
}
.probe-stat-d {
  display: inline-block;
  margin-top: 4px;
  padding: 1px 6px;
  border-radius: 9999px;
  font-size: 9.5px; font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.probe-stat-d.is-up {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}

@media (max-width: 720px) {
  .probe-grid { grid-template-columns: 1fr; }
  .probe-stats { grid-template-columns: repeat(2, 1fr); }
}
@media (prefers-reduced-motion: reduce) {
  .probe-typer { animation: none; width: auto; }
  .probe-caret { animation: none; opacity: 0.6; }
  .probe-card { opacity: 1; transform: none; animation: none; }
  .probe-card::after { display: none; }
  .probe-mark { animation: none; background-position: 0 0; }
  .probe-ring-fg { animation: none; stroke-dashoffset: 62; }
  .probe-status-dot { animation: none; }
  .probe-stat { opacity: 1; transform: none; animation: none; }
  .probe-stat::after { display: none; }
  .probe-card { transform: none; }
}

/* word-cycle transition (reused from the deleted features section) */
.word-cycle-enter-active, .word-cycle-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
  display: inline-block;
}
.word-cycle-enter-from { opacity: 0; transform: translateY(8px); }
.word-cycle-leave-to   { opacity: 0; transform: translateY(-8px); position: absolute; }
.hero-h {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
.price-big { font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 2.6rem; line-height: 1; }
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
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-weight: 400; font-size: clamp(1.6rem, 3vw, 2.2rem);
  margin-bottom: 10px;
}
.cta-inner p { font-size: 15px; color: #6e6a65; margin-bottom: 28px; }

/* ── Footer ── */
/* ── Footer ─────────────────────────────────────────────── */
.footer {
  padding: 80px 0 32px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: #faf6ef;
  color: #4a4540;
}
.footer-grid {
  display: grid;
  grid-template-columns: 1.4fr repeat(4, 1fr);
  gap: 48px 32px;
  padding-bottom: 56px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
@media (max-width: 980px) {
  .footer-grid { grid-template-columns: 1fr 1fr; gap: 40px 24px; }
  .footer-brand-col { grid-column: 1 / -1; }
}
@media (max-width: 600px) {
  .footer-grid { grid-template-columns: 1fr; }
}

.footer-brand-col { max-width: 320px; }
.footer-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 20px;
  color: #1f2937;
  margin-bottom: 14px;
}
.footer-logo { width: 32px; height: 32px; object-fit: contain; }
.footer-tagline {
  font-size: 13.5px;
  line-height: 1.65;
  color: #6e6a65;
  margin: 0 0 18px;
}

.footer-socials {
  display: flex;
  gap: 8px;
}
.footer-social {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #ffffff;
  color: #4a4540;
  transition: transform 0.15s ease-out, color 0.15s ease-out, border-color 0.15s ease-out, box-shadow 0.15s ease-out;
}
.footer-social:hover {
  color: var(--brand-accent, #ff6b35);
  border-color: var(--brand-accent, #ff6b35);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(255, 107, 53, 0.18);
}

.footer-col { display: flex; flex-direction: column; gap: 10px; }
.footer-col-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #1f2937;
  margin-bottom: 8px;
}
.footer-col a {
  font-size: 13.5px;
  color: #6e6a65;
  text-decoration: none;
  transition: color 0.12s ease;
}
.footer-col a:hover {
  color: var(--brand-accent, #ff6b35);
}

.footer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 28px;
}
.footer-copy {
  font-size: 12.5px;
  color: #a09a93;
}
.footer-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: #a09a93;
}
.footer-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.footer-meta-divider { color: #cbc5bd; }
.footer-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: #10b981;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.55);
  animation: footer-status-pulse 1.8s ease-out infinite;
}
@keyframes footer-status-pulse {
  70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

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
/* Landing page must never produce horizontal scroll. The .lp wrapper
   below uses overflow-x: clip, but a few browsers (and some descendant
   stacking contexts) still let intrinsic overflow leak up to the
   document. Lock it at the root while this page is in the DOM. */
html:has(.lp),
html:has(.lp) body,
html:has(.lp) #app {
  overflow-x: clip;
  max-width: 100vw;
}
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
  background: linear-gradient(110deg, #131718 0%, #131718 55%, var(--brand-accent, #ff6b35) 100%);
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
  background: radial-gradient(circle, var(--brand-accent, #ff6b35) 0%, rgba(255,107,53,0) 70%);
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
  color: var(--brand-accent, #ff6b35);
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

/* ── Why you need this ── */
.why {
  position: relative;
  padding: 100px 0 60px;
  background: linear-gradient(180deg, #ffffff 0%, #f7f9fc 100%);
}
.why-wrap { max-width: 1080px; }
.why-eyebrow {
  display: inline-block;
  font-size: 11.5px; font-weight: 700; letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #ff6b35;
  padding: 5px 12px;
  border-radius: 9999px;
  background: rgba(255, 107, 53, 0.10);
  margin-bottom: 22px;
}
.why-h {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-weight: 700;
  font-size: clamp(2.2rem, 4.5vw, 3.6rem);
  line-height: 1.1;
  letter-spacing: -0.025em;
  color: #0f172a;
  margin-bottom: 18px;
}
.why-h em {
  font-style: normal;
  font-weight: 700;
  color: #1f2937;
}
.why-h-pop {
  background: linear-gradient(120deg, #ff6b35 0%, #3b82f6 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.why-sub {
  max-width: 720px;
  font-size: 17px;
  line-height: 1.6;
  color: #475569;
  margin-bottom: 56px;
}
.why-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 22px;
  margin-bottom: 56px;
}
.why-card {
  position: relative;
  padding: 28px 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 16px 40px rgba(15, 23, 42, 0.05);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.why-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 107, 53, 0.35);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 24px 60px rgba(15, 23, 42, 0.10);
}
.why-card-num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 36px; height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #ff6b35 0%, #ff5722 100%);
  color: #fff;
  font-weight: 800;
  font-size: 15px;
  margin-bottom: 18px;
  box-shadow: 0 6px 16px rgba(255, 107, 53, 0.25);
}
.why-card-h {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 700;
  font-size: 20px;
  line-height: 1.25;
  color: #0f172a;
  margin-bottom: 10px;
}
.why-card-h em {
  font-style: normal;
  color: #ff6b35;
}
.why-card p {
  font-size: 14.5px;
  line-height: 1.55;
  color: #64748b;
  margin: 0;
}
.why-cta {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 18px;
  padding: 28px 32px;
  border-radius: 18px;
  background: linear-gradient(120deg, #0f172a 0%, #1e293b 100%);
  position: relative;
  overflow: hidden;
}
.why-cta::before {
  content: '';
  position: absolute; inset: -50% -10% auto auto;
  width: 60%; height: 200%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.35) 0%, transparent 65%);
  pointer-events: none;
}
.why-cta::after {
  content: '';
  position: absolute; inset: auto auto -40% -10%;
  width: 50%; height: 160%;
  background: radial-gradient(circle, rgba(255, 107, 53, 0.30) 0%, transparent 65%);
  pointer-events: none;
}
.why-cta-line {
  position: relative; z-index: 1;
  font-size: 18px;
  color: #e2e8f0;
  max-width: 580px;
  line-height: 1.4;
}
.why-cta-line strong {
  color: #fff;
  font-weight: 700;
}
.why-cta-btn {
  position: relative; z-index: 1;
  display: inline-flex; align-items: center; gap: 8px;
  padding: 13px 22px;
  border-radius: 9999px;
  background: #ff6b35;
  color: #ffffff;
  font-weight: 600;
  font-size: 14.5px;
  text-decoration: none;
  transition: background 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
  box-shadow: 0 8px 22px rgba(255, 107, 53, 0.35);
}
.why-cta-btn:hover {
  background: #ff5722;
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(255, 107, 53, 0.45);
}

@media (max-width: 880px) {
  .why-grid { grid-template-columns: 1fr; }
  .why { padding: 70px 0 40px; }
  .why-cta { flex-direction: column; align-items: flex-start; padding: 24px; }
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
  color: var(--brand-accent, #ff6b35);
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
  color: var(--brand-accent, #ff6b35);
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
  background: var(--brand-accent, #ff6b35);
  flex-shrink: 0;
  box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.12);
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
  color: var(--brand-accent, #ff6b35);
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
  background: rgba(255,107,53,0.14);
  color: #8a6d2a;
}
.mock-chip.is-comparison { background: rgba(74,127,176,0.14);  color: #345f86; }
.mock-chip.is-how-to     { background: rgba(110,165,110,0.16); color: #3f6b3f; }
.mock-chip.is-vs         { background: rgba(198,90,47,0.14);   color: #8a3d18; }
.mock-chip.is-question   { background: rgba(126,34,206,0.12);  color: #5b21b6; }
.mock-chip.is-local      { background: rgba(217,119,6,0.14);   color: #92400e; }
.mock-chip.is-story      { background: rgba(15,118,110,0.14);  color: #115e59; }

/* Cycler: rows fade in from the top, push older rows down. The
   transition-group + per-row absolute positioning would be over-
   engineered for 3 rows, so we use a simple opacity+translate. */
.mock-row-stagger-enter-active { transition: opacity .35s ease, transform .35s cubic-bezier(.16,1,.3,1); }
.mock-row-stagger-enter-from   { opacity: 0; transform: translateY(-6px); }
.mock-row-stagger-leave-active { transition: opacity .25s ease; }
.mock-row-stagger-leave-to     { opacity: 0; }
.mock-trend {
  height: 6px; border-radius: 4px;
  background: #ece6da;
  overflow: hidden;
}
.mock-trend-bar {
  width: 0; height: 100%;
  background: linear-gradient(90deg, var(--brand-accent, #ff6b35), #3b82f6);
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
.mock-mini-pct { color: var(--brand-accent, #ff6b35); font-weight: 600; }
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
.seg-own    { background: var(--brand-accent, #ff6b35); }
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
  background: rgba(59, 130, 246, 0.14);
  color: #1d4ed8;
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
  background: #e2e8f0;
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
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #1f2937;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  padding: 7px 14px;
  cursor: pointer;
  transition: all 0.18s ease;
}
.mock-btn:hover { background: #f1f5f9; }
.mock-btn.is-primary {
  background: #ff6b35;
  color: #fff;
  border-color: #ff6b35;
}
.mock-btn.is-primary:hover { background: #ff5722; }

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
  color: var(--brand-accent, #ff6b35);
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
  background: var(--brand-accent, #ff6b35);
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

/* ── Final CTA with video background ── */
.final-cta { position: relative; overflow: hidden; isolation: isolate; }
.final-cta-video {
  position: absolute;
  inset: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  z-index: 0;
  pointer-events: none;
}
.final-cta-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.55) 0%, rgba(15, 23, 42, 0.72) 100%),
    radial-gradient(ellipse at 50% 50%, rgba(255, 107, 53, 0.25) 0%, transparent 60%);
  z-index: 1;
  pointer-events: none;
}
.final-cta-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 50%, rgba(59, 130, 246, 0.18) 0%, transparent 60%);
  pointer-events: none;
  z-index: 2;
}
.final-cta .cta-inner { position: relative; z-index: 3; }
.final-cta h2 { font-size: 56px; color: #fff; }
.final-cta p { color: rgba(255, 255, 255, 0.85); }

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
