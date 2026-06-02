# Telegram Language Detection Methods

Telegram language detection is implemented as a source-aware segmentation and
aggregation workflow rather than a direct copy of the YouTube LID pipeline.

## Inputs

- Channel title/about/description where available.
- Message text fields: `post_content`, `all_text`, `searchable_text`,
  `image_text`, and `transcript_text`.
- Existing provisional `detected_language`.
- Optional review labels and adjudications.

## Segmentation

`telegram_descriptive.language.segmentation` creates one segment per text source
with source weights. OCR/transcript text are retained because Telegram has a
large media/no-text share.

## Aggregation

`telegram_descriptive.language.aggregation` combines segment-level predictions
with weighted confidence. It preserves:

- `NO TEXT` for insufficient evidence.
- `MIXED` when top labels are close.
- Confidence, margin, evidence weight, and segment count.

## Validation

Validation queues should be stratified by:

- High-reach channels.
- High-impact languages.
- Confusable language families.
- Mixed/no-text channels.
- Source-list or crawl-route cohorts.

Adjudications are merged explicitly so original predictions remain auditable.

