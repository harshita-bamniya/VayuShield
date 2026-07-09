"""Advisory Engine — generates plain-text public-health advisories from attribution + forecast.

No LLM. Uses a template system keyed on (aqi_level, dominant_source, language).
Module 09 (Claude API) will upgrade the body generation to use an LLM.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.aqi import aqi_category
from app.core.claude_client import generate_text
from app.modules.advisory import repository as repo
from app.modules.advisory.schemas import AdvisoryGenerateResponse, AdvisoryOut

# Languages to generate advisories for on each /generate call.
# "en" is the default; "hi" is the first regional language.
ADVISORY_LANGUAGES = ["en", "hi"]

# --------------------------------------------------------------------------- #
# Template data                                                               #
# --------------------------------------------------------------------------- #

_SOURCE_LABEL_EN = {
    "vehicular": "vehicular emissions (vehicles and transport)",
    "industrial": "industrial activities",
    "construction": "construction dust",
    "agricultural": "agricultural burning (crop residue)",
    "fire": "active fire hotspots",
    "other": "mixed pollution sources",
}

_SOURCE_LABEL_HI = {
    "vehicular": "वाहनों के धुएं",
    "industrial": "औद्योगिक गतिविधियों",
    "construction": "निर्माण कार्य की धूल",
    "agricultural": "पराली जलाने",
    "fire": "सक्रिय आग के स्थानों",
    "other": "मिश्रित प्रदूषण स्रोतों",
}

_AQI_ADVICE_EN = {
    "Good": (
        "Outdoor air quality is good today.",
        "No restrictions are needed for any group.",
        "Enjoy outdoor activities freely.",
        "Continue monitoring for any changes.",
    ),
    "Satisfactory": (
        "Air quality is satisfactory with minor pollutant levels.",
        "Sensitive individuals (elderly, children, and those with respiratory conditions) "
        "may experience mild discomfort during prolonged outdoor activity.",
        "General population can continue outdoor activities normally.",
        "Consider reducing strenuous exercise if you experience any irritation.",
    ),
    "Moderate": (
        "Air quality is moderate and may cause breathing discomfort to sensitive people.",
        "People with heart disease, lung disease, asthma, or diabetes should limit "
        "prolonged outdoor exertion.",
        "Keep windows closed during peak traffic hours and use air purifiers indoors if available.",
        "Children and elderly should avoid extended outdoor activity.",
    ),
    "Poor": (
        "Air quality is poor and likely to cause breathing discomfort to most people.",
        "Avoid prolonged outdoor physical activity — particularly jogging, cycling, or sports.",
        "Wear an N95/FFP2 mask if outdoor exposure is unavoidable.",
        "People with respiratory or cardiovascular conditions should stay indoors.",
    ),
    "Very Poor": (
        "Air quality is very poor and may cause serious respiratory illness on prolonged exposure.",
        "Avoid all non-essential outdoor activity.",
        "Keep doors and windows shut; use air purifiers with HEPA filters.",
        "Seek medical attention immediately if you experience shortness of breath, "
        "chest tightness, or persistent coughing.",
    ),
    "Severe": (
        "Air quality has reached a SEVERE level — a public health emergency.",
        "All outdoor activity is strongly discouraged for the entire population.",
        "Schools, construction sites, and outdoor markets should be closed.",
        "If you must go outdoors, wear a certified respirator (N95 or better) "
        "and minimise exposure time.",
    ),
}

_AQI_ADVICE_HI = {
    "Good": (
        "आज वायु गुणवत्ता अच्छी है।",
        "किसी भी समूह के लिए कोई प्रतिबंध आवश्यक नहीं है।",
        "बाहरी गतिविधियाँ स्वतंत्र रूप से करें।",
        "किसी भी बदलाव के लिए निगरानी जारी रखें।",
    ),
    "Satisfactory": (
        "वायु गुणवत्ता संतोषजनक है, प्रदूषक स्तर थोड़ा बढ़ा हुआ है।",
        "संवेदनशील व्यक्ति (बुजुर्ग, बच्चे और श्वसन रोगियों) को लंबे समय तक बाहर रहने पर हल्की परेशानी हो सकती है।",
        "सामान्य जनता सामान्य रूप से बाहरी गतिविधियाँ जारी रख सकती है।",
        "यदि कोई जलन महसूस हो तो कठिन व्यायाम कम करें।",
    ),
    "Moderate": (
        "वायु गुणवत्ता मध्यम है और संवेदनशील लोगों को सांस लेने में परेशानी हो सकती है।",
        "हृदय रोग, फेफड़े की बीमारी, अस्थमा या मधुमेह से पीड़ित लोग लंबे समय तक बाहर कठिन परिश्रम करने से बचें।",
        "पीक ट्रैफिक घंटों के दौरान खिड़कियाँ बंद रखें और यदि उपलब्ध हो तो एयर प्यूरीफायर का उपयोग करें।",
        "बच्चे और बुजुर्ग लंबे समय तक बाहर न रहें।",
    ),
    "Poor": (
        "वायु गुणवत्ता खराब है और अधिकांश लोगों को सांस लेने में परेशानी हो सकती है।",
        "लंबे समय तक बाहर शारीरिक गतिविधि से बचें।",
        "यदि बाहर जाना अपरिहार्य हो तो N95/FFP2 मास्क पहनें।",
        "श्वसन या हृदय रोग से पीड़ित लोग घर के अंदर रहें।",
    ),
    "Very Poor": (
        "वायु गुणवत्ता बहुत खराब है और लंबे समय तक संपर्क में रहने से गंभीर श्वसन रोग हो सकता है।",
        "सभी अनावश्यक बाहरी गतिविधियों से बचें।",
        "दरवाजे और खिड़कियाँ बंद रखें; HEPA फिल्टर वाले एयर प्यूरीफायर का उपयोग करें।",
        "यदि सांस लेने में तकलीफ, सीने में जकड़न या लगातार खांसी हो तो तुरंत चिकित्सा सहायता लें।",
    ),
    "Severe": (
        "वायु गुणवत्ता गंभीर स्तर पर पहुँच गई है — यह एक सार्वजनिक स्वास्थ्य आपातकाल है।",
        "पूरी जनसंख्या के लिए सभी बाहरी गतिविधियाँ दृढ़ता से हतोत्साहित हैं।",
        "स्कूल, निर्माण स्थल और बाहरी बाजार बंद होने चाहिए।",
        "यदि बाहर जाना हो तो प्रमाणित रेस्पिरेटर (N95 या बेहतर) पहनें।",
    ),
}

_AQI_TITLE_EN = {
    "Good": "Air Quality Advisory — Good Conditions",
    "Satisfactory": "Air Quality Advisory — Satisfactory Conditions",
    "Moderate": "Air Quality Advisory — Moderate Pollution Alert",
    "Poor": "Air Quality Advisory — Poor Air Quality Warning",
    "Very Poor": "Air Quality Advisory — Very Poor Air Quality Alert",
    "Severe": "URGENT: Severe Air Quality Emergency",
}

_AQI_TITLE_HI = {
    "Good": "वायु गुणवत्ता सलाह — अच्छी स्थिति",
    "Satisfactory": "वायु गुणवत्ता सलाह — संतोषजनक स्थिति",
    "Moderate": "वायु गुणवत्ता सलाह — मध्यम प्रदूषण चेतावनी",
    "Poor": "वायु गुणवत्ता सलाह — खराब वायु गुणवत्ता चेतावनी",
    "Very Poor": "वायु गुणवत्ता चेतावनी — अत्यंत खराब वायु गुणवत्ता",
    "Severe": "तत्काल: गंभीर वायु गुणवत्ता आपातकाल",
}


def _build_body_en(aqi_level: str, dominant_source: str | None, aqi_value: int) -> str:
    src_label = _SOURCE_LABEL_EN.get(dominant_source or "other", "mixed pollution sources")
    advice = _AQI_ADVICE_EN.get(aqi_level, _AQI_ADVICE_EN["Moderate"])
    intro = (
        f"Current AQI is {aqi_value} ({aqi_level}), primarily driven by {src_label}. {advice[0]}"
    )
    return " ".join([intro, advice[1], advice[2], advice[3]])


def _build_body_hi(aqi_level: str, dominant_source: str | None, aqi_value: int) -> str:
    src_label = _SOURCE_LABEL_HI.get(dominant_source or "other", "मिश्रित प्रदूषण स्रोतों")
    advice = _AQI_ADVICE_HI.get(aqi_level, _AQI_ADVICE_HI["Moderate"])
    intro = f"वर्तमान AQI {aqi_value} ({aqi_level}) है, जो मुख्यतः {src_label} के कारण है। {advice[0]}"
    return " ".join([intro, advice[1], advice[2], advice[3]])


_BUILDERS = {
    "en": (_AQI_TITLE_EN, _build_body_en),
    "hi": (_AQI_TITLE_HI, _build_body_hi),
}


def _build_advisory_text_template(
    language: str, aqi_level: str, dominant_source: str | None, aqi_value: int
) -> tuple[str, str]:
    """Return (title, body) using static templates. Falls back to English."""
    titles, body_fn = _BUILDERS.get(language, _BUILDERS["en"])
    title = titles.get(aqi_level, titles.get("Moderate", "Air Quality Advisory"))
    body = body_fn(aqi_level, dominant_source, aqi_value)
    return title, body


_LANG_NAMES = {"en": "English", "hi": "Hindi"}


async def _build_advisory_text(
    language: str, aqi_level: str, dominant_source: str | None, aqi_value: int
) -> tuple[str, str]:
    """Return (title, body) — tries Claude first, falls back to templates."""
    lang_name = _LANG_NAMES.get(language, "English")
    src_label = _SOURCE_LABEL_EN.get(dominant_source or "other", "mixed sources")
    prompt = (
        f"Write a public health air quality advisory in {lang_name}. "
        f"Current AQI: {aqi_value} ({aqi_level}). Dominant pollution source: {src_label}. "
        f"The advisory should be 4-5 sentences, factual, and give actionable health guidance "
        f"appropriate for the AQI level. Do not include a title or subject line — body text only."
    )
    ai_body = await generate_text(
        prompt,
        system=(
            "You are a public health official issuing air quality advisories. "
            "Write clear, concise, actionable advisories. No headers, no bullet points."
        ),
        max_tokens=350,
    )
    titles, body_fn = _BUILDERS.get(language, _BUILDERS["en"])
    title = titles.get(aqi_level, titles.get("Moderate", "Air Quality Advisory"))
    body = ai_body if ai_body else body_fn(aqi_level, dominant_source, aqi_value)
    return title, body


# --------------------------------------------------------------------------- #
# Service functions                                                            #
# --------------------------------------------------------------------------- #


async def _get_latest_context(db: AsyncSession, city_id: str) -> tuple[int, str]:
    """Return (current_aqi, dominant_source) from latest attribution + forecast."""
    # Try latest attribution first (has dominant_source)
    attr_row = await db.execute(
        text(
            """
            SELECT dominant_source,
                   vehicular_pct, industrial_pct, construction_pct,
                   agricultural_pct, fire_pct, other_pct
            FROM attributions
            WHERE city_id = :city_id
            ORDER BY computed_at DESC
            LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    attr = attr_row.fetchone()
    dominant_source: str = attr[0] if attr else "vehicular"

    # Latest AQI from station readings
    aqi_row = await db.execute(
        text(
            """
            SELECT AVG(aqi) AS avg_aqi
            FROM station_readings sr
            JOIN stations s ON s.id = sr.station_id
            WHERE s.city_id = :city_id
              AND sr.ts >= NOW() - INTERVAL '2 hours'
            """
        ),
        {"city_id": city_id},
    )
    aqi_result = aqi_row.fetchone()
    aqi_value = int(aqi_result[0]) if aqi_result and aqi_result[0] else 200

    return aqi_value, dominant_source


