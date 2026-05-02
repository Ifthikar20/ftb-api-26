// Pricing tiers shown on the paywall.
//
// Three tiers: Individual ($45), Pro ($100), Business (contact). The
// per-tier ``maxPromptsPerAudit`` mirrors core.utils.constants.PLAN_LIMITS
// — keep in sync with the backend or the dashboard will lie about the
// cap a user has when their plan changes.

export const TIERS = [
    {
        id: 'individual',
        name: 'Individual',
        price: 45,
        priceLabel: '$45',
        period: '/month',
        maxPromptsPerAudit: 5,
        description: 'For solo founders watching one site.',
        features: [
            '1 website',
            '5 prompts per audit',
            '4 audits / month',
            'Claude + GPT-4',
            'Email support',
        ],
        cta: 'Start with Individual',
        // Backend reads STRIPE_INDIVIDUAL_PRICE_ID from env.
        stripePriceId: 'STRIPE_INDIVIDUAL_PRICE_ID',
        planCode: 'individual',
        highlight: false,
    },
    {
        id: 'pro',
        name: 'Pro',
        price: 100,
        priceLabel: '$100',
        period: '/month',
        maxPromptsPerAudit: 15,
        description: 'Full access — every LLM provider and competitor tracking.',
        features: [
            'Up to 5 websites',
            '15 prompts per audit',
            'Daily audits',
            '4 LLM providers (Claude, GPT-4, Gemini, Perplexity)',
            'Competitor tracking + RAG knowledge base',
            'Trend intelligence + recommendations',
            'Priority support',
        ],
        cta: 'Upgrade to Pro',
        stripePriceId: 'STRIPE_PRO_PRICE_ID',
        planCode: 'pro',
        highlight: true,
    },
    {
        id: 'enterprise',
        name: 'Business',
        price: null,
        priceLabel: 'Custom',
        period: '',
        maxPromptsPerAudit: 50,
        description: 'Dedicated support, custom integrations, and unlimited scale.',
        features: [
            'Unlimited websites',
            '50+ prompts per audit',
            'Unlimited audits',
            'SSO, SAML, audit logs',
            'Custom prompt packs',
            'API access + white-label',
            'Dedicated account manager',
        ],
        cta: 'Contact sales',
        stripePriceId: null,
        planCode: 'enterprise',
        contactTarget: 'mailto:sales@fetchbot.ai?subject=Business plan inquiry',
        highlight: false,
    },
]
