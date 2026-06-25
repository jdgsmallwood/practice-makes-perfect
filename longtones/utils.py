from datetime import date

# Enharmonic spellings: C#/F#/G# as sharps; Eb/Ab/Bb as flats — covers all instrument ranges.
MIDI_NAMES = {
    21: "A0",   22: "Bb0",  23: "B0",
    24: "C1",   25: "C#1",  26: "D1",   27: "Eb1",  28: "E1",   29: "F1",
    30: "F#1",  31: "G1",   32: "Ab1",  33: "A1",   34: "Bb1",  35: "B1",
    36: "C2",   37: "C#2",  38: "D2",   39: "Eb2",  40: "E2",   41: "F2",
    42: "F#2",  43: "G2",   44: "Ab2",  45: "A2",   46: "Bb2",  47: "B2",
    48: "C3",   49: "C#3",  50: "D3",   51: "Eb3",  52: "E3",   53: "F3",
    54: "F#3",  55: "G3",   56: "Ab3",  57: "A3",   58: "Bb3",  59: "B3",
    60: "C4",   61: "C#4",  62: "D4",   63: "Eb4",  64: "E4",   65: "F4",
    66: "F#4",  67: "G4",   68: "Ab4",  69: "A4",   70: "Bb4",  71: "B4",
    72: "C5",   73: "C#5",  74: "D5",   75: "Eb5",  76: "E5",   77: "F5",
    78: "F#5",  79: "G5",   80: "Ab5",  81: "A5",   82: "Bb5",  83: "B5",
    84: "C6",   85: "C#6",  86: "D6",   87: "Eb6",  88: "E6",   89: "F6",
    90: "F#6",  91: "G6",   92: "Ab6",  93: "A6",   94: "Bb6",  95: "B6",
    96: "C7",   97: "C#7",  98: "D7",   99: "Eb7",  100: "E7",  101: "F7",
    102: "F#7", 103: "G7",  104: "Ab7", 105: "A7",  106: "Bb7", 107: "B7",
    108: "C8",
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


def session_notes_for_date(d=None, midi_low: int = 60, midi_high: int = 96) -> list[int]:
    """Cycle-of-fifths rotation across an instrument's range.

    Offset cycles through 0–11 over 12 days. Each session practices ~5-6
    notes spaced a perfect fifth (7 semitones) apart, covering the full range.
    """
    if d is None:
        d = date.today()
    offset = d.toordinal() % 12
    notes = []
    midi = midi_low + offset
    while midi <= midi_high:
        notes.append(midi)
        midi += 7
    return notes


def midi_to_hz(midi: int) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12))