async def generate_advisories(
    db: AsyncSession, city_id: str, languages: list[str] | None = None
) -> AdvisoryGenerateResponse:
    """Generate one advisory per language for today, skipping duplicates."""
    langs = languages or ADVISORY_LANGUAGES
    aqi_value, dominant_source = await _get_latest_context(db, city_id)
    aqi_level = aqi_category(aqi_value)

    generated_items: list[dict] = []
    skipped = 0

    for lang in langs:
        already_exists = await repo.advisory_exists_today(db, city_id, aqi_level, lang)
        if already_exists:
            skipped += 1
            continue

        title, body = await _build_advisory_text(lang, aqi_level, dominant_source, aqi_value)
        row = await repo.create_advisory(
            db=db,
            city_id=city_id,
            language=lang,
            title=title,
            body=body,
            aqi_level=aqi_level,
            dominant_source=dominant_source,
            channel="web",
        )
        generated_items.append(row)

    await db.commit()

    advisories = [AdvisoryOut(**item) for item in generated_items]
    return AdvisoryGenerateResponse(
        generated=len(advisories),
        skipped=skipped,
        advisories=advisories,
    )


async def list_advisories(
    db: AsyncSession,
    city_id: str,
    language: str | None = None,
    channel: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[AdvisoryOut], int]:
    rows, total = await repo.list_advisories(
        db, city_id, language=language, channel=channel, limit=limit, offset=offset
    )
    return [AdvisoryOut(**r) for r in rows], total


async def get_advisory(db: AsyncSession, advisory_id: str, city_id: str) -> AdvisoryOut | None:
    row = await repo.get_advisory(db, advisory_id, city_id)
    return AdvisoryOut(**row) if row else None


async def count_advisories(db: AsyncSession, city_id: str) -> int:
    return await repo.count_advisories(db, city_id)
