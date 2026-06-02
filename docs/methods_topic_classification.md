# Telegram Topic Classification Methods

Topic classification is Telegram-native and should not blindly copy YouTube
channel categories.

## Taxonomy

`telegram_descriptive.topics.taxonomy` defines `telegram_topics_v1`, including:

- News/politics
- Geopolitics/war
- Health
- Crypto/finance
- Commerce
- Entertainment
- Religion
- Ideology/movements
- Scams/spam
- File sharing
- Adult content
- Local community
- Education
- Technology
- Mixed/unknown

## Evidence Bundles

Evidence bundles should include title, about/description, representative recent
messages, high-view messages, domains/URLs, and forwarded-from sources. They
should not send full message histories to an LLM.

## Implementation

The package includes:

- Prompt builders.
- Taxonomy validation.
- A conservative keyword fallback for smoke tests.
- Review-queue prioritization for low-confidence and high-reach channels.

Every production classifier output should track taxonomy version, prompt
version, model, temperature, evidence IDs, confidence, and rationale.

