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
        <span class="legal-date">Last updated: March 26, 2026</span>
      </div>

      <h1>Privacy Policy</h1>
      <p class="legal-intro">
        FetchBot Inc. ("FetchBot", "Company", "we", "us", or "our") is committed to protecting your
        privacy. This Privacy Policy describes how we collect, use, disclose, and safeguard your
        information when you use the FetchBot platform, website, and APIs (the "Service").
      </p>
      <p class="legal-intro">
        By using the Service, you consent to the data practices described in this Privacy Policy.
        If you do not agree to the terms of this Privacy Policy, please do not access or use the Service.
      </p>

      <div class="legal-toc">
        <h3>Table of Contents</h3>
        <ol>
          <li><a href="#info-collected">Information We Collect</a></li>
          <li><a href="#how-we-use">How We Use Your Information</a></li>
          <li><a href="#legal-basis">Legal Basis for Processing (GDPR)</a></li>
          <li><a href="#data-sharing">Data Sharing & Disclosure</a></li>
          <li><a href="#data-retention">Data Retention</a></li>
          <li><a href="#data-security">Data Security</a></li>
          <li><a href="#cookies">Cookies & Tracking Technologies</a></li>
          <li><a href="#analytics">Website Analytics & Tracking Scripts</a></li>
          <li><a href="#ai-data">AI & Machine Learning</a></li>
          <li><a href="#third-party">Third-Party Services</a></li>
          <li><a href="#your-rights">Your Rights</a></li>
          <li><a href="#international">International Data Transfers</a></li>
          <li><a href="#children">Children's Privacy</a></li>
          <li><a href="#california">California Privacy Rights (CCPA)</a></li>
          <li><a href="#changes">Changes to This Policy</a></li>
          <li><a href="#contact">Contact Us</a></li>
        </ol>
      </div>

      <!-- ── 1. Information We Collect ── -->
      <section id="info-collected">
        <h2>1. Information We Collect</h2>

        <h3>1.1 Information You Provide</h3>
        <ul>
          <li><strong>Account Information</strong> — Full name, email address, and password when you register.</li>
          <li><strong>Profile Information</strong> — Company name, job title, profile picture, and timezone preferences.</li>
          <li><strong>Payment Information</strong> — Billing details processed through Stripe. We never store credit card numbers on our servers.</li>
          <li><strong>Support Communications</strong> — Content of emails, support tickets, and feedback you send us.</li>
          <li><strong>Website Configuration</strong> — Domain names, tracking snippet placement, and project settings you configure.</li>
        </ul>

        <h3>1.2 Information Collected Automatically</h3>
        <ul>
          <li><strong>Usage Data</strong> — Pages visited within FetchBot, features used, buttons clicked, and session duration.</li>
          <li><strong>Device Information</strong> — Browser type, operating system, device type, screen resolution, and language preferences.</li>
          <li><strong>Network Information</strong> — IP address, approximate geographic location (city-level), referring URL, and ISP.</li>
          <li><strong>Log Data</strong> — Server logs including timestamps, API endpoints accessed, request/response metadata, and error logs.</li>
        </ul>

        <h3>1.3 Information Collected on Your Behalf</h3>
        <p>When you install the FetchBot analytics tracking script on your website, we collect data about your website visitors on your behalf. This includes:</p>
        <ul>
          <li>Page views, sessions, and navigation paths</li>
          <li>Referral sources and UTM parameters</li>
          <li>Device and browser information</li>
          <li>IP addresses (anonymized for EU visitors)</li>
          <li>Interaction events (clicks, form submissions, scroll depth)</li>
        </ul>
        <p><strong>Important:</strong> You are the data controller for your website visitors' data. You are responsible for ensuring you have appropriate consent mechanisms (cookie banners, privacy policies) on your own website.</p>
      </section>

      <!-- ── 2. How We Use Your Information ── -->
      <section id="how-we-use">
        <h2>2. How We Use Your Information</h2>
        <p>We use the information we collect for the following purposes:</p>
        <ul>
          <li><strong>Providing the Service</strong> — To operate, maintain, and deliver the features and functionality of FetchBot.</li>
          <li><strong>Analytics & Insights</strong> — To generate reports, dashboards, lead scores, and AI-powered recommendations for your account.</li>
          <li><strong>Communication</strong> — To send you account notifications, security alerts, billing receipts, and product updates.</li>
          <li><strong>Customer Support</strong> — To respond to inquiries, troubleshoot issues, and provide technical assistance.</li>
          <li><strong>Improvement</strong> — To understand usage patterns, improve our algorithms, and develop new features.</li>
          <li><strong>Security</strong> — To detect, prevent, and address fraud, abuse, and security threats.</li>
          <li><strong>Compliance</strong> — To comply with legal obligations, enforce our Terms of Service, and protect our legal rights.</li>
          <li><strong>Billing</strong> — To process payments, manage subscriptions, and enforce usage limits.</li>
        </ul>
        <p>We do NOT use your data for:</p>
        <ul>
          <li>Selling personal information to third parties</li>
          <li>Targeted advertising or ad network profiling</li>
          <li>Building consumer profiles for resale or marketing purposes</li>
        </ul>
      </section>

      <!-- ── 3. Legal Basis (GDPR) ── -->
      <section id="legal-basis">
        <h2>3. Legal Basis for Processing (GDPR)</h2>
        <p>For users in the European Economic Area (EEA), United Kingdom, and Switzerland, we process your personal data under the following legal bases:</p>
        <table class="legal-table">
          <thead>
            <tr><th>Purpose</th><th>Legal Basis</th></tr>
          </thead>
          <tbody>
            <tr><td>Account management & service delivery</td><td>Contract performance</td></tr>
            <tr><td>Payment processing</td><td>Contract performance</td></tr>
            <tr><td>Security monitoring & fraud prevention</td><td>Legitimate interest</td></tr>
            <tr><td>Service improvement & analytics</td><td>Legitimate interest</td></tr>
            <tr><td>Email communications</td><td>Consent / legitimate interest</td></tr>
            <tr><td>Legal compliance & audit logging</td><td>Legal obligation</td></tr>
            <tr><td>AI model training (aggregated data only)</td><td>Legitimate interest</td></tr>
          </tbody>
        </table>
      </section>

      <!-- ── 4. Data Sharing ── -->
      <section id="data-sharing">
        <h2>4. Data Sharing & Disclosure</h2>
        <p>We do not sell your personal information. We share data only in the following limited circumstances:</p>
        <ul>
          <li><strong>Service Providers</strong> — Trusted third parties who assist us in operating the Service (hosting, payment processing, email delivery). These providers are contractually obligated to protect your data.</li>
          <li><strong>Integrations</strong> — When you connect Slack, Discord, Telegram, or other platforms, we share configured notification data with those services at your direction.</li>
          <li><strong>Legal Requirements</strong> — When required by law, subpoena, court order, or governmental regulation.</li>
          <li><strong>Business Transfers</strong> — In connection with a merger, acquisition, bankruptcy, or sale of assets, your data may be transferred. We will notify you before your data is transferred and becomes subject to a different privacy policy.</li>
          <li><strong>Safety</strong> — When we believe disclosure is necessary to protect the safety of our users, the public, or FetchBot.</li>
        </ul>

        <h3>Key Service Providers</h3>
        <table class="legal-table">
          <thead>
            <tr><th>Provider</th><th>Purpose</th><th>Data Shared</th></tr>
          </thead>
          <tbody>
            <tr><td>Stripe</td><td>Payment processing</td><td>Billing details, transaction history</td></tr>
            <tr><td>AWS / Cloud Provider</td><td>Infrastructure hosting</td><td>All service data (encrypted at rest)</td></tr>
            <tr><td>SendGrid / Resend</td><td>Transactional email</td><td>Email address, name</td></tr>
            <tr><td>Sentry</td><td>Error monitoring</td><td>Error context (no PII)</td></tr>
          </tbody>
        </table>
      </section>

      <!-- ── 5. Data Retention ── -->
      <section id="data-retention">
        <h2>5. Data Retention</h2>
        <table class="legal-table">
          <thead>
            <tr><th>Data Type</th><th>Retention Period</th></tr>
          </thead>
          <tbody>
            <tr><td>Account information</td><td>Duration of account + 30 days</td></tr>
            <tr><td>Website analytics data</td><td>24 months, then auto-archived</td></tr>
            <tr><td>Lead & pipeline data</td><td>Duration of account + 30 days</td></tr>
            <tr><td>Audit logs</td><td>24 months (compliance requirement)</td></tr>
            <tr><td>Payment records</td><td>7 years (tax & legal requirement)</td></tr>
            <tr><td>Support communications</td><td>36 months</td></tr>
            <tr><td>Aggregated analytics</td><td>Indefinitely (non-identifiable)</td></tr>
          </tbody>
        </table>
        <p>You can request data deletion at any time by contacting <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a> or through your account settings.</p>
      </section>

      <!-- ── 6. Data Security ── -->
      <section id="data-security">
        <h2>6. Data Security</h2>
        <p>We implement industry-standard security measures to protect your data:</p>
        <ul>
          <li><strong>Encryption in Transit</strong> — All data transmitted between your browser and our servers is encrypted using TLS 1.3.</li>
          <li><strong>Encryption at Rest</strong> — All stored data is encrypted using AES-256 encryption.</li>
          <li><strong>Access Controls</strong> — Role-based access control (RBAC) ensures employees access only the data necessary for their role.</li>
          <li><strong>Audit Logging</strong> — All access to user data is logged with timestamp, user identity, action performed, and IP address. Logs are retained for 24 months.</li>
          <li><strong>Vulnerability Management</strong> — Regular security assessments, penetration testing, and dependency scanning.</li>
          <li><strong>Incident Response</strong> — Documented incident response procedures with notification within 72 hours of a confirmed breach (per GDPR requirements).</li>
          <li><strong>Password Security</strong> — Passwords are hashed using Argon2 with salting. We never store passwords in plaintext.</li>
          <li><strong>2FA Support</strong> — Two-factor authentication is available and recommended for all accounts.</li>
        </ul>
      </section>

      <!-- ── 7. Cookies ── -->
      <section id="cookies">
        <h2>7. Cookies & Tracking Technologies</h2>
        <h3>7.1 Cookies Used by FetchBot (the App)</h3>
        <table class="legal-table">
          <thead>
            <tr><th>Cookie</th><th>Type</th><th>Purpose</th><th>Duration</th></tr>
          </thead>
          <tbody>
            <tr><td>fb-session</td><td>Essential</td><td>Maintains login session</td><td>Session</td></tr>
            <tr><td>fb-refresh</td><td>Essential</td><td>JWT refresh token</td><td>7 days</td></tr>
            <tr><td>fb-theme</td><td>Preference</td><td>Dark/light mode preference</td><td>1 year</td></tr>
            <tr><td>fb-consent</td><td>Essential</td><td>Records cookie consent choice</td><td>1 year</td></tr>
          </tbody>
        </table>

        <h3>7.2 Your Tracking Script</h3>
        <p>The FetchBot analytics tracking script you install on your website uses a first-party cookie to identify unique sessions. It does NOT use third-party cookies, fingerprinting, or cross-site tracking.</p>
      </section>

      <!-- ── 8. Analytics & Tracking Scripts ── -->
      <section id="analytics">
        <h2>8. Website Analytics & Tracking Scripts</h2>
        <p>When you deploy the FetchBot tracking script on your website:</p>
        <ul>
          <li>You act as the <strong>Data Controller</strong> for your website visitors' data.</li>
          <li>FetchBot acts as a <strong>Data Processor</strong> processing data on your behalf.</li>
          <li>You are responsible for obtaining appropriate consent from your website visitors before deploying tracking scripts.</li>
          <li>We provide tools to anonymize IP addresses and respect Do Not Track (DNT) headers.</li>
          <li>We offer a Data Processing Agreement (DPA) for Enterprise customers upon request.</li>
        </ul>
      </section>

      <!-- ── 9. AI & Machine Learning ── -->
      <section id="ai-data">
        <h2>9. AI & Machine Learning</h2>
        <p>FetchBot uses AI to provide marketing intelligence, strategy recommendations, and trend analysis. Regarding your data and AI:</p>
        <ul>
          <li>Your account data is used to generate personalized insights <strong>only within your account</strong>.</li>
          <li>We do NOT use your individual data to train AI models for other users.</li>
          <li>We may use <strong>anonymized, aggregated data</strong> (which cannot identify you, your company, or your users) to improve our AI models and algorithms.</li>
          <li>AI-generated outputs may be similar or identical for different users based on similar inputs — no exclusivity is provided.</li>
          <li>You can opt out of aggregated data usage by contacting <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a>.</li>
        </ul>
      </section>

      <!-- ── 10. Third-Party Services ── -->
      <section id="third-party">
        <h2>10. Third-Party Services</h2>
        <p>Our Service integrates with third-party platforms. When you use these integrations, you are subject to their respective privacy policies:</p>
        <ul>
          <li><a href="https://slack.com/privacy-policy" target="_blank" rel="noopener">Slack Privacy Policy</a></li>
          <li><a href="https://discord.com/privacy" target="_blank" rel="noopener">Discord Privacy Policy</a></li>
          <li><a href="https://telegram.org/privacy" target="_blank" rel="noopener">Telegram Privacy Policy</a></li>
          <li><a href="https://stripe.com/privacy" target="_blank" rel="noopener">Stripe Privacy Policy</a></li>
        </ul>
        <p>We only share the minimum data necessary for the integration to function (e.g., notification content for messaging platforms).</p>
      </section>

      <!-- ── 11. Your Rights ── -->
      <section id="your-rights">
        <h2>11. Your Rights</h2>
        <p>Depending on your jurisdiction, you may have the following rights regarding your personal data:</p>
        <table class="legal-table">
          <thead>
            <tr><th>Right</th><th>Description</th></tr>
          </thead>
          <tbody>
            <tr><td>Access</td><td>Request a copy of the personal data we hold about you.</td></tr>
            <tr><td>Rectification</td><td>Request correction of inaccurate or incomplete data.</td></tr>
            <tr><td>Erasure</td><td>Request deletion of your personal data ("right to be forgotten").</td></tr>
            <tr><td>Portability</td><td>Request your data in a structured, machine-readable format.</td></tr>
            <tr><td>Restriction</td><td>Request restriction of processing in certain circumstances.</td></tr>
            <tr><td>Objection</td><td>Object to processing based on legitimate interest.</td></tr>
            <tr><td>Withdraw Consent</td><td>Withdraw consent at any time where processing is based on consent.</td></tr>
          </tbody>
        </table>
        <p>To exercise any of these rights, contact <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a>. We will respond within 30 days.</p>
      </section>

      <!-- ── 12. International Data Transfers ── -->
      <section id="international">
        <h2>12. International Data Transfers</h2>
        <p>Your data may be transferred to and processed in the United States, where our primary servers are located. For transfers from the EEA/UK, we rely on:</p>
        <ul>
          <li>Standard Contractual Clauses (SCCs) approved by the European Commission.</li>
          <li>Adequacy decisions where applicable.</li>
          <li>Supplementary measures to ensure data protection standards are maintained.</li>
        </ul>
      </section>

      <!-- ── 13. Children's Privacy ── -->
      <section id="children">
        <h2>13. Children's Privacy</h2>
        <p>The Service is not intended for individuals under 18 years of age. We do not knowingly collect personal information from children. If we become aware that a child under 18 has provided us with personal information, we will take steps to delete such information promptly.</p>
      </section>

      <!-- ── 14. California Privacy Rights (CCPA) ── -->
      <section id="california">
        <h2>14. California Privacy Rights (CCPA)</h2>
        <p>If you are a California resident, you have additional rights under the California Consumer Privacy Act (CCPA):</p>
        <ul>
          <li><strong>Right to Know</strong> — You can request details about the categories and specific pieces of personal information we have collected.</li>
          <li><strong>Right to Delete</strong> — You can request deletion of your personal information, subject to certain exceptions.</li>
          <li><strong>Right to Non-Discrimination</strong> — We will not discriminate against you for exercising your CCPA rights.</li>
          <li><strong>No Sale of Personal Information</strong> — We do NOT sell personal information. We have not sold personal information in the preceding 12 months.</li>
        </ul>
        <p>To make a CCPA request, contact <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a> with the subject line "CCPA Request".</p>
      </section>

      <!-- ── 15. Changes ── -->
      <section id="changes">
        <h2>15. Changes to This Policy</h2>
        <p>We may update this Privacy Policy from time to time. When we make material changes, we will notify you by email and update the "Last updated" date. We encourage you to review this page periodically for the latest information on our privacy practices.</p>
      </section>

      <!-- ── 16. Contact ── -->
      <section id="contact">
        <h2>16. Contact Us</h2>
        <p>If you have any questions, concerns, or complaints about this Privacy Policy or our data practices, contact us at:</p>
        <div class="contact-card">
          <p><strong>FetchBot Inc. — Data Protection</strong></p>
          <p>Email: <a href="mailto:privacy@fetchbot.ai">privacy@fetchbot.ai</a></p>
          <p>General: <a href="mailto:support@fetchbot.ai">support@fetchbot.ai</a></p>
          <p>Website: <a href="https://fetchbot.ai" target="_blank" rel="noopener">https://fetchbot.ai</a></p>
        </div>
        <p>For EEA/UK users: If you believe we have not adequately addressed your data protection concern, you have the right to lodge a complaint with your local Data Protection Authority (DPA).</p>
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
