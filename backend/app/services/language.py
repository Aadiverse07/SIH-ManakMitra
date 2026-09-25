"""Lightweight language detection/localisation for ManakMitra chat.

The detector is intentionally deterministic and has no network/provider cost.
It supports the major Indian languages exposed by the voice assistant, plus Hinglish.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class LanguageInfo:
    code: str
    name: str


LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "te": "Telugu",
    "mr": "Marathi",
    "ta": "Tamil",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
    "ur": "Urdu",
    "hinglish": "Hinglish",
}

LOCALE_TO_LANGUAGE = {
    "en-IN": "en", "hi-IN": "hi", "bn-IN": "bn", "te-IN": "te",
    "mr-IN": "mr", "ta-IN": "ta", "gu-IN": "gu", "kn-IN": "kn",
    "ml-IN": "ml", "pa-IN": "pa", "or-IN": "or", "as-IN": "as",
    "ur-IN": "ur",
}

# Marathi markers are used only to disambiguate Devanagari, which is shared
# with Hindi. Unknown Devanagari defaults to Hindi rather than guessing.
_MARATHI_MARKERS = {
    "आहे", "आहेत", "काय", "कसे", "कसा", "कशी", "मध्ये", "म्हणजे", "मला",
    "तुम्ही", "याचा", "याची", "याचे", "सांग", "करा", "होते", "असते", "साठी",
}
_HINDI_MARKERS = {
    "है", "हैं", "क्या", "कैसे", "क्यों", "में", "मुझे", "आप", "बताओ", "बताइए",
    "करें", "होता", "होती", "के", "का", "की", "से", "और",
}

_SCRIPT_RANGES = (
    ("bn", 0x0980, 0x09FF),
    ("te", 0x0C00, 0x0C7F),
    ("ta", 0x0B80, 0x0BFF),
    ("gu", 0x0A80, 0x0AFF),
    ("kn", 0x0C80, 0x0CFF),
    ("ml", 0x0D00, 0x0D7F),
    ("pa", 0x0A00, 0x0A7F),
    ("or", 0x0B00, 0x0B7F),
    ("as", 0x0980, 0x09FF),
    ("ur", 0x0600, 0x06FF),
)
_HINGLISH_MARKERS = {
    "kya", "hai", "hain", "kaise", "kyu", "kyun", "mujhe", "batao", "samjhao",
    "ka", "ki", "ke", "mein", "me", "aur", "hota", "hoti", "karna", "karo",
    "formula kya", "difference kya", "kitna", "wala", "wali",
}


def _contains_range(text: str, start: int, end: int) -> bool:
    return any(start <= ord(ch) <= end for ch in text)


def detect_language(text: str) -> LanguageInfo:
    raw = (text or "").strip()
    if not raw:
        return LanguageInfo("en", LANGUAGES["en"])

    # Script-based detection is deterministic and local; it makes no LLM/provider call.
    # Assamese shares the Bengali script, so Assamese markers are checked first.
    if _contains_range(raw, 0x0980, 0x09FF):
        words = set(re.findall(r"[\u0980-\u09FF]+", raw))
        assamese_markers = {"নেকি", "কৰা", "কৰিব", "হয়", "হয়", "আপুনি", "মই", "আপোনাৰ", "অসমীয়া"}
        if words & assamese_markers:
            return LanguageInfo("as", LANGUAGES["as"])
        return LanguageInfo("bn", LANGUAGES["bn"])

    for code, start, end in _SCRIPT_RANGES[1:]:
        if _contains_range(raw, start, end):
            return LanguageInfo(code, LANGUAGES[code])

    # Hindi and Marathi both primarily use Devanagari.
    if _contains_range(raw, 0x0900, 0x097F):
        words = set(re.findall(r"[\u0900-\u097F]+", raw))
        mr_score = len(words & _MARATHI_MARKERS)
        hi_score = len(words & _HINDI_MARKERS)
        code = "mr" if mr_score > hi_score else "hi"
        return LanguageInfo(code, LANGUAGES[code])

    # Latin-script Hindi is treated as Hinglish. Require more than one weak
    # marker (or one strong phrase) to avoid classifying normal English that
    # happens to contain words such as "me".
    latin = re.sub(r"[^a-z0-9\s]", " ", raw.lower())
    latin = re.sub(r"\s+", " ", latin).strip()
    words = set(latin.split())
    marker_words = {m for m in _HINGLISH_MARKERS if " " not in m}
    weak_hits = len(words & marker_words)
    strong_phrase = any(" " in m and m in latin for m in _HINGLISH_MARKERS)
    if strong_phrase or weak_hits >= 2 or ("kya" in words and len(words) >= 2):
        return LanguageInfo("hinglish", LANGUAGES["hinglish"])

    return LanguageInfo("en", LANGUAGES["en"])


def language_from_locale(locale: str | None) -> LanguageInfo | None:
    code = LOCALE_TO_LANGUAGE.get(str(locale or "").strip())
    return LanguageInfo(code, LANGUAGES[code]) if code else None


def language_locale(language: LanguageInfo) -> str:
    # Hinglish is rendered as English-locale speech because it uses Latin script;
    # it is not exposed as a separate Indian TTS locale.
    if language.code == "hinglish":
        return "en-IN"
    return f"{language.code}-IN"


def response_instruction(language: LanguageInfo) -> str:
    if language.code == "hinglish":
        return (
            "Reply in natural Hinglish using the Latin/Roman script. Keep common "
            "technical civil-engineering terms in English when that is clearer."
        )
    if language.code == "en":
        return "Reply in English."
    return (
        f"Reply in {language.name}. Keep standard numbers, formulas, symbols, and "
        "technical terms unchanged when translating them would reduce precision."
    )


_LOCALIZED = {
    "empty": {
        "en": "Please enter a BIS, Indian Standards, or civil-engineering question.",
        "hi": "कृपया BIS, भारतीय मानक या सिविल इंजीनियरिंग से संबंधित प्रश्न दर्ज करें।",
        "bn": "অনুগ্রহ করে BIS, ভারতীয় মান বা সিভিল ইঞ্জিনিয়ারিং সম্পর্কিত প্রশ্ন লিখুন।",
        "ta": "BIS, இந்திய தரநிலைகள் அல்லது சிவில் இன்ஜினியரிங் தொடர்பான கேள்வியை உள்ளிடவும்.",
        "mr": "कृपया BIS, भारतीय मानके किंवा सिव्हिल इंजिनिअरिंगशी संबंधित प्रश्न विचारा.",
        "hinglish": "Please BIS, Indian Standards ya civil-engineering se related question poochhiye.",
    },
    "no_reliable_bis": {
        "en": "I couldn't find reliable BIS information for that question.",
        "hi": "मुझे उस प्रश्न के लिए विश्वसनीय BIS जानकारी नहीं मिली।",
        "bn": "এই প্রশ্নের জন্য আমি নির্ভরযোগ্য BIS তথ্য খুঁজে পাইনি।",
        "ta": "அந்தக் கேள்விக்கான நம்பகமான BIS தகவலை நான் கண்டுபிடிக்க முடியவில்லை.",
        "mr": "त्या प्रश्नासाठी मला विश्वसनीय BIS माहिती सापडली नाही.",
        "hinglish": "Mujhe is question ke liye reliable BIS information nahi mili.",
    },
    "ai1_unavailable": {
        "en": "I couldn't generate a grounded BIS answer right now. Please try again later.",
        "hi": "मैं अभी प्रमाण-आधारित BIS उत्तर तैयार नहीं कर सका। कृपया बाद में फिर प्रयास करें।",
        "bn": "আমি এখন প্রমাণভিত্তিক BIS উত্তর তৈরি করতে পারিনি। অনুগ্রহ করে পরে আবার চেষ্টা করুন।",
        "ta": "இப்போது ஆதாரபூர்வமான BIS பதிலை உருவாக்க முடியவில்லை. பின்னர் மீண்டும் முயற்சிக்கவும்.",
        "mr": "मी सध्या पुराव्यावर आधारित BIS उत्तर तयार करू शकलो नाही. कृपया नंतर पुन्हा प्रयत्न करा.",
        "hinglish": "Main abhi grounded BIS answer generate nahi kar paaya. Please baad mein dobara try karein.",
    },
    "ai2_unavailable": {
        "en": "I couldn't generate a reliable answer right now. Please try again or ask a more specific BIS-related question.",
        "hi": "मैं अभी विश्वसनीय उत्तर तैयार नहीं कर सका। कृपया दोबारा प्रयास करें या अधिक स्पष्ट प्रश्न पूछें।",
        "bn": "আমি এখন নির্ভরযোগ্য উত্তর তৈরি করতে পারিনি। আবার চেষ্টা করুন বা আরও নির্দিষ্ট প্রশ্ন করুন।",
        "ta": "இப்போது நம்பகமான பதிலை உருவாக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது இன்னும் குறிப்பான கேள்வியை கேட்கவும்.",
        "mr": "मी सध्या विश्वसनीय उत्तर तयार करू शकलो नाही. कृपया पुन्हा प्रयत्न करा किंवा अधिक स्पष्ट प्रश्न विचारा.",
        "hinglish": "Main abhi reliable answer generate nahi kar paaya. Please dobara try karein ya thoda specific question poochhein.",
    },
}


def localized_message(key: str, language: LanguageInfo) -> str:
    values = _LOCALIZED.get(key, {})
    return values.get(language.code) or values.get("en") or ""
