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
ADVISORY_LANGUAGES = ["en", "hi", "kn", "ta"]

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

_SOURCE_LABEL_KN = {
    "vehicular": "ವಾಹನ ಹೊಗೆ",
    "industrial": "ಕೈಗಾರಿಕಾ ಚಟುವಟಿಕೆಗಳು",
    "construction": "ನಿರ್ಮಾಣ ಧೂಳು",
    "agricultural": "ಕೃಷಿ ಸುಡುವಿಕೆ",
    "fire": "ಸಕ್ರಿಯ ಬೆಂಕಿ ತಾಣಗಳು",
    "other": "ಮಿಶ್ರ ಮಾಲಿನ್ಯ ಮೂಲಗಳು",
}

_SOURCE_LABEL_TA = {
    "vehicular": "வாகன புகை",
    "industrial": "தொழிற்சாலை நடவடிக்கைகள்",
    "construction": "கட்டுமான தூசி",
    "agricultural": "விவசாய எரிப்பு",
    "fire": "செயலில் உள்ள தீ இடங்கள்",
    "other": "கலப்பு மாசு மூலங்கள்",
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

_AQI_ADVICE_KN = {
    "Good": (
        "ಇಂದು ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಉತ್ತಮವಾಗಿದೆ.",
        "ಯಾವುದೇ ಗುಂಪಿಗೂ ನಿರ್ಬಂಧಗಳ ಅಗತ್ಯವಿಲ್ಲ.",
        "ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ಮುಕ್ತವಾಗಿ ಆನಂದಿಸಿ.",
        "ಯಾವುದೇ ಬದಲಾವಣೆಗಳಿಗಾಗಿ ಮೇಲ್ವಿಚಾರಣೆ ಮುಂದುವರಿಸಿ.",
    ),
    "Satisfactory": (
        "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ತೃಪ್ತಿಕರವಾಗಿದೆ.",
        "ಸಂವೇದನಾಶೀಲ ವ್ಯಕ್ತಿಗಳಿಗೆ (ವೃದ್ಧರು, ಮಕ್ಕಳು, ಉಸಿರಾಟದ ತೊಂದರೆ ಇರುವವರು) ಸ್ವಲ್ಪ ಅಸ್ವಸ್ಥತೆ ಆಗಬಹುದು.",
        "ಸಾಮಾನ್ಯ ಜನರು ಸಾಮಾನ್ಯ ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ಮುಂದುವರಿಸಬಹುದು.",
        "ಯಾವುದಾದರೂ ಉರಿಯೂತ ಅನುಭವಿಸಿದರೆ ಕಠಿಣ ವ್ಯಾಯಾಮವನ್ನು ಕಡಿಮೆ ಮಾಡಿ.",
    ),
    "Moderate": (
        "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಮಧ್ಯಮ ಮಟ್ಟದಲ್ಲಿದ್ದು ಸಂವೇದನಾಶೀಲ ಜನರಿಗೆ ಉಸಿರಾಟದ ತೊಂದರೆ ಆಗಬಹುದು.",
        "ಹೃದ್ರೋಗ, ಶ್ವಾಸಕೋಶದ ಕಾಯಿಲೆ, ಆಸ್ತಮಾ ಅಥವಾ ಮಧುಮೇಹ ಇರುವವರು ದೀರ್ಘಕಾಲ ಹೊರಗೆ ದೈಹಿಕ ಶ್ರಮ ತಪ್ಪಿಸಿ.",
        "ಗರಿಷ್ಠ ಟ್ರಾಫಿಕ್ ಸಮಯದಲ್ಲಿ ಕಿಟಕಿಗಳನ್ನು ಮುಚ್ಚಿ ಮತ್ತು ಒಳಾಂಗಣದಲ್ಲಿ ಏರ್ ಪ್ಯೂರಿಫೈಯರ್ ಬಳಸಿ.",
        "ಮಕ್ಕಳು ಮತ್ತು ವೃದ್ಧರು ಹೊರಗೆ ದೀರ್ಘಕಾಲ ಇರುವುದನ್ನು ತಪ್ಪಿಸಿ.",
    ),
    "Poor": (
        "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಕಳಪೆಯಾಗಿದ್ದು ಹೆಚ್ಚಿನ ಜನರಿಗೆ ಉಸಿರಾಟದ ತೊಂದರೆ ಆಗಬಹುದು.",
        "ದೀರ್ಘಕಾಲ ಹೊರಾಂಗಣ ದೈಹಿಕ ಚಟುವಟಿಕೆಯನ್ನು ತಪ್ಪಿಸಿ.",
        "ಹೊರಗೆ ಹೋಗಲೇಬೇಕಾದರೆ N95/FFP2 ಮಾಸ್ಕ್ ಧರಿಸಿ.",
        "ಉಸಿರಾಟ ಅಥವಾ ಹೃದ್ರೋಗ ಇರುವವರು ಮನೆಯಲ್ಲೇ ಇರಿ.",
    ),
    "Very Poor": (
        "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಅತ್ಯಂತ ಕಳಪೆಯಾಗಿದ್ದು ದೀರ್ಘಕಾಲ ಸಂಪರ್ಕದಿಂದ ಗಂಭೀರ ಉಸಿರಾಟದ ಅನಾರೋಗ್ಯ ಉಂಟಾಗಬಹುದು.",
        "ಎಲ್ಲಾ ಅನಗತ್ಯ ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಯನ್ನು ತಪ್ಪಿಸಿ.",
        "ಬಾಗಿಲು ಮತ್ತು ಕಿಟಕಿಗಳನ್ನು ಮುಚ್ಚಿ; HEPA ಫಿಲ್ಟರ್ ಏರ್ ಪ್ಯೂರಿಫೈಯರ್ ಬಳಸಿ.",
        "ಉಸಿರಾಟದ ತೊಂದರೆ, ಎದೆ ನೋವು ಅಥವಾ ನಿರಂತರ ಕೆಮ್ಮು ಉಂಟಾದರೆ ತಕ್ಷಣ ವೈದ್ಯಕೀಯ ಸಹಾಯ ಪಡೆಯಿರಿ.",
    ),
    "Severe": (
        "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ತೀವ್ರ ಮಟ್ಟ ತಲುಪಿದೆ — ಇದು ಸಾರ್ವಜನಿಕ ಆರೋಗ್ಯ ತುರ್ತುಸ್ಥಿತಿ.",
        "ಸಮಗ್ರ ಜನಸಂಖ್ಯೆಗೆ ಎಲ್ಲಾ ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ದೃಢವಾಗಿ ನಿರುತ್ಸಾಹಗೊಳಿಸಲಾಗುತ್ತದೆ.",
        "ಶಾಲೆಗಳು, ನಿರ್ಮಾಣ ಸ್ಥಳಗಳು ಮತ್ತು ಹೊರಾಂಗಣ ಮಾರುಕಟ್ಟೆಗಳನ್ನು ಮುಚ್ಚಬೇಕು.",
        "ಹೊರಗೆ ಹೋಗಲೇಬೇಕಾದರೆ N95 ಅಥವಾ ಉತ್ತಮ ಶ್ರೇಣಿಯ ಪ್ರಮಾಣೀಕೃತ ರೆಸ್ಪಿರೇಟರ್ ಧರಿಸಿ.",
    ),
}

_AQI_ADVICE_TA = {
    "Good": (
        "இன்று காற்றின் தரம் நன்றாக உள்ளது.",
        "எந்த குழுவிற்கும் எந்த கட்டுப்பாடும் தேவையில்லை.",
        "வெளிப்புற நடவடிக்கைகளை சுதந்திரமாக அனுபவியுங்கள்.",
        "எந்த மாற்றங்களுக்கும் கண்காணிப்பை தொடர்ந்து கொள்ளுங்கள்.",
    ),
    "Satisfactory": (
        "காற்றின் தரம் திருப்திகரமாக உள்ளது.",
        "உணர்திறன் உடையவர்கள் (முதியோர், குழந்தைகள், சுவாசப் பிரச்சனை உள்ளவர்கள்) சிறிய அசௌகர்யம் உணரலாம்.",
        "பொதுமக்கள் வழக்கமான வெளிப்புற நடவடிக்கைகளை தொடரலாம்.",
        "எரிச்சல் உணர்ந்தால் கடுமையான உடற்பயிற்சியை குறைக்கவும்.",
    ),
    "Moderate": (
        "காற்றின் தரம் மிதமானதாக உள்ளது மற்றும் உணர்திறன் உள்ளவர்களுக்கு சுவாசிக்க சிரமம் ஏற்படலாம்.",
        "இதய நோய், நுரையீரல் நோய், ஆஸ்துமா அல்லது நீரிழிவு உள்ளவர்கள் நீண்ட நேரம் வெளியில் கடின உழைப்பை தவிர்க்கவும்.",
        "போக்குவரத்து நேரத்தில் ஜன்னல்களை மூடி, உள்ளிருக்கும்போது காற்று சுத்திகரிப்பாளர் பயன்படுத்தவும்.",
        "குழந்தைகளும் முதியோரும் நீண்ட நேரம் வெளியில் இருப்பதை தவிர்க்கவும்.",
    ),
    "Poor": (
        "காற்றின் தரம் மோசமாக உள்ளது மற்றும் பெரும்பாலான மக்களுக்கு சுவாசிக்க சிரமம் ஏற்படலாம்.",
        "நீண்ட நேரம் வெளிப்புற உடல் நடவடிக்கையை தவிர்க்கவும்.",
        "வெளியில் செல்வது அவசியமானால் N95/FFP2 முகமூடி அணியவும்.",
        "சுவாச அல்லது இதய நோய் உள்ளவர்கள் வீட்டிலேயே இருக்கவும்.",
    ),
    "Very Poor": (
        "காற்றின் தரம் மிகவும் மோசமாக உள்ளது மற்றும் நீண்ட வெளிப்பாட்டால் தீவிர சுவாச நோய் ஏற்படலாம்.",
        "அனைத்து தேவையற்ற வெளிப்புற நடவடிக்கைகளையும் தவிர்க்கவும்.",
        "கதவுகளையும் ஜன்னல்களையும் மூடி வைக்கவும்; HEPA வடிகட்டி காற்று சுத்திகரிப்பாளர் பயன்படுத்தவும்.",
        "மூச்சு திணறல், நெஞ்சு இறுக்கம் அல்லது தொடர்ந்த இருமல் ஏற்பட்டால் உடனடியாக மருத்துவ உதவி பெறவும்.",
    ),
    "Severe": (
        "காற்றின் தரம் தீவிர நிலையை எட்டியுள்ளது — இது பொது சுகாதார அவசரநிலை.",
        "அனைத்து மக்களுக்கும் அனைத்து வெளிப்புற நடவடிக்கைகளும் கடுமையாக தடுக்கப்படுகின்றன.",
        "பள்ளிகள், கட்டுமான தளங்கள் மற்றும் வெளிப்புற சந்தைகள் மூடப்பட வேண்டும்.",
        "வெளியில் செல்வது அவசியமானால் சான்றளிக்கப்பட்ட N95 அல்லது சிறந்த சுவாசக் கருவி அணியவும்.",
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

_AQI_TITLE_KN = {
    "Good": "ವಾಯು ಗುಣಮಟ್ಟ ಸಲಹೆ — ಉತ್ತಮ ಸ್ಥಿತಿ",
    "Satisfactory": "ವಾಯು ಗುಣಮಟ್ಟ ಸಲಹೆ — ತೃಪ್ತಿಕರ ಸ್ಥಿತಿ",
    "Moderate": "ವಾಯು ಗುಣಮಟ್ಟ ಸಲಹೆ — ಮಧ್ಯಮ ಮಾಲಿನ್ಯ ಎಚ್ಚರಿಕೆ",
    "Poor": "ವಾಯು ಗುಣಮಟ್ಟ ಸಲಹೆ — ಕಳಪೆ ವಾಯು ಗುಣಮಟ್ಟ ಎಚ್ಚರಿಕೆ",
    "Very Poor": "ವಾಯು ಗುಣಮಟ್ಟ ಎಚ್ಚರಿಕೆ — ಅತ್ಯಂತ ಕಳಪೆ ವಾಯು ಗುಣಮಟ್ಟ",
    "Severe": "ತುರ್ತು: ತೀವ್ರ ವಾಯು ಗುಣಮಟ್ಟ ತುರ್ತುಸ್ಥಿತಿ",
}

_AQI_TITLE_TA = {
    "Good": "காற்று தர ஆலோசனை — நல்ல நிலை",
    "Satisfactory": "காற்று தர ஆலோசனை — திருப்திகரமான நிலை",
    "Moderate": "காற்று தர ஆலோசனை — மிதமான மாசு எச்சரிக்கை",
    "Poor": "காற்று தர ஆலோசனை — மோசமான காற்று தர எச்சரிக்கை",
    "Very Poor": "காற்று தர எச்சரிக்கை — மிகவும் மோசமான காற்று தரம்",
    "Severe": "அவசரம்: தீவிர காற்று தர அவசரநிலை",
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


def _build_body_kn(aqi_level: str, dominant_source: str | None, aqi_value: int) -> str:
    src_label = _SOURCE_LABEL_KN.get(dominant_source or "other", "ಮಿಶ್ರ ಮಾಲಿನ್ಯ ಮೂಲಗಳು")
    advice = _AQI_ADVICE_KN.get(aqi_level, _AQI_ADVICE_KN["Moderate"])
    intro = f"ಪ್ರಸ್ತುತ AQI {aqi_value} ({aqi_level}) ಆಗಿದ್ದು, ಮುಖ್ಯವಾಗಿ {src_label} ಕಾರಣದಿಂದ. {advice[0]}"
    return " ".join([intro, advice[1], advice[2], advice[3]])


def _build_body_ta(aqi_level: str, dominant_source: str | None, aqi_value: int) -> str:
    src_label = _SOURCE_LABEL_TA.get(dominant_source or "other", "கலப்பு மாசு மூலங்கள்")
    advice = _AQI_ADVICE_TA.get(aqi_level, _AQI_ADVICE_TA["Moderate"])
    intro = f"தற்போதைய AQI {aqi_value} ({aqi_level}) ஆகும், முக்கியமாக {src_label} காரணமாக. {advice[0]}"
    return " ".join([intro, advice[1], advice[2], advice[3]])


_BUILDERS = {
    "en": (_AQI_TITLE_EN, _build_body_en),
    "hi": (_AQI_TITLE_HI, _build_body_hi),
    "kn": (_AQI_TITLE_KN, _build_body_kn),
    "ta": (_AQI_TITLE_TA, _build_body_ta),
}


def _build_advisory_text_template(
    language: str, aqi_level: str, dominant_source: str | None, aqi_value: int
) -> tuple[str, str]:
    """Return (title, body) using static templates. Falls back to English."""
    titles, body_fn = _BUILDERS.get(language, _BUILDERS["en"])
    title = titles.get(aqi_level, titles.get("Moderate", "Air Quality Advisory"))
    body = body_fn(aqi_level, dominant_source, aqi_value)
    return title, body


_LANG_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil"}


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
    ward_id: str | None = None,
) -> tuple[list[AdvisoryOut], int]:
    rows, total = await repo.list_advisories(
        db, city_id, language=language, channel=channel, limit=limit, offset=offset, ward_id=ward_id
    )
    return [AdvisoryOut(**r) for r in rows], total


async def get_advisory(db: AsyncSession, advisory_id: str, city_id: str) -> AdvisoryOut | None:
    row = await repo.get_advisory(db, advisory_id, city_id)
    return AdvisoryOut(**row) if row else None


async def count_advisories(db: AsyncSession, city_id: str) -> int:
    return await repo.count_advisories(db, city_id)


async def generate_ward_advisories(
    db: AsyncSession, city_id: str, ward_id: str, languages: list[str] | None = None
) -> AdvisoryGenerateResponse:
    """Generate ward-level advisories using per-ward AQI and emission source context."""
    langs = languages or ADVISORY_LANGUAGES

    # Ward-specific AQI (last 2h average from stations in this ward)
    aqi_row = await db.execute(
        text("""
            SELECT ROUND(AVG(sr.aqi))::int, w.name
            FROM station_readings sr
            JOIN stations s ON s.id = sr.station_id
            JOIN wards w ON w.id = s.ward_id
            WHERE s.city_id = :city_id AND s.ward_id = :ward_id
              AND sr.aqi IS NOT NULL AND sr.ts >= NOW() - INTERVAL '2 hours'
            GROUP BY w.name
        """),
        {"city_id": city_id, "ward_id": ward_id},
    )
    aqi_result = aqi_row.fetchone()
    aqi_value = int(aqi_result[0]) if aqi_result and aqi_result[0] else None

    if aqi_value is None:
        # Fall back to city-level if ward has no recent readings
        city_aqi, dominant_source = await _get_latest_context(db, city_id)
        aqi_value = city_aqi
        ward_name = ward_id
    else:
        ward_name = aqi_result[1] if aqi_result else ward_id
        # Get dominant source from city attribution (ward-level attribution not yet separate)
        attr_row = await db.execute(
            text(
                "SELECT dominant_source FROM attributions"
                " WHERE city_id = :cid ORDER BY computed_at DESC LIMIT 1"
            ),
            {"cid": city_id},
        )
        attr = attr_row.fetchone()
        dominant_source = attr[0] if attr else "vehicular"

    aqi_level = aqi_category(aqi_value)
    generated_items: list[dict] = []
    skipped = 0

    for lang in langs:
        already_exists = await repo.advisory_exists_today(
            db, city_id, aqi_level, lang, ward_id=ward_id
        )
        if already_exists:
            skipped += 1
            continue

        title, body = await _build_advisory_text(lang, aqi_level, dominant_source, aqi_value)
        # Prepend ward name to title
        lang_ward_prefix = {
            "en": f"{ward_name} Ward — ",
            "hi": f"{ward_name} वार्ड — ",
            "kn": f"{ward_name} ವಾರ್ಡ್ — ",
            "ta": f"{ward_name} வார்டு — ",
        }
        title = lang_ward_prefix.get(lang, f"{ward_name} — ") + title

        row = await repo.create_advisory(
            db=db,
            city_id=city_id,
            ward_id=ward_id,
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
        generated=len(advisories), skipped=skipped, advisories=advisories
    )


def build_ivr_text(advisory: AdvisoryOut, language: str = "en") -> str:
    """Return a short TTS-friendly IVR script (≤ 30 words) from an advisory."""
    aqi_level = advisory.aqi_level
    src = advisory.dominant_source or "mixed sources"

    _IVR = {
        "en": (
            f"Air quality alert. Current AQI level is {aqi_level}, caused by {src}. "
            + {
                "Good": "Air is clean. No restrictions today.",
                "Satisfactory": "Sensitive groups should limit outdoor activity.",
                "Moderate": "Sensitive people should avoid prolonged outdoor exposure.",
                "Poor": "Wear a mask outdoors. Avoid exercise outside.",
                "Very Poor": "Stay indoors. Close windows. Seek medical help if breathless.",
                "Severe": "Emergency. All outdoor activity banned. Wear respirator if you must go out.",  # noqa: E501
            }.get(aqi_level, "Follow local authority guidance.")
        ),
        "hi": (
            f"वायु गुणवत्ता चेतावनी। वर्तमान AQI स्तर {aqi_level} है। "
            + {
                "Good": "वायु स्वच्छ है।",
                "Satisfactory": "संवेदनशील लोग बाहरी गतिविधि सीमित करें।",
                "Moderate": "संवेदनशील लोग लंबे समय तक बाहर न रहें।",
                "Poor": "बाहर मास्क पहनें। बाहर व्यायाम से बचें।",
                "Very Poor": "घर के अंदर रहें। खिड़कियाँ बंद करें। सांस की तकलीफ हो तो डॉक्टर से मिलें।",
                "Severe": "आपातकाल। बाहर न जाएं। जाना जरूरी हो तो रेस्पिरेटर पहनें।",
            }.get(aqi_level, "स्थानीय प्राधिकरण के निर्देशों का पालन करें।")
        ),
        "kn": (
            f"ವಾಯು ಗುಣಮಟ್ಟ ಎಚ್ಚರಿಕೆ। ಪ್ರಸ್ತುತ AQI ಮಟ್ಟ {aqi_level} ಆಗಿದೆ। "
            + {
                "Good": "ಗಾಳಿ ಶುದ್ಧವಾಗಿದೆ।",
                "Satisfactory": "ಸಂವೇದನಾಶೀಲ ಜನರು ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆ ಮಿತಿಗೊಳಿಸಿ.",
                "Moderate": "ಸಂವೇದನಾಶೀಲ ಜನರು ದೀರ್ಘಕಾಲ ಹೊರಗೆ ಇರಬೇಡಿ.",
                "Poor": "ಹೊರಗೆ ಮಾಸ್ಕ್ ಧರಿಸಿ. ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮ ತಪ್ಪಿಸಿ.",
                "Very Poor": "ಮನೆಯಲ್ಲಿ ಇರಿ. ಕಿಟಕಿಗಳು ಮುಚ್ಚಿ. ಉಸಿರಾಟ ಕಷ್ಟವಾದರೆ ವೈದ್ಯರನ್ನು ಕಾಣಿ.",
                "Severe": "ತುರ್ತು. ಹೊರಗೆ ಹೋಗಬೇಡಿ. ಅಗತ್ಯವಿದ್ದರೆ ರೆಸ್ಪಿರೇಟರ್ ಧರಿಸಿ.",
            }.get(aqi_level, "ಸ್ಥಳೀಯ ಅಧಿಕಾರಿಗಳ ಸೂಚನೆ ಪಾಲಿಸಿ.")
        ),
        "ta": (
            f"காற்று தர எச்சரிக்கை. தற்போதைய AQI நிலை {aqi_level}. "
            + {
                "Good": "காற்று சுத்தமாக உள்ளது.",
                "Satisfactory": "உணர்திறன் உள்ளவர்கள் வெளிப்புற நடவடிக்கையை குறைக்கவும்.",
                "Moderate": "உணர்திறன் உள்ளவர்கள் நீண்ட நேரம் வெளியில் இருக்க வேண்டாம்.",
                "Poor": "வெளியில் முகமூடி அணியவும். வெளிப்புற உடற்பயிற்சி தவிர்க்கவும்.",
                "Very Poor": "வீட்டில் இருங்கள். ஜன்னல்கள் மூடவும். மூச்சு திணறினால் மருத்துவரை அணுகவும்.",
                "Severe": "அவசரநிலை. வெளியில் செல்லாதீர்கள். செல்வது அவசியமானால் சுவாசக் கருவி அணியவும்.",
            }.get(aqi_level, "உள்ளூர் அதிகாரிகளின் வழிகாட்டுதலை பின்பற்றவும்.")
        ),
    }
    return _IVR.get(language, _IVR["en"])


async def get_ivr_advisory(
    db: AsyncSession, city_id: str, language: str = "en", ward_id: str | None = None
) -> dict:
    """Return the latest advisory for this city/ward in IVR-formatted text."""
    rows, _ = await repo.list_advisories(
        db, city_id, language=language, channel=None, limit=1, offset=0, ward_id=ward_id
    )
    if not rows:
        # Try English fallback
        rows, _ = await repo.list_advisories(
            db, city_id, language="en", channel=None, limit=1, offset=0
        )
    if not rows:
        return {
            "ivr_text": "No advisory available at this time. Please check back later.",
            "language": language,
        }
    advisory = AdvisoryOut(**rows[0])
    ivr_text = build_ivr_text(advisory, language=advisory.language)
    return {
        "ivr_text": ivr_text,
        "language": advisory.language,
        "aqi_level": advisory.aqi_level,
        "advisory_id": advisory.id,
    }
