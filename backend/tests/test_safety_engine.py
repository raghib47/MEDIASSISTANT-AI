"""Tests for the deterministic emergency rules (English + Bangla + negation + context)."""
import pytest

from app.safety_engine.rules import build_emergency_response, check_emergency


def ids(text: str) -> set[str]:
    return set(check_emergency(text).rule_ids)


# ---- English emergencies -------------------------------------------------------------
@pytest.mark.parametrize(
    "text, expected",
    [
        ("I have severe chest pain and my left arm feels numb", "chest_pain"),
        ("I think I'm having a heart attack", "chest_pain"),
        ("I can't breathe", "breathing_difficulty"),
        ("He is having difficulty breathing", "breathing_difficulty"),
        ("My father is unconscious", "unconsciousness"),
        ("She passed out and won't wake up", "unconsciousness"),
        ("The bleeding won't stop", "severe_bleeding"),
        ("He is coughing up blood", "severe_bleeding"),
        ("His face is drooping and his speech is slurred", "stroke_signs"),
        ("My brother is having a seizure", "seizure"),
        ("My child swallowed bleach", "poisoning_overdose"),
        ("I want to kill myself", "self_harm_crisis"),
    ],
)
def test_english_emergencies(text, expected):
    result = check_emergency(text)
    assert result.is_emergency
    assert expected in result.rule_ids


# ---- Bangla emergencies --------------------------------------------------------------
@pytest.mark.parametrize(
    "text, expected",
    [
        ("আমার বুকে প্রচণ্ড ব্যথা হচ্ছে", "chest_pain"),
        ("শ্বাস নিতে কষ্ট হচ্ছে", "breathing_difficulty"),
        ("আমি শ্বাস নিতে পারছি না", "breathing_difficulty"),
        ("বাবা অজ্ঞান হয়ে গেছেন", "unconsciousness"),
        ("রক্ত পড়া বন্ধ হচ্ছে না", "severe_bleeding"),
        ("মায়ের মুখ বেঁকে গেছে এবং কথা জড়িয়ে যাচ্ছে", "stroke_signs"),
        ("রোগীর খিঁচুনি হচ্ছে", "seizure"),
        ("সে বিষ খেয়েছে", "poisoning_overdose"),
        ("আমি আত্মহত্যা করতে চাই", "self_harm_crisis"),
    ],
)
def test_bangla_emergencies(text, expected):
    result = check_emergency(text)
    assert result.is_emergency
    assert expected in result.rule_ids


# ---- Negation ------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "I do not have chest pain",
        "No chest pain, just a mild headache",
        "I have no difficulty breathing",
        "He is fine, without chest pain or shortness of breath",
        "I have no fever, cough or chest pain",
        "I'm not suicidal",
        "আমার বুকে ব্যথা নেই",
        "শ্বাসকষ্ট হচ্ছে না",
        "আমি মরতে চাই না",
    ],
)
def test_negated_symptoms_are_not_emergencies(text):
    assert not check_emergency(text).is_emergency, text


@pytest.mark.parametrize(
    "text, expected, absent",
    [
        ("I don't have chest pain but I can't breathe", "breathing_difficulty", "chest_pain"),
        ("বুকে ব্যথা নেই কিন্তু শ্বাসকষ্ট হচ্ছে", "breathing_difficulty", "chest_pain"),
        ("I don't feel well and I can't breathe", "breathing_difficulty", None),
    ],
)
def test_negation_is_scoped_to_its_own_symptom(text, expected, absent):
    found = ids(text)
    assert expected in found
    if absent:
        assert absent not in found


# ---- Things that must NOT be mistaken for negation (safety-first) --------------------
@pytest.mark.parametrize(
    "text",
    [
        "No, I'm having chest pain",
        "I'm not sure if this chest pain is serious",
        "I don't know what's wrong, I can't breathe",
    ],
)
def test_false_negation_does_not_hide_real_emergencies(text):
    assert check_emergency(text).is_emergency, text


# ---- Informational questions vs. personal situations -----------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "What are the symptoms of a stroke?",
        "What causes chest pain?",
        "স্ট্রোকের লক্ষণ কী?",
    ],
)
def test_general_questions_are_not_flagged(text):
    result = check_emergency(text)
    assert not result.is_emergency
    assert result.informational_question


@pytest.mark.parametrize(
    "text",
    [
        "What should I do? My dad has chest pain",
        "বুকে খুব ব্যথা হচ্ছে, কারণ বুঝতে পারছি না",
    ],
)
def test_personal_situations_with_question_words_still_flag(text):
    assert check_emergency(text).is_emergency, text


def test_self_harm_is_never_downgraded_as_informational():
    assert check_emergency("What is suicide?").is_emergency


# ---- Ordinary health questions ---------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    ["What are common symptoms of dehydration?", "ডায়াবেটিসের সাধারণ লক্ষণ কী?", "How can I sleep better?", ""],
)
def test_ordinary_questions_are_not_emergencies(text):
    assert not check_emergency(text).is_emergency


# ---- Reply builder ---------------------------------------------------------------------
def test_reply_is_localized_and_contains_number():
    en = build_emergency_response(check_emergency("I can't breathe"), "en", "999")
    bn = build_emergency_response(check_emergency("আমি শ্বাস নিতে পারছি না"), "bn", "999")
    assert "999" in en and "emergency" in en.lower()
    assert "৯৯৯" in bn and "জরুরি" in bn


def test_self_harm_reply_has_no_medical_checklist():
    reply = build_emergency_response(check_emergency("I want to kill myself"), "en", "999")
    assert "999" in reply and "medical emergency" not in reply.lower()
