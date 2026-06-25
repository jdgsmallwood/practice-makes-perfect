TRACK_CHOICES = [
    ("single", "Single Tongue"),
    ("double", "Double Tongue"),
    ("full",   "Full Session (ST + DT)"),
]

# Each exercise: id, name, track, cue, bpm_default, bpm_label, subdivision, rating_question
# subdivision: 1=quarter notes, 2=eighths, 4=sixteenths
EXERCISES = {
    "ST_1": {
        "id":              "ST_1",
        "name":            "Air Only",
        "track":           "single",
        "cue":             "Air is the engine; tongue is just a valve. Let air pressure alone start the note. No tongue at all — let the air 'pop' the note open.",
        "bpm_default":     60,
        "bpm_label":       "60 bpm — whole notes",
        "subdivision":     1,
        "rating_question": "How clean was the air attack?",
    },
    "ST_2": {
        "id":              "ST_2",
        "name":            "Ghost Touch",
        "track":           "single",
        "cue":             "Tongue tip barely grazes behind the upper teeth then releases immediately. Say 'du' — not 'tu'. Interrupt the air stream; don't push it.",
        "bpm_default":     60,
        "bpm_label":       "60–72 bpm — quarter notes",
        "subdivision":     1,
        "rating_question": "How light was the tongue contact?",
    },
    "ST_3": {
        "id":              "ST_3",
        "name":            "Whisper Tongue",
        "track":           "single",
        "cue":             "Tongue quarter notes at pp dynamic. Harsh or spitty attacks at this volume mean too much tongue. Goal: each attack clear but whisper-soft.",
        "bpm_default":     72,
        "bpm_label":       "72 bpm — quarter notes, pp dynamic",
        "subdivision":     1,
        "rating_question": "How clean and soft were the attacks?",
    },
    "ST_4": {
        "id":              "ST_4",
        "name":            "Steady Eighths",
        "track":           "single",
        "cue":             "Every eighth note should have identical weight. If downbeats sound louder, lighten the tongue on every note — not just the offbeats.",
        "bpm_default":     80,
        "bpm_label":       "80–100 bpm — even eighth notes",
        "subdivision":     2,
        "rating_question": "How even was the weight of each note?",
    },
    "ST_5": {
        "id":              "ST_5",
        "name":            "Speed Ladder",
        "track":           "single",
        "cue":             "Start slower than you think you need to. Raise tempo by 4 bpm each pass. Speed comes from relaxation — the moment evenness suffers, hold that tempo.",
        "bpm_default":     72,
        "bpm_label":       "72–120 bpm — build in small steps",
        "subdivision":     2,
        "rating_question": "How even at your highest clean tempo?",
    },
    "DT_1": {
        "id":              "DT_1",
        "name":            "Ku Only",
        "track":           "double",
        "cue":             "Use only the back tongue: 'ku-ku-ku'. Try 'guh' if ku is unclear. The ku must be as clear and present as your regular tu before combining them.",
        "bpm_default":     60,
        "bpm_label":       "60 bpm — back tongue isolation",
        "subdivision":     1,
        "rating_question": "How clear was the ku articulation?",
    },
    "DT_2": {
        "id":              "DT_2",
        "name":            "Even Pairs",
        "track":           "double",
        "cue":             "Alternate tu-ku slowly and listen: is tu noticeably louder? Goal is identical weight on both. Try 'did-dle' or 'da-ga' if tu-ku feels uneven.",
        "bpm_default":     72,
        "bpm_label":       "72–80 bpm — tu-ku pairs",
        "subdivision":     2,
        "rating_question": "How matched were tu and ku?",
    },
    "DT_3": {
        "id":              "DT_3",
        "name":            "Scale Flow",
        "track":           "double",
        "cue":             "Run a scale or arpeggio in eighth-note double tongue. Keep the air moving steadily — don't puff each note. Slow down at direction changes if evenness breaks.",
        "bpm_default":     80,
        "bpm_label":       "80–100 bpm — scale or arpeggio passage",
        "subdivision":     2,
        "rating_question": "How steady was the air and evenness through the scale?",
    },
    "DT_4": {
        "id":              "DT_4",
        "name":            "Speed Build",
        "track":           "double",
        "cue":             "Increase tempo in 4 bpm steps. The ku gets quieter as speed rises — actively listen for it. If ku disappears, drop back 8 bpm and rebuild from there.",
        "bpm_default":     80,
        "bpm_label":       "80–140 bpm — progressive build",
        "rating_question": "How balanced was ku at your fastest clean tempo?",
        "subdivision":     2,
    },
}

SINGLE_QUEUE = [k for k, v in EXERCISES.items() if v["track"] == "single"]
DOUBLE_QUEUE = [k for k, v in EXERCISES.items() if v["track"] == "double"]
FULL_QUEUE = SINGLE_QUEUE + DOUBLE_QUEUE


def queue_for_track(track: str) -> list[str]:
    if track == "single":
        return list(SINGLE_QUEUE)
    if track == "double":
        return list(DOUBLE_QUEUE)
    return list(FULL_QUEUE)
