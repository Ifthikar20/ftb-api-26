<template>
  <div class="legal-page">
    <header class="legal-header">
      <router-link to="/" class="legal-logo">
        <img src="/images/fb-logo.png" alt="FetchBot" width="28" height="28" />
        <span>FetchBot</span>
      </router-link>
      <div class="legal-nav">
        <router-link to="/terms">Terms of Service</router-link>
        <router-link to="/login" class="btn btn-sm btn-primary">Sign In</router-link>
      </div>
    </header>

    <main class="legal-content">
      <div class="legal-meta">
        <span class="legal-badge">Legal</span>
        <span class="legal-date">Effective Date: May 17, 2026</span>
      </div>

      <h1>Privacy Policy</h1>
      <p class="legal-intro">
        FetchBot Inc. ("FetchBot", "we", "us", or "our") respects your privacy. This Privacy
        Policy explains how we collect, use, and protect your information when you use our
        website, dashboard, applications, and APIs (the "Services").
      </p>
      <p class="legal-intro">
        This Policy applies to all FetchBot surfaces, including the fetchbot.ai marketing site,
        the dashboard at fetchbot.ai/app, the api.fetchbot.ai API, the FetchBot analytics pixel
        embedded on customer websites, and any third-party integrations you connect to your
        FetchBot workspace (Google Analytics, Google Search Console, WordPress, Webflow,
        Shopify, HubSpot, Slack, Discord, and Telegram).
      </p>
      <p class="legal-intro">
        By using FetchBot, you agree to the practices described in this Privacy Policy.
      </p>

      <div class="legal-toc">
        <h3>Table of Contents</h3>
        <ol>
          <li><a href="#info-collected">Information We Collect</a></li>
          <li><a href="#how-we-use">How We Use Information</a></li>
          <li><a href="#sharing">Sharing of Information</a></li>
          <li><a href="#subprocessors">Service Providers and Subprocessors</a></li>
          <li><a href="#ai-usage">AI Usage and LLM Providers</a></li>
          <li><a href="#pixel">The FetchBot Analytics Pixel</a></li>
          <li><a href="#retention">Data Retention</a></li>
          <li><a href="#security">Security</a></li>
          <li><a href="#rights">Your Rights</a></li>
          <li><a href="#cookies">Cookies and Tracking</a></li>
          <li><a href="#international">International Data Transfers</a></li>
          <li><a href="#children">Children's Privacy</a></li>
          <li><a href="#changes">Changes to This Policy</a></li>
          <li><a href="#contact">Contact</a></li>
        </ol>
      </div>

      <section id="info-collected">
        <h2>1. Information We Collect</h2>

        <h3>(a) Information You Provide</h3>
        <ul>
          <li>Account details (name, email address, password, company name).</li>
          <li>Billing information collected by our payment processor (Stripe).</li>
          <li>The URL of the website you want to analyze and any descriptive content you submit during onboarding (business name, industry, description, topics, competitor list).</li>
          <li>Communications you send to us (support requests, bug reports, feedback).</li>
        </ul>

        <h3>(b) Automatically Collected Information</h3>
        <ul>
          <li>Device information (operating system, browser, IP address, approximate region derived from IP).</li>
          <li>Usage data (pages visited, features accessed, clicks, API requests).</li>
          <li>Log data and error reports captured for security, debugging, and reliability.</li>
        </ul>

        <h3>(c) Website Content We Analyze on Your Request</h3>
        <p>
          When you onboard a website, we fetch its publicly accessible pages and supply
          excerpts to the LLM providers listed in Section 4 so we can describe the site,
          extract competitors, and run audits. We do not log into private areas of your
          site or bypass authentication. We may periodically refresh this content while
          your subscription is active.
        </p>

        <h3>(d) AI-Generated Content</h3>
        <p>
          When you request AI-assisted features (Content Studio briefs, LLM ranking audits,
          competitor extraction, prompt generation), we send the relevant inputs to one or
          more LLM providers and return their outputs to you. Inputs and outputs are stored
          in your account so you can review historical audits.
        </p>
      </section>

      <section id="how-we-use">
        <h2>2. How We Use Information</h2>
        <ul>
          <li>Operate, secure, and improve the Services.</li>
          <li>Run LLM-visibility audits on your behalf and surface the results in your dashboard.</li>
          <li>Generate content drafts, prompts, and competitor lists at your request.</li>
          <li>Collect website analytics on your behalf through the FetchBot pixel (see Section 6).</li>
          <li>Process payments, manage your subscription, and detect fraud.</li>
          <li>Send transactional email (email verification, password reset, security alerts, billing notices).</li>
          <li>Send service email you have opted into (weekly reports, product announcements). Every such email contains a one-click unsubscribe link.</li>
          <li>Comply with legal obligations and enforce our Terms of Service.</li>
        </ul>
        <p><strong>We do not sell your personal information.</strong></p>
      </section>

      <section id="sharing">
        <h2>3. Sharing of Information</h2>
        <p>We share information only as described below:</p>
        <ul>
          <li><strong>Service providers and subprocessors</strong> that operate the platform on our behalf (listed in Section 4). Each receives only the data necessary for its function and is contractually required to process it on our behalf in accordance with applicable law.</li>
          <li><strong>Third-party integrations you choose to connect</strong> (e.g., Google Analytics, Search Console, WordPress, Webflow, Shopify, HubSpot, Slack, Discord, Telegram). Data flows are governed by each provider's own terms.</li>
          <li><strong>Legal disclosures</strong> when required by law, court order, or to protect our rights, users, or the public.</li>
          <li><strong>Corporate transactions</strong>: if FetchBot is involved in a merger, acquisition, or asset sale, your information may be transferred subject to this Policy.</li>
        </ul>
        <p>
          We do not share LLM audit data, content briefs, brand vault data, or website
          analytics with advertisers or data brokers.
        </p>
      </section>

      <section id="subprocessors">
        <h2>4. Service Providers and Subprocessors</h2>
        <p>
          We rely on the following categories of third-party providers to deliver the
          Services. Each provider receives only the data necessary for its function and is
          contractually required to process it on our behalf.
        </p>
        <ul>
          <li><strong>Hosting and infrastructure</strong>: Amazon Web Services (EC2 compute, S3 object storage), Cloudflare (CDN, DDoS protection, edge TLS).</li>
          <li><strong>Database and queue</strong>: self-managed PostgreSQL and Redis running on AWS.</li>
          <li><strong>LLM providers</strong>: Anthropic (Claude), OpenAI (GPT), Google (Gemini), Perplexity, Meta (Llama), Mistral AI, Cohere, DeepSeek, xAI (Grok), and Amazon (Nova via Bedrock). Each provider receives only the inputs required for the requested audit or content generation. See Section 5.</li>
          <li><strong>Payments</strong>: Stripe (subscription billing and payment method storage). FetchBot never stores full card numbers.</li>
          <li><strong>Email delivery</strong>: Amazon Simple Email Service (SES) for transactional and service email.</li>
          <li><strong>Error monitoring</strong>: Sentry, used only when SENTRY_DSN is configured in production, to correlate client and server errors.</li>
        </ul>
        <p>
          We may add or change subprocessors as the Services evolve. A current list is
          available on request by emailing
          <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a>.
        </p>
      </section>

      <section id="ai-usage">
        <h2>5. AI Usage and LLM Providers</h2>
        <p>
          FetchBot's core feature is querying large language models on your behalf to
          measure how your brand appears in their responses. To do this we send prompts
          containing your business name, industry, topics, and competitor list to the LLM
          providers listed in Section 4. The responses we receive may contain mentions of
          your brand, competitors, and third-party content that we then parse and store in
          your account.
        </p>
        <ul>
          <li>LLM provider APIs we call are governed by each provider's privacy and data-processing terms in addition to this Policy.</li>
          <li>We use API endpoints that, per each provider's published terms, do not use your inputs to train their models. We do not opt in to any provider's training programs.</li>
          <li>AI-generated outputs may be inaccurate or out of date. You are responsible for reviewing AI-generated content before publishing it or relying on it for decisions.</li>
          <li>We may use anonymized or aggregated usage data internally to improve prompts, ranking algorithms, and quality.</li>
        </ul>
      </section>

      <section id="pixel">
        <h2>6. The FetchBot Analytics Pixel</h2>
        <p>
          When you install our analytics pixel on a website you own, we collect anonymized
          visitor analytics for that site on your behalf:
        </p>
        <ul>
          <li>Visitor IP addresses (hashed before storage), browser user-agent strings, referrer URLs, and event timestamps.</li>
          <li>Page-view and click events fired by the pixel script.</li>
          <li>UTM and campaign parameters present on the inbound URL.</li>
        </ul>
        <p>
          For pixel data, you (the website operator) are the controller and FetchBot is the
          processor. You are responsible for obtaining the consents required by applicable
          law (e.g., GDPR / ePrivacy in the EU, the UK PECR, and CCPA / CPRA in California)
          before activating the pixel on your site, and for surfacing this collection in
          your own privacy policy. A Data Processing Addendum is available on request.
        </p>
      </section>

      <section id="retention">
        <h2>7. Data Retention</h2>
        <ul>
          <li><strong>Active accounts</strong>: we retain account data, audit history, and dashboards for as long as your account is active.</li>
          <li><strong>Account deletion</strong>: you may delete your account at any time. We remove your personal data from our active systems within 30 days. Some data may be retained longer where required by law (e.g., tax records for billing) or for fraud prevention and dispute resolution.</li>
          <li><strong>Server logs</strong>: typically retained for 90 days.</li>
          <li><strong>Backups</strong>: encrypted database backups roll off on a 30-day cycle.</li>
        </ul>
      </section>

      <section id="security">
        <h2>8. Security</h2>
        <p>
          We use reasonable administrative, technical, and physical safeguards to protect
          your information:
        </p>
        <ul>
          <li>TLS 1.2+ for all traffic, enforced by HSTS preload.</li>
          <li>Passwords stored only as salted hashes (Django's default hasher; never plaintext).</li>
          <li>JWT-based session tokens; refresh tokens are HTTP-only cookies blacklisted on logout.</li>
          <li>Brute-force protection on authentication endpoints via rate limiting and account lockout (django-axes).</li>
          <li>Principle-of-least-privilege access to production systems; access is logged and audited.</li>
          <li>Documented incident response. We notify affected users and regulators within 72 hours of confirming a personal-data breach where required by law (GDPR Art. 33).</li>
        </ul>
        <p>
          To report a security issue, email
          <a href="mailto:security@fetchbot.ai">security@fetchbot.ai</a>. We investigate every
          report in good faith and ask that you give us a reasonable opportunity to remediate
          before public disclosure.
        </p>
      </section>

      <section id="rights">
        <h2>9. Your Rights</h2>

        <h3>(a) General Rights</h3>
        <ul>
          <li>Access, edit, or delete your account information from your account settings.</li>
          <li>Export your audit history and dashboard data on request.</li>
          <li>Opt out of non-essential email at any time using the unsubscribe link in any such message or by emailing <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a>.</li>
          <li>Delete your account; your personal data is removed from active systems within 30 days.</li>
        </ul>

        <h3>(b) Rights Under GDPR (EU / EEA / UK Users)</h3>
        <p>If you are located in the European Union, the European Economic Area, or the United Kingdom, you have the following rights:</p>
        <ul>
          <li>Right to access the personal data we hold about you.</li>
          <li>Right to request correction of inaccurate data.</li>
          <li>Right to request erasure of your data.</li>
          <li>Right to restrict or object to processing.</li>
          <li>Right to data portability (export in a structured, machine-readable format).</li>
          <li>Right to withdraw consent where processing is based on consent.</li>
          <li>Right to lodge a complaint with your local supervisory authority.</li>
        </ul>
        <p>To exercise these rights, email <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a>.</p>

        <h3>(c) Rights Under CCPA / CPRA (California Residents)</h3>
        <p>If you are a California resident, you have the following rights under the California Consumer Privacy Act, as amended by the California Privacy Rights Act:</p>
        <ul>
          <li>Right to know what categories of personal information we collect, the sources of that information, the purposes for which we use it, and the categories of third parties we share it with (described in Sections 1 through 5).</li>
          <li>Right to access a copy of the personal information we hold about you.</li>
          <li>Right to request deletion or correction of your personal information.</li>
          <li>Right to limit the use and disclosure of sensitive personal information.</li>
          <li>Right to opt out of the "sale" or "sharing" of personal information. We do not sell personal information and do not share it for cross-context behavioral advertising.</li>
          <li>Right to non-discrimination for exercising any of these rights.</li>
        </ul>
        <p>To exercise these rights, email <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a> with the subject line "CCPA Request". We verify requests using account-based authentication and respond within the timeframes required by law.</p>
      </section>

      <section id="cookies">
        <h2>10. Cookies and Tracking</h2>
        <p>FetchBot uses cookies and similar technologies to operate the Services and understand how they are used:</p>
        <ul>
          <li><strong>Strictly necessary</strong>: session cookies that keep you signed in (HTTP-only refresh-token cookie), CSRF-protection tokens, and load-balancing cookies set by Cloudflare. These cannot be disabled without breaking the Services.</li>
          <li><strong>Functional</strong>: cookies that remember workspace preferences (active website, theme).</li>
          <li><strong>Error monitoring</strong>: Sentry may set short-lived identifiers to correlate client errors with backend logs.</li>
        </ul>
        <p>
          We do not use third-party advertising cookies and do not participate in
          cross-context behavioral advertising networks. Most browsers let you block or
          delete cookies; doing so may affect FetchBot's functionality.
        </p>
      </section>

      <section id="international">
        <h2>11. International Data Transfers</h2>
        <p>
          FetchBot is operated from the United States. If you access the Services from
          outside the United States, your information will be transferred to and processed
          in the United States. Where required by law (e.g., transfers out of the EEA or
          UK), we rely on Standard Contractual Clauses or other lawful transfer mechanisms
          with our subprocessors.
        </p>
      </section>

      <section id="children">
        <h2>12. Children's Privacy</h2>
        <p>
          FetchBot is a B2B product not directed to children under 13 (or under 16 in the
          EU / EEA / UK), and we do not knowingly collect personal information from such
          children. If you believe we have collected information from a child below the
          applicable age, please email
          <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a> and we will delete it
          promptly.
        </p>
      </section>

      <section id="changes">
        <h2>13. Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. When we do, we will update
          the "Effective Date" at the top and, for material changes, notify you by email
          or an in-app notice before the changes take effect.
        </p>
      </section>

      <section id="contact">
        <h2>14. Contact</h2>
        <p>
          If you have questions about this Privacy Policy or our data practices, contact
          us at <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a>. For security
          issues, email <a href="mailto:security@fetchbot.ai">security@fetchbot.ai</a>.
        </p>
        <p>
          FetchBot Inc.
        </p>
      </section>
    </main>

    <footer class="legal-footer">
      <p>&copy; 2026 FetchBot Inc. All rights reserved.</p>
      <div class="legal-footer-links">
        <router-link to="/terms">Terms of Service</router-link>
        <router-link to="/privacy">Privacy Policy</router-link>
        <a href="mailto:support@fetchbot.ai">Contact</a>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  document.title = 'Privacy Policy — FetchBot'
})
</script>

