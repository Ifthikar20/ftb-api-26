<template>
  <div class="voice-onboarding">
    <div v-if="loading" class="voice-onboarding__loading">Loading setup status…</div>

    <template v-else>
      <div class="voice-onboarding__grid">
        <section
          v-for="segment in segmentList"
          :key="segment.key"
          class="voice-onboarding__card"
          :class="{ 'is-complete': segment.complete }"
        >
          <header class="voice-onboarding__card-header">
            <div>
              <h3>{{ segment.label }}</h3>
              <p>{{ segment.description }}</p>
            </div>
            <div class="voice-onboarding__progress">
              <div class="voice-onboarding__progress-bar">
                <div
                  class="voice-onboarding__progress-fill"
                  :style="{ width: segment.progress + '%' }"
                />
              </div>
              <span>{{ segment.progress }}%</span>
            </div>
          </header>

          <ol class="voice-onboarding__steps">
            <li
              v-for="step in segment.steps"
              :key="step.key"
              :class="{ done: step.done }"
            >
              <span class="voice-onboarding__step-icon">{{ step.done ? '✓' : '○' }}</span>
              <div class="voice-onboarding__step-body">
                <strong>{{ step.label }}</strong>
                <p>{{ step.description }}</p>
              </div>
              <button
                v-if="!step.done"
                class="btn btn-sm btn-secondary"
                @click="$emit('navigate', step.cta_url)"
              >
                Set up
              </button>
            </li>
          </ol>
        </section>
      </div>

      <section class="voice-onboarding__templates">
        <div class="voice-onboarding__templates-header">
          <h3>Starter templates</h3>
          <p>One-click knowledge-base files. Apply, then edit to match your business.</p>
        </div>
        <div class="voice-onboarding__template-grid">
          <article
            v-for="t in templates"
            :key="t.slug"
            class="voice-onboarding__template"
            :class="{ 'is-applied': appliedSlugs.has(t.slug) }"
          >
            <header>
              <h4>{{ t.title }}</h4>
              <span class="voice-onboarding__badge" :data-segment="t.segment">{{ segmentLabel(t.segment) }}</span>
            </header>
            <p>{{ t.description }}</p>
            <div class="voice-onboarding__template-actions">
              <button class="btn btn-sm btn-secondary" @click="preview(t)">Preview</button>
              <button
                class="btn btn-sm btn-primary"
                :disabled="applying === t.slug"
                @click="apply(t)"
              >
                {{ appliedSlugs.has(t.slug) ? 'Re-apply' : (applying === t.slug ? 'Applying…' : 'Apply') }}
              </button>
            </div>
          </article>
        </div>
      </section>

      <div v-if="previewing" class="voice-onboarding__modal" @click.self="previewing = null">
        <div class="voice-onboarding__modal-card">
          <header>
            <h3>{{ previewing.title }}</h3>
            <button class="voice-onboarding__close" @click="previewing = null">×</button>
          </header>
          <pre>{{ previewing.content }}</pre>
          <footer>
            <button class="btn btn-secondary btn-sm" @click="previewing = null">Close</button>
            <button class="btn btn-primary btn-sm" @click="apply(previewing); previewing = null">Apply this template</button>
          </footer>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import voiceAgent from '@/api/voiceAgent'

