// Pricing tiers shown on the paywall.
// TODO: team decision — replace price IDs with real Stripe price IDs once created.
// TODO: team decision — finalize feature bullets per tier.

export const TIERS = [
    {
        id: 'starter',
        name: 'Starter',
        price: 29,
        priceLabel: '$29',
        period: '/month',
        description: 'For solo founders and small sites getting started with AI visibility.',
        features: [
            '1 website',
            '4 LLM providers (Claude, GPT-4, Gemini, Perplexity)',
            'Weekly audits',
            '10 prompts per audit',
            'Email support',
        ],
        cta: 'Start with Starter',
        // TODO: replace with real Stripe price id from dashboard
        stripePriceId: 'TODO_STRIPE_PRICE_ID_STARTER_29',
        planCode: 'starter',
        highlight: false,
    },
    {
        id: 'pro',
        name: 'Pro',
        price: 96,
        priceLabel: '$96',
        period: '/month',
        description: 'For growing teams who need competitive intelligence and scheduled monitoring.',
        features: [
            'Up to 5 websites',
            '4 LLM providers + competitor tracking',
            'Daily audits',
            '50 prompts per audit',
            'Trend intelligence + recommendations',
            'Priority support',
        ],
        cta: 'Upgrade to Pro',
        // TODO: replace with real Stripe price id from dashboard
        stripePriceId: 'TODO_STRIPE_PRICE_ID_PRO_96',
        planCode: 'pro',
        highlight: true,
    },
    {
        id: 'enterprise',
        name: 'Business',
        price: null,
        priceLabel: 'Custom',
        period: '',
        description: 'Dedicated support, custom integrations, and unlimited scale.',
        features: [
            'Unlimited websites',
            'SSO, SAML, audit logs',
            'Custom prompt packs',
            'API access + white-label',
            'Dedicated account manager',
        ],
        cta: 'Contact sales',
        stripePriceId: null,
        planCode: 'enterprise',
        // TODO: team decision — replace with real contact target (calendly link or sales@)
        contactTarget: 'mailto:sales@fetchbot.ai?subject=Business plan inquiry',
        highlight: false,
    },
]