<style scoped>
.legal-page {
  min-height: 100vh;
  background: var(--bg-body, #fafafa);
  color: var(--text-primary, #1a1a2e);
}

.legal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 40px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-card, #fff);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(12px);
}

.legal-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text-primary);
  text-decoration: none;
}

.legal-nav {
  display: flex;
  align-items: center;
  gap: 20px;
}
.legal-nav a {
  font-size: var(--font-sm, 0.875rem);
  color: var(--text-secondary, #6b7280);
  text-decoration: none;
  font-weight: 500;
}
.legal-nav a:hover { color: var(--text-primary); }
.legal-nav .btn { padding: 8px 18px; border-radius: 8px; font-size: 0.8rem; }

.legal-content {
  max-width: 780px;
  margin: 0 auto;
  padding: 48px 24px 80px;
  line-height: 1.8;
}

.legal-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.legal-badge {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #8b5cf6;
  background: rgba(139, 92, 246, 0.08);
  padding: 4px 10px;
  border-radius: 6px;
}

.legal-date {
  font-size: var(--font-sm, 0.875rem);
  color: var(--text-muted, #9ca3af);
}

h1 {
  font-size: 2.2rem;
  font-weight: 800;
  margin-bottom: 16px;
  letter-spacing: -0.02em;
}

.legal-intro {
  font-size: 1.05rem;
  color: var(--text-secondary, #4b5563);
  margin-bottom: 12px;
}

.legal-toc {
  background: var(--bg-surface, #f3f4f6);
  border-radius: 12px;
  padding: 24px 28px;
  margin: 32px 0;
}
.legal-toc h3 {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 12px;
}
.legal-toc ol {
  padding-left: 20px;
  columns: 2;
  column-gap: 24px;
}
.legal-toc li {
  padding: 3px 0;
  font-size: var(--font-sm, 0.875rem);
  break-inside: avoid;
}
.legal-toc a {
  color: var(--text-secondary);
  text-decoration: none;
}
.legal-toc a:hover {
  color: #8b5cf6;
  text-decoration: underline;
}

section { margin-top: 40px; }

h2 {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}

h3 {
  font-size: 1rem;
  font-weight: 600;
  margin: 20px 0 8px;
  color: var(--text-primary);
}

p {
  margin-bottom: 12px;
  color: var(--text-secondary, #4b5563);
}

ul, ol {
  padding-left: 24px;
  margin-bottom: 16px;
}

li {
  margin-bottom: 6px;
  color: var(--text-secondary, #4b5563);
}

a {
  color: #8b5cf6;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.legal-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: var(--font-sm, 0.875rem);
}
.legal-table th {
  background: var(--bg-surface, #f3f4f6);
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-color, #e5e7eb);
}
.legal-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  color: var(--text-secondary);
}
.legal-table tr:last-child td { border-bottom: none; }

.contact-card {
  background: var(--bg-surface, #f3f4f6);
  border-radius: 12px;
  padding: 20px 24px;
  margin-top: 12px;
}
.contact-card p { margin-bottom: 4px; }

.legal-footer {
  border-top: 1px solid var(--border-color, #e5e7eb);
  padding: 24px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-sm, 0.875rem);
  color: var(--text-muted, #9ca3af);
}
.legal-footer-links {
  display: flex;
  gap: 20px;
}
.legal-footer-links a {
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 500;
}
.legal-footer-links a:hover { color: var(--text-primary); }

@media (max-width: 640px) {
  .legal-header { padding: 12px 16px; }
  .legal-content { padding: 32px 16px 60px; }
  h1 { font-size: 1.6rem; }
  .legal-toc ol { columns: 1; }
  .legal-footer { flex-direction: column; gap: 12px; text-align: center; }
}
</style>