export default {
  name: 'VoiceOnboarding',
  props: {
    websiteId: { type: String, required: true },
  },
  emits: ['navigate', 'applied'],
  data() {
    return {
      loading: true,
      status: null,
      templates: [],
      previewing: null,
      applying: null,
      appliedSlugs: new Set(),
    }
  },
  computed: {
    segmentList() {
      if (!this.status) return []
      return [
        { key: 'inbound', ...this.status.inbound },
        { key: 'outbound', ...this.status.outbound },
      ]
    },
  },
  async mounted() {
    await this.refresh()
  },
  methods: {
    segmentLabel(seg) {
      if (seg === 'inbound') return 'Inbound'
      if (seg === 'outbound') return 'Outbound'
      return 'Both'
    },
    async refresh() {
      this.loading = true
      try {
        const [statusRes, templatesRes] = await Promise.all([
          voiceAgent.getSetupStatus(this.websiteId),
          voiceAgent.listTemplates(),
        ])
        this.status = statusRes.data?.data || statusRes.data
        this.templates = templatesRes.data?.data || templatesRes.data
        // Detect already-applied templates by matching titles in inbound steps + KB
        const appliedTitles = new Set()
        const intro = this.templates.find((t) => t.slug === 'introduction')
        const script = this.templates.find((t) => t.slug === 'outbound_sales_script')
        if (intro && this.status?.inbound?.steps?.find((s) => s.key === 'introduction_doc')?.done) {
          appliedTitles.add(intro.slug)
        }
        if (script && this.status?.outbound?.steps?.find((s) => s.key === 'sales_script')?.done) {
          appliedTitles.add(script.slug)
        }
        this.appliedSlugs = appliedTitles
      } catch (err) {
        console.error('voice onboarding load failed', err)
      } finally {
        this.loading = false
      }
    },
    async preview(t) {
      try {
        const res = await voiceAgent.previewTemplate(this.websiteId, t.slug)
        this.previewing = res.data?.data || res.data
      } catch (err) {
        console.error('preview failed', err)
      }
    },
    async apply(t) {
      this.applying = t.slug
      try {
        await voiceAgent.applyTemplate(this.websiteId, t.slug)
        this.appliedSlugs.add(t.slug)
        this.$emit('applied', t.slug)
        await this.refresh()
      } catch (err) {
        console.error('apply failed', err)
      } finally {
        this.applying = null
      }
    },
  },
}
</script>

<style scoped>
.voice-onboarding {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.voice-onboarding__loading {
  padding: 24px;
  color: var(--text-muted, #666);
}

.voice-onboarding__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}

.voice-onboarding__card {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.voice-onboarding__card.is-complete {
  border-color: #10b981;
}

.voice-onboarding__card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.voice-onboarding__card-header h3 {
  margin: 0 0 4px;
  font-size: 16px;
}

.voice-onboarding__card-header p {
  margin: 0;
  color: var(--text-muted, #6b7280);
  font-size: 13px;
  max-width: 28em;
}

.voice-onboarding__progress {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  min-width: 90px;
}

.voice-onboarding__progress-bar {
  width: 90px;
  height: 6px;
  background: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
}

.voice-onboarding__progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #10b981);
  transition: width 0.3s ease;
}

.voice-onboarding__steps {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.voice-onboarding__steps li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f9fafb;
}

.voice-onboarding__steps li.done {
  background: #ecfdf5;
}

.voice-onboarding__step-icon {
  font-weight: 700;
  width: 18px;
  text-align: center;
  color: #6b7280;
}

.voice-onboarding__steps li.done .voice-onboarding__step-icon {
  color: #10b981;
}

.voice-onboarding__step-body {
  flex: 1;
  font-size: 13px;
}

.voice-onboarding__step-body strong {
  display: block;
  margin-bottom: 2px;
}

.voice-onboarding__step-body p {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
}

.voice-onboarding__templates {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 12px;
  padding: 20px;
}

.voice-onboarding__templates-header h3 {
  margin: 0 0 4px;
  font-size: 16px;
}

.voice-onboarding__templates-header p {
  margin: 0 0 16px;
  color: #6b7280;
  font-size: 13px;
}

.voice-onboarding__template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.voice-onboarding__template {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fff;
}

.voice-onboarding__template.is-applied {
  border-color: #10b981;
}

.voice-onboarding__template header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.voice-onboarding__template h4 {
  margin: 0;
  font-size: 14px;
}

.voice-onboarding__template p {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
  flex: 1;
}

.voice-onboarding__badge {
  font-size: 10px;
  text-transform: uppercase;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
  background: #e0e7ff;
  color: #3730a3;
}

.voice-onboarding__badge[data-segment='inbound'] {
  background: #dbeafe;
  color: #1e40af;
}

.voice-onboarding__badge[data-segment='outbound'] {
  background: #fef3c7;
  color: #92400e;
}

.voice-onboarding__template-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.voice-onboarding__modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.voice-onboarding__modal-card {
  background: #fff;
  border-radius: 12px;
  width: min(720px, 92vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.voice-onboarding__modal-card header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.voice-onboarding__modal-card h3 {
  margin: 0;
  font-size: 16px;
}

.voice-onboarding__close {
  background: none;
  border: none;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
}

.voice-onboarding__modal-card pre {
  margin: 0;
  padding: 20px;
  flex: 1;
  overflow: auto;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  background: #f9fafb;
}

.voice-onboarding__modal-card footer {
  padding: 12px 20px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
