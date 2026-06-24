from datetime import date

# Preferred enharmonic spellings for flute (flats over sharps for Eb/Ab/Bb/Db/Gb)
MIDI_NAMES = {
    60: "C4",  61: "C#4", 62: "D4",  63: "Eb4", 64: "E4",
    65: "F4",  66: "F#4", 67: "G4",  68: "Ab4", 69: "A4",
    70: "Bb4", 71: "B4",  72: "C5",  73: "C#5", 74: "D5",
    75: "Eb5", 76: "E5",  77: "F5",  78: "F#5", 79: "G5",
    80: "Ab5", 81: "A5",  82: "Bb5", 83: "B5",  84: "C6",
    85: "C#6", 86: "D6",  87: "Eb6", 88: "E6",  89: "F6",
    90: "F#6", 91: "G6",  92: "Ab6", 93: "A6",  94: "Bb6",
    95: "B6",  96: "C7",
}

FOCUS_CHOICES = [
    ("steadiness",   "Steadiness"),
    ("intonation",   "Intonation"),
    ("crescendo",    "Crescendo"),
    ("decrescendo",  "Decrescendo"),
    ("body_scan",    "Body Scan"),
]

FOCUS_PROMPTS = {
    "steadiness":   "Listen for wavering in the last third of your breath. Keep air moving through to the very end.",
    "intonation":   "Match the drone. Listen for beats (interference patterns) and try to eliminate them.",
    "crescendo":    "Start pp and grow to ff. Keep the tone full and vibrant at every dynamic.",
    "decrescendo":  "Start ff and taper to pp. Hold all the way through — don't stop early.",
    "body_scan":    "Before you blow: scan shoulders, neck, jaw, knees. After: where did you work too hard?",
}

FOCUS_QUESTION = {
    "steadiness":   "How steady?",
    "intonation":   "How in tune?",
    "crescendo":    "How full throughout?",
    "decrescendo":  "How controlled to the end?",
    "body_scan":    "How relaxed overall?",
}


def session_notes_for_date(d=None) -> list[int]:
    """Cycle-of-fifths rotation across the flute range.

    Offset cycles through 0–11 over 12 days. Each session practices ~5-6
    notes spaced a perfect fifth (7 semitones) apart, covering the full range.
    """
    if d is None:
        d = date.today()
    offset = d.toordinal() % 12
    notes = []
    midi = 60 + offset
    while midi <= 96:
        notes.append(midi)
        midi += 7
    return notes


def midi_to_hz(midi: int) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12))
