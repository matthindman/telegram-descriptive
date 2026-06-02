"""Telegram-native topic taxonomy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    description: str


TELEGRAM_TOPICS_V1: tuple[Topic, ...] = (
    Topic("news_politics", "News / politics", "Current affairs, political commentary, civic information."),
    Topic("geopolitics_war", "Geopolitics / war", "Conflict, military, regional security, war reporting."),
    Topic("health", "Health", "Medicine, wellness, public health, health misinformation risk."),
    Topic("crypto_finance", "Crypto / finance", "Crypto, trading, investment, banking, financial advice."),
    Topic("commerce", "Commerce", "Sales, services, marketplaces, coupons, product promotion."),
    Topic("entertainment", "Entertainment", "Movies, music, memes, celebrity, sports, games."),
    Topic("religion", "Religion", "Religious teaching, worship, institutions, spiritual communities."),
    Topic("ideology_movements", "Ideology / movements", "Activist, extremist, nationalist, or movement content."),
    Topic("scams_spam", "Scams / spam", "Fraud, phishing, low-quality spam, suspicious promotion."),
    Topic("file_sharing", "File sharing", "Media, books, software, leaks, downloads, archives."),
    Topic("adult_content", "Adult content", "Sexual content or adult services."),
    Topic("local_community", "Local community", "Local services, neighborhood/community information."),
    Topic("education", "Education", "Courses, tutoring, learning resources, institutional education."),
    Topic("technology", "Technology", "Software, hardware, AI, cybersecurity, developer communities."),
    Topic("mixed_unknown", "Mixed / unknown", "Insufficient evidence or no dominant topical identity."),
)


def taxonomy_dict() -> dict[str, Topic]:
    return {topic.key: topic for topic in TELEGRAM_TOPICS_V1}

