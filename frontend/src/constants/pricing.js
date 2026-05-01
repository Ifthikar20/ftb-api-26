// Pricing tiers shown on the paywall.
//
// Currently we ship a single paid tier ($100 / month, gives Pro access)
// and a "talk to us" Business tier. Starter has been retired — every
// new sign-up goes straight to Pro. Re-introducing a lower tier later
// only requires adding it back to this array.

export const TIERS = [
    {
        id: 'pro',
        name: 'Pro',
        price: 100,
        priceLabel: '$100',
        period: '/month',
        description: 'Full access — every LLM provider, scheduled audits, competitor tracking.',
        features: [
            'Up to 5 websites',
            '4 LLM providers (Claude, GPT-4, Gemini, Perplexity)',
            'Daily audits',
            '50 prompts per audit',
            'Competitor tracking + RAG knowledge base',
            'Trend intelligence + recommendations',
            'Priority support',
        ],
        cta: 'Start with Pro',
        // Set STRIPE_PRO_PRICE_ID in env to point at the live or test
        // price object. When unset and DEBUG=True the backend grants Pro
        // access without charging — see ``StripeService.create_checkout_session``.
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
        contactTarget: 'mailto:sales@fetchbot.ai?subject=Business plan inquiry',
        highlight: false,
    },
]
