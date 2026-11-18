"""Deterministic emergency warning-sign detection (English + Bangla).

!!! PROTOTYPE - NOT CLINICALLY VALIDATED !!!
These are hand-written pattern rules for a hackathon demo. They have NOT been reviewed by
medical professionals and will miss some emergencies (false negatives) and flag some
non-emergencies (false positives). The design deliberately leans towards over-warning.
A real deployment needs clinical review, a much larger test set, and ongoing audit.

How it works
------------
1. Normalise the text (Unicode NFC, strip zero-width chars, lower-case, straighten quotes).
2. Skip purely *informational* questions ("What are the symptoms of a stroke?") when there is
   no sign the user or someone near them is affected (no personal pronouns, no ongoing-
   verb forms). Mental-health crisis rules are never skipped this way.
3. Match regex patterns per rule, in English and Bangla (any language mix is handled).
4. Negation handling:
   * English: negation words in the same clause, shortly BEFORE the match
     ("no chest pain", "without difficulty breathing"). "No, I have chest pain" and
     "not sure if this chest pain is serious" are NOT treated as negated.
   * Bangla: negation comes AFTER the symptom ("বুকে ব্যথা নেই", "শ্বাসকষ্ট হচ্ছে না").
5. Build a fixed, pre-written safety reply (no LLM involved, so it is instant and reliable).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

SAFETY_ENGINE_VERSION = "0.1-prototype"

Category = Literal["medical", "mental_health"]
Language = Literal["en", "bn"]


# --------------------------------------------------------------------------------------
# Rule definitions
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class EmergencyRule:
    rule_id: str
    category: Category
    label_en: str
    label_bn: str
    patterns_en: tuple[str, ...] = ()
    patterns_bn: tuple[str, ...] = ()
    # False = always fire, even for "what is ...?" style questions
    allow_informational_downgrade: bool = True


RULES: tuple[EmergencyRule, ...] = (
    EmergencyRule(
        rule_id="chest_pain",
        category="medical",
        label_en="chest pain or pressure",
        label_bn="বুকে ব্যথা বা চাপ",
        patterns_en=(
            r"\bchest\s+(?:pain|pains|pressure|tightness|discomfort)\b",
            r"\b(?:tightness|pressure|pain)\s+in\s+(?:my|the|his|her)\s+chest\b",
            r"\bheart\s+attack\b",
            r"\bcrushing\s+(?:pain|pressure)\b",
            r"\bpain\s+(?:radiating|spreading|going)\s+(?:to|down)\s+(?:my|the|his|her)\s+(?:left\s+)?(?:arm|jaw)\b",
        ),
        patterns_bn=(
            r"বুকে\s*(?:খুব\s*|প্রচণ্ড\s*|প্রচন্ড\s*|তীব্র\s*|অসহ্য\s*|হঠাৎ\s*)?(?:ব্যথা|ব্যাথা|যন্ত্রণা|চাপ)",
            r"বুক\s*(?:ব্যথা|ব্যাথা|চেপে\s*ধ)",
            r"হার্ট\s*(?:অ্যাটাক|এটাক|আটাক|অ্যাটেক|এটেক)",
            r"হৃদরোগে\s*আক্রান্ত",
        ),
    ),
    EmergencyRule(
        rule_id="breathing_difficulty",
        category="medical",
        label_en="difficulty breathing",
        label_bn="শ্বাসকষ্ট",
        patterns_en=(
            r"\b(?:difficulty|trouble|struggling|problems?)\s+(?:in\s+)?breathing\b",
            r"\b(?:can't|cannot|can\s+not|unable\s+to|not\s+able\s+to|couldn't|hard\s+to|hardly\s+able\s+to|struggling\s+to)\s+(?:\w+\s+){0,2}?breathe?\b(?!\s+through\s+(?:my|the|his|her)\s+nose)",
            r"\bshort(?:ness)?\s+of\s+breath\b",
            r"\bgasping\s+for\s+(?:air|breath)\b",
            r"\b(?:stopped|not)\s+breathing\b",
            r"\bchoking\b",
            r"\bcan't\s+get\s+(?:enough\s+)?(?:air|breath)\b",
            r"\b(?:blue|bluish|purple)\s+(?:lips|face)\b",
        ),
        patterns_bn=(
            r"শ্বাস\s*কষ্ট",
            r"(?:শ্বাস|স্বাস|নিঃশ্বাস|নিশ্বাস|নিঃস্বাস|দম)\s*(?:নিতে|ফেলতে)?\s*(?:খুব\s*)?(?:কষ্ট|পারছি\s*না|পারছে\s*না|পারছেন\s*না|পারি\s*না|পারে\s*না|পারছিনা|পারছেনা)",
            r"দম\s*(?:বন্ধ|আটকে)",
            r"(?:নিঃশ্বাস|নিশ্বাস|শ্বাস)\s*বন্ধ",
            r"শ্বাস\s*নিচ্ছে\s*না|শ্বাস\s*নিচ্ছেন\s*না",
            r"ঠোঁট\s*(?:নীল|নীলচে)",
        ),
    ),
    EmergencyRule(
        rule_id="unconsciousness",
        category="medical",
        label_en="loss of consciousness or being unresponsive",
        label_bn="অজ্ঞান হওয়া বা সাড়া না দেওয়া",
        patterns_en=(
            r"\bunconscious(?:ness)?\b",
            r"\bunresponsive\b",
            r"\b(?:passed|passing)\s+out\b",
            r"\bfaint(?:ed|ing)\b",
            r"\bcollaps(?:ed|ing)\b",
            r"\bblack(?:ed|ing)\s+out\b",
            r"\b(?:won't|will\s+not|can't|cannot|not)\s+(?:wake\s+up|waking\s+up|responding\s+to\s+(?:me|anything|my\s+voice|touch))\b",
            r"\bnot\s+responsive\b",
            r"\b(?:lost|loss\s+of)\s+consciousness\b",
        ),
        patterns_bn=(
            r"অজ্ঞান\s*(?:হয়ে|হয়|হচ্ছে|হইয়া|হচ্ছেন|হতে)",
            r"জ্ঞান\s*(?:হারিয়ে|নেই|হারাচ্ছে|ফিরছে\s*না|ফেরেনি|ফেরে\s*না)",
            r"অচেতন",
            r"সাড়া\s*(?:দিচ্ছে|দিচ্ছেন|দিচ্ছি)\s*না",
            r"সাড়া\s*নেই",
            r"চেতনা\s*(?:নেই|হারি)",
            r"মূর্ছা|মুর্ছা",
        ),
    ),
    EmergencyRule(
        rule_id="severe_bleeding",
        category="medical",
        label_en="severe bleeding",
        label_bn="তীব্র রক্তপাত",
        patterns_en=(
            r"\b(?:severe|heavy|massive|profuse|serious|excessive|uncontrolled|uncontrollable)\s+(?:bleeding|blood\s+loss|haemorrhage|hemorrhage)\b",
            r"\bbleeding\s+(?:heavily|profusely|a\s+lot|badly|nonstop|non-stop|non\s+stop|uncontrollably|won't\s+stop|will\s+not\s+stop|through)\b",
            r"\b(?:won't|will\s+not|can't|cannot|not)\s+(?:stop|stopping)\s+bleeding\b",
            r"\b(?:blood|bleeding)\s+(?:is\s+)?(?:won't|will\s+not|not)\s+(?:stop|stopping)\b",
            r"\b(?:coughing|coughed|vomiting|vomited|throwing\s+up|spitting)\s+(?:up\s+)?blood\b",
            r"\blosing\s+(?:a\s+lot\s+of\s+|too\s+much\s+)?blood\b",
        ),
        patterns_bn=(
            r"(?:প্রচুর|অনেক|ভীষণ|খুব|তীব্র|অতিরিক্ত|অনবরত)\s*(?:রক্তপাত|রক্তক্ষরণ|রক্ত\s*(?:পড়ছে|পড়ে|যাচ্ছে|বের\s*হচ্ছে|ঝরছে))",
            r"রক্ত\s*(?:পড়া\s*)?(?:বন্ধ\s*হচ্ছে\s*না|থামছে\s*না|থামে\s*না|বন্ধ\s*হয়\s*না)",
            r"রক্ত\s*বমি|বমিতে\s*রক্ত|বমির\s*(?:সাথে|সঙ্গে)\s*রক্ত|রক্ত\s*কাশি|রক্ত\s*কাশ|কাশির\s*সাথে\s*রক্ত|কাশিতে\s*রক্ত",
        ),
    ),
    EmergencyRule(
        rule_id="stroke_signs",
        category="medical",
        label_en="possible stroke signs",
        label_bn="স্ট্রোকের সম্ভাব্য লক্ষণ",
        patterns_en=(
            r"\bstroke\b",
            r"\b(?:face|facial|mouth|smile)\s+(?:is\s+)?(?:droop\w*|drop\w*|sagg\w*|numb\w*|crooked|uneven)\b",
            r"\bdroop(?:ing|y)\s+(?:face|mouth|smile)\b",
            r"\bslurr(?:ed|ing)\s+(?:of\s+)?(?:speech|words)\b",
            r"\bspeech\s+(?:is\s+)?slurred\b",
            r"\b(?:can't|cannot|unable\s+to)\s+(?:speak|talk)\b",
            r"\bsudden(?:ly)?\s+(?:\w+\s+){0,2}?(?:weakness|numbness|paralysis|confusion|loss\s+of\s+vision|vision\s+loss|trouble\s+(?:seeing|speaking|walking))\b",
            r"\b(?:weakness|numbness)\s+(?:on|in)\s+one\s+side\b",
            r"\bone\s+side\s+of\s+(?:the\s+|my\s+|his\s+|her\s+)?(?:body|face)\s+(?:is\s+)?(?:weak|numb|paralys\w*|droop\w*)\b",
            r"\bsudden\s+(?:severe|worst|intense)\s+headache\b",
            r"\bworst\s+headache\s+of\s+(?:my|his|her)\s+life\b",
        ),
        patterns_bn=(
            r"স্ট্রোক",
            r"মুখ\s*(?:বেঁকে|বেকে|বাঁকা|বাঁকিয়ে)",
            r"কথা\s*(?:জড়িয়ে|অস্পষ্ট|বলতে\s*পারছে\s*না|বলতে\s*পারছি\s*না|বলতে\s*পারছেন\s*না)",
            r"(?:এক\s*পাশ|একপাশ|এক\s*দিক)\w*\s*(?:অবশ|দুর্বল|প্যারালাইসিস|অসাড়)",
            r"হঠাৎ\s*(?:[^\s]+\s+){0,2}?(?:অবশ|অসাড়|দৃষ্টি\s*হারি|দেখতে\s*পাচ্ছি\s*না|কথা\s*বলতে\s*পারছে\s*না)",
        ),
    ),
    EmergencyRule(
        rule_id="seizure",
        category="medical",
        label_en="a seizure or convulsions",
        label_bn="খিঁচুনি",
        patterns_en=(
            r"\bseizures?\b",
            r"\bconvuls\w+\b",
            r"\bhaving\s+(?:a\s+)?(?:fit|fits)\b",
            r"\bepileptic\s+(?:fit|attack)\b",
            r"\bshaking\s+uncontrollably\b",
            r"\bfoaming\s+(?:at|from)\s+(?:the\s+)?mouth\b",
        ),
        patterns_bn=(
            r"খিঁচুনি|খিচুনি|খিচুনী|খিঁচুনী",
            r"মৃগী",
            r"তড়কা",
            r"ফিট\s*(?:হয়ে|হচ্ছে|হয়েছে)",
            r"মুখ\s*দিয়ে\s*ফেনা",
        ),
    ),
    EmergencyRule(
        rule_id="poisoning_overdose",
        category="medical",
        label_en="possible poisoning or overdose",
        label_bn="বিষ খাওয়া বা ওভারডোজের সম্ভাবনা",
        patterns_en=(
            r"\boverdos\w*\b",
            r"\bpoisoned\b",
            r"\b(?:swallowed|drank|ingested|ate|consumed|took)\s+(?:\w+\s+){0,3}?(?:poison|pesticide|bleach|kerosene|insecticide)\b",
            r"\btook\s+too\s+many\s+(?:pills|tablets|medicines?|medications?)\b",
        ),
        patterns_bn=(
            r"বিষ\s*(?:খেয়ে|খেয়েছে|খেয়েছি|পান|খাইয়ে)",
            r"কীটনাশক\s*(?:খেয়ে|খেয়েছে|খেয়েছি|পান)",
            r"ইঁদুরের\s*বিষ",
            r"ওভার\s*ডোজ",
            r"(?:অতিরিক্ত|অনেক)\s*(?:ঘুমের\s*)?(?:ওষুধ|ট্যাবলেট|বড়ি)\s*খে",
        ),
    ),
    EmergencyRule(
        rule_id="severe_allergic_reaction",
        category="medical",
        label_en="a possible severe allergic reaction",
        label_bn="তীব্র অ্যালার্জিক প্রতিক্রিয়ার সম্ভাবনা",
        patterns_en=(
            r"\banaphyla\w+\b",
            r"\bsevere\s+allergic\s+reaction\b",
            r"\b(?:throat|tongue|lips?|face)\s+(?:is\s+|are\s+|feels?\s+)?(?:swelling|swollen|closing)\b",
            r"\bswelling\s+(?:of\s+|in\s+)?(?:the\s+|my\s+|his\s+|her\s+)?(?:throat|tongue)\b",
        ),
        patterns_bn=(
            r"অ্যানাফাইল\w*|এনাফাইল\w*",
            r"তীব্র\s*অ্যালার্জি",
            r"গলা\s*(?:ফুলে|বন্ধ\s*হয়ে|আটকে)",
            r"জিহ্বা\s*ফুলে|জিভ\s*ফুলে|ঠোঁট\s*ফুলে",
        ),
    ),
    EmergencyRule(
        rule_id="snakebite",
        category="medical",
        label_en="a possible snakebite",
        label_bn="সাপে কামড়ানোর সম্ভাবনা",
        patterns_en=(
            r"\bsnake\s*bit(?:e|ten)\b",
            r"\bbitten\s+by\s+(?:a\s+)?snake\b",
        ),
        patterns_bn=(
            r"সাপে\s*(?:কেটেছে|কামড়েছে|কাটা|কেটে)",
            r"সাপের\s*কামড়",
        ),
    ),
    EmergencyRule(
        rule_id="self_harm_crisis",
        category="mental_health",
        label_en="thoughts of harming yourself",
        label_bn="নিজের ক্ষতি করার চিন্তা",
        patterns_en=(
            r"\bsuicid(?:e|al)\b",
            r"\b(?:kill|hurt|harm)\s+(?:myself|my\s*self)\b",
            r"\b(?:want|wanna|going|plan(?:ning)?|thinking\s+(?:of|about))\s+(?:to\s+)?(?:die|end\s+it\s+all|end\s+my\s+life)\b",
            r"\bend\s+my\s+life\b",
            r"\bdon't\s+want\s+to\s+(?:live|be\s+alive|exist)\b",
            r"\bbetter\s+off\s+(?:dead|without\s+me)\b",
            r"\bself[-\s]?harm\b",
            r"\bcut(?:ting)?\s+myself\b",
        ),
        patterns_bn=(
            r"আত্মহত্যা|আত্মঘাতী",
            r"মরে\s*যেতে\s*(?:ইচ্ছে|ইচ্ছা|চাই)",
            r"মরতে\s*(?:ইচ্ছে|ইচ্ছা|চাই)",
            r"নিজেকে\s*(?:শেষ|মেরে|কেটে|আঘাত)",
            r"বাঁচতে\s*(?:ইচ্ছে|ইচ্ছা)\s*করছে\s*না|বাঁচতে\s*চাই\s*না|বাঁচতে\s*ইচ্ছা\s*করে\s*না",
            r"জীবন\s*শেষ\s*করে",
            r"নিজের\s*ক্ষতি\s*করতে",
        ),
        allow_informational_downgrade=False,
    ),
)

_RULES_BY_ID = {r.rule_id: r for r in RULES}


def _nfc(pattern: str) -> str:
    # Bangla letters like য় can be typed in composed or decomposed form; NFC makes both match.
    return unicodedata.normalize("NFC", pattern)


def _compile(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(_nfc(p), re.IGNORECASE) for p in patterns)


_COMPILED = tuple((rule, _compile(rule.patterns_en), _compile(rule.patterns_bn)) for rule in RULES)


# --------------------------------------------------------------------------------------
# Text normalisation
# --------------------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u200c", "").replace("\u200d", "")  # zero-width (non-)joiners
    for fancy, plain in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"')):
        text = text.replace(fancy, plain)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


# --------------------------------------------------------------------------------------
# Negation handling
# --------------------------------------------------------------------------------------
_SUBJECTS = r"(?:i|he|she|they|we|it|my|his|her|their|now|also|still)"
# Boundaries that end the scope of a negation (English)
_CLAUSE_SPLIT_EN = re.compile(
    r"[.;!?:\n]"
    r"|\b(?:but|however|although|though|except|yet)\b"
    rf"|\band\s+(?={_SUBJECTS}\b)"
    rf"|,\s*(?={_SUBJECTS}\b)"
)
# Negators. "no," (an answer to a question) and "not sure/only/just..." are NOT negations of the symptom.
_NEG_EN = re.compile(
    r"\b(?:no|not|never|without|denies|denied|nor|neither|negative\s+for|free\s+of|ruled\s+out|"
    r"isn't|aren't|wasn't|weren't|don't|doesn't|didn't|haven't|hasn't|hadn't)\b"
    r"(?!\s*,)"
    r"(?!\s+(?:sure|certain|only|just|know|really|quite|even|think|if|whether))"
)
_NEG_WINDOW_WORDS = 5

# Bangla: negation follows the symptom, within a short span, before any conjunction/punctuation.
_BN_CUT = re.compile(r"[।.,;!?\n]|(?:^|\s)(?:কিন্তু|তবে|এবং|আর|ও|আবার|অথচ|যদিও)(?:\s|$)")
_NEG_BN = re.compile(
    r"^\s*(?:[^\s]+\s+){0,2}?"
    r"(?:নেই|নাই|নয়|হয়নি|হয়\s*নি|হচ্ছে\s*না|হয়\s*না|হচ্ছিল\s*না|ছিল\s*না|ছিলো\s*না|"
    r"করছে\s*না|করছি\s*না|দেখা\s*যায়নি)"
)
_NEG_BN_DIRECT = re.compile(r"^\s*না(?=\s|$)")  # e.g. "মরতে চাই না"


def _is_negated_en(norm: str, match_start: int) -> bool:
    clause = _CLAUSE_SPLIT_EN.split(norm[:match_start])[-1]
    window = " ".join(clause.split()[-_NEG_WINDOW_WORDS:])
    return bool(_NEG_EN.search(window))


def _is_negated_bn(norm: str, match_end: int) -> bool:
    tail = norm[match_end : match_end + 60]
    cut = _BN_CUT.search(tail)
    if cut:
        tail = tail[: cut.start()]
    return bool(_NEG_BN_DIRECT.match(tail) or _NEG_BN.match(tail))


# --------------------------------------------------------------------------------------
# "Informational question" detection
# --------------------------------------------------------------------------------------
_INFO_EN = re.compile(
    r"^(?:please\s+|can\s+you\s+|could\s+you\s+)?"
    r"(?:what(?:'s|\s+is|\s+are|\s+causes?|\s+does|\s+do)\b"
    r"|how\s+(?:to|can\s+i|do\s+i|can\s+we)\s+(?:prevent|avoid|reduce)\b"
    r"|define\b|definition\s+of\b|meaning\s+of\b|explain\b|tell\s+me\s+about\b|describe\b"
    r"|symptoms?\s+of\b|signs?\s+of\b|causes?\s+of\b|why\s+(?:does|do|is|are)\b)"
)
_PERSONAL_EN = re.compile(
    r"\b(?:i|i'm|i've|i'd|i'll|me|my|mine|myself|he|he's|she|she's|his|her|they|them|their|"
    r"someone|somebody|patient|mom|mum|dad|mother|father|wife|husband|baby|child|kid|son|"
    r"daughter|friend|brother|sister|grandma|grandpa|grandmother|grandfather|uncle|aunt|"
    r"now|help|urgent|urgently|currently)\b"
)
_INFO_BN = re.compile(
    r"(?:লক্ষণ|কারণ|প্রতিরোধ|সংজ্ঞা)\s*(?:কী|কি|কিছু|গুলো|সমূহ|সম্পর্কে)"
    r"|কাকে\s*বলে|মানে\s*(?:কী|কি)|(?:কী|কি)\s*কারণে"
)
_PERSONAL_BN = re.compile(
    r"(?:^|\s)(?:আমি|আমার|আমাকে|আমরা|আমাদের|সে|তার|তাকে|তিনি|উনি|ওনার|বাবা|বাবার|বাবাকে|মা|মায়ের|মাকে|"
    r"আব্বু|আব্বুর|আম্মু|আম্মুর|ভাই|ভাইয়ের|বোন|বোনের|স্ত্রী|স্ত্রীর|স্বামী|স্বামীর|বাচ্চা|বাচ্চার|শিশু|শিশুর|"
    r"ছেলে|ছেলের|মেয়ে|মেয়ের|রোগী|রোগীর|এখন|এখনই|সাহায্য|বন্ধু|বন্ধুর|দাদা|দাদার|দাদি|দাদির|নানা|নানার|"
    r"নানি|নানির|চাচা|মামা|খালা|ফুফু|কেউ|একজন)(?=\s|$|[।,.?!])"
)
_ONGOING_BN = re.compile(r"(?:হচ্ছে|করছে|করছি|হয়েছে|পারছি|পারছে|পারছেন|যাচ্ছে|গেছে|গেছেন)")


def _is_informational(norm: str) -> bool:
    """True only for general knowledge questions with no sign that someone is affected now."""
    if _INFO_EN.match(norm) and not _PERSONAL_EN.search(norm) and not _PERSONAL_BN.search(norm):
        return True
    if (
        _INFO_BN.search(norm)
        and not _PERSONAL_BN.search(norm)
        and not _PERSONAL_EN.search(norm)
        and not _ONGOING_BN.search(norm)
    ):
        return True
    return False


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SafetyResult:
    is_emergency: bool
    rule_ids: tuple[str, ...] = ()
    categories: tuple[Category, ...] = ()
    informational_question: bool = False


def _rule_fires(norm: str, en_rx: tuple[re.Pattern[str], ...], bn_rx: tuple[re.Pattern[str], ...]) -> bool:
    for rx in en_rx:
        for m in rx.finditer(norm):
            if not _is_negated_en(norm, m.start()):
                return True
    for rx in bn_rx:
        for m in rx.finditer(norm):
            if not _is_negated_bn(norm, m.end()):
                return True
    return False


def check_emergency(text: str) -> SafetyResult:
    """Scan one user message for emergency warning signs. Pure function, no I/O."""
    norm = normalize_text(text)
    if not norm:
        return SafetyResult(False)

    informational = _is_informational(norm)
    rule_ids: list[str] = []
    categories: list[Category] = []

    for rule, en_rx, bn_rx in _COMPILED:
        if informational and rule.allow_informational_downgrade:
            continue
        if _rule_fires(norm, en_rx, bn_rx):
            rule_ids.append(rule.rule_id)
            if rule.category not in categories:
                categories.append(rule.category)

    return SafetyResult(
        is_emergency=bool(rule_ids),
        rule_ids=tuple(rule_ids),
        categories=tuple(categories),
        informational_question=informational,
    )


# --------------------------------------------------------------------------------------
# Pre-written safety replies (never generated by an LLM)
# --------------------------------------------------------------------------------------
_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _medical_reply(labels: list[str], lang: Language, number: str) -> str:
    joined = ", ".join(labels)
    if lang == "bn":
        num = number.translate(_BN_DIGITS)
        return (
            "⚠️ **এটি জরুরি চিকিৎসা পরিস্থিতি হতে পারে।**\n\n"
            f"আপনি যা লিখেছেন ({joined}) তা গুরুতর অসুস্থতার লক্ষণ হতে পারে। "
            "অনুগ্রহ করে **এখনই** জরুরি চিকিৎসা সহায়তা নিন:\n\n"
            f"- এখনই জরুরি নম্বরে (**{num}**) কল করুন অথবা নিকটস্থ হাসপাতালের জরুরি বিভাগে যান।\n"
            "- আশেপাশে কেউ থাকলে তাকে আপনার সাথে থাকতে বলুন। মাথা ঘুরলে বা খুব অসুস্থ বোধ করলে নিজে গাড়ি চালাবেন না।\n"
            "- কেউ অজ্ঞান হয়ে গেলে বা শ্বাস না নিলে সঙ্গে সঙ্গে জরুরি সেবাকে জানান এবং তাদের নির্দেশ অনুসরণ করুন।\n"
            "- চ্যাটবটের উত্তরের জন্য অপেক্ষা করবেন না।\n\n"
            "আমি একটি এআই সহকারী, ডাক্তার নই। এই স্বয়ংক্রিয় সতর্কতা একটি প্রোটোটাইপ নিরাপত্তা পরীক্ষা, যা এখনো চিকিৎসকদের দ্বারা যাচাই করা হয়নি।"
        )
    return (
        "⚠️ **This may be a medical emergency.**\n\n"
        f"What you described ({joined}) can be a sign of a serious condition. "
        "Please get urgent medical help **right now**:\n\n"
        f"- Call your local emergency number immediately (**{number}**) or go to the nearest hospital emergency department.\n"
        "- If someone is with you, ask them to stay with you. If you feel faint or very unwell, do not drive yourself.\n"
        "- If a person is unconscious or not breathing, tell the emergency operator straight away and follow their instructions.\n"
        "- Please don't wait for an online chatbot's reply.\n\n"
        "I'm an AI assistant, not a doctor. This automatic warning is a prototype safety check that has not been clinically validated."
    )


def _mental_health_reply(lang: Language, number: str) -> str:
    if lang == "bn":
        num = number.translate(_BN_DIGITS)
        return (
            "আপনি যে কষ্টের মধ্য দিয়ে যাচ্ছেন তা শুনে আমি দুঃখিত। এই মুহূর্তে আপনার নিরাপত্তাই সবচেয়ে গুরুত্বপূর্ণ।\n\n"
            f"যদি আপনি নিজের ক্ষতি করার ঝুঁকিতে থাকেন বা এখনই বিপদে থাকেন, অনুগ্রহ করে এখনই জরুরি নম্বরে (**{num}**) কল করুন "
            "অথবা নিকটস্থ হাসপাতালে যান। বিশ্বাসের কোনো মানুষকে জানান এবং তাকে আপনার পাশে থাকতে বলুন।\n\n"
            "আপনাকে একা এটি সামলাতে হবে না। আমি একটি এআই এবং সংকটকালীন সেবা দিতে পারি না, কিন্তু প্রশিক্ষিত পেশাদাররা পারেন।"
        )
    return (
        "I'm really sorry you're going through this. Your safety matters most right now.\n\n"
        f"If you might act on thoughts of harming yourself, or you're in immediate danger, please call your local emergency number now (**{number}**) "
        "or go to the nearest hospital. Please also reach out to someone you trust and ask them to stay with you.\n\n"
        "You don't have to handle this alone. I'm an AI and can't provide crisis care, but trained professionals can."
    )


def build_emergency_response(result: SafetyResult, lang: Language, emergency_number: str) -> str:
    """Build the fixed safety reply for a positive SafetyResult."""
    parts: list[str] = []
    medical_labels = [
        (_RULES_BY_ID[r].label_bn if lang == "bn" else _RULES_BY_ID[r].label_en)
        for r in result.rule_ids
        if _RULES_BY_ID[r].category == "medical"
    ]
    if medical_labels:
        parts.append(_medical_reply(medical_labels, lang, emergency_number))
    if "mental_health" in result.categories:
        parts.append(_mental_health_reply(lang, emergency_number))
    return "\n\n".join(parts)
