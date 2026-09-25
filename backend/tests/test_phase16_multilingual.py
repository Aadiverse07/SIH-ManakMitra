from backend.app.services.language import detect_language, response_instruction, language_from_locale, language_locale
from backend.app.services.faq.service import normalize_question, FAQMatcher


def test_detects_six_supported_language_modes():
    assert detect_language("What is concrete mix design?").code == "en"
    assert detect_language("कंक्रीट मिक्स डिजाइन क्या है?").code == "hi"
    assert detect_language("কংক্রিট মিক্স ডিজাইন কী?").code == "bn"
    assert detect_language("கான்கிரீட் கலவை வடிவமைப்பு என்றால் என்ன?").code == "ta"
    assert detect_language("काँक्रीट मिक्स डिझाइन काय आहे?").code == "mr"
    assert detect_language("concrete mix design kya hai?").code == "hinglish"


def test_unicode_normalization_preserves_supported_scripts():
    assert normalize_question("कंक्रीट क्या है?") == "कंक्रीट क्या है"
    assert normalize_question("কংক্রিট কী?") == "কংক্রিট কী"
    assert normalize_question("கான்கிரீட் என்ன?") == "கான்கிரீட் என்ன"


def test_multilingual_exact_faq_can_match_without_ai():
    matcher = FAQMatcher([
        {"q": "बिटुमेन क्या है", "a": "उत्तर", "category": "civil"},
    ])
    match = matcher.match("बिटुमेन क्या है?")
    assert match is not None
    assert match.answer == "उत्तर"
    assert match.confidence == 1.0


def test_response_instruction_keeps_hinglish_in_roman_script():
    instruction = response_instruction(detect_language("formula kya hai"))
    assert "Hinglish" in instruction
    assert "Latin/Roman" in instruction


def test_voice_language_locales_cover_supported_indian_languages():
    locales = ["en-IN", "hi-IN", "bn-IN", "te-IN", "mr-IN", "ta-IN", "gu-IN",
               "kn-IN", "ml-IN", "pa-IN", "or-IN", "as-IN", "ur-IN"]
    for locale in locales:
        language = language_from_locale(locale)
        assert language is not None
        assert language_locale(language) == locale


def test_detects_additional_indian_scripts_without_provider_calls():
    assert detect_language("BIS అంటే ఏమిటి?").code == "te"
    assert detect_language("BIS શું છે?").code == "gu"
    assert detect_language("BIS ಎಂದರೇನು?").code == "kn"
    assert detect_language("BIS എന്താണ്?").code == "ml"
    assert detect_language("BIS ਕੀ ਹੈ?").code == "pa"
    assert detect_language("BIS କ'ଣ?").code == "or"
    assert detect_language("BIS কি?").code == "bn"  # Shared Bengali/Assamese script is ambiguous without provider locale.
    assert language_from_locale("as-IN").code == "as"
    assert detect_language("BIS کیا ہے؟").code == "ur"
