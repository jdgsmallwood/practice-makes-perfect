"""Scale catalog — slug, name, category, semitone intervals from root.

Intervals are ascending semitone offsets from the root (root = 0).
A 7-note scale returns 7 values (not including the octave).
"""

ROOTS = [
    "C", "C#/Db", "D", "D#/Eb", "E", "F",
    "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B",
]

# Short note names used for ABC notation (sharps preferred for display)
ROOT_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ROOT_NAMES_FLAT  = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

CATALOG = [
    # ── Diatonic modes ──────────────────────────────────────────────────────
    {
        "slug": "major",
        "name": "Major (Ionian)",
        "category": "Diatonic Modes",
        "intervals": [0, 2, 4, 5, 7, 9, 11],
        "description": "The standard major scale (Ionian mode).",
    },
    {
        "slug": "dorian",
        "name": "Dorian",
        "category": "Diatonic Modes",
        "intervals": [0, 2, 3, 5, 7, 9, 10],
        "description": "Minor mode with a raised 6th. Used heavily in jazz and folk.",
    },
    {
        "slug": "phrygian",
        "name": "Phrygian",
        "category": "Diatonic Modes",
        "intervals": [0, 1, 3, 5, 7, 8, 10],
        "description": "Minor mode with a flattened 2nd. Flamenco and Spanish flavour.",
    },
    {
        "slug": "lydian",
        "name": "Lydian",
        "category": "Diatonic Modes",
        "intervals": [0, 2, 4, 6, 7, 9, 11],
        "description": "Major mode with a raised 4th. Dreamy, ethereal quality.",
    },
    {
        "slug": "mixolydian",
        "name": "Mixolydian",
        "category": "Diatonic Modes",
        "intervals": [0, 2, 4, 5, 7, 9, 10],
        "description": "Major mode with a flattened 7th. Blues, rock and Celtic feel.",
    },
    {
        "slug": "aeolian",
        "name": "Natural Minor (Aeolian)",
        "category": "Diatonic Modes",
        "intervals": [0, 2, 3, 5, 7, 8, 10],
        "description": "The natural minor scale.",
    },
    {
        "slug": "locrian",
        "name": "Locrian",
        "category": "Diatonic Modes",
        "intervals": [0, 1, 3, 5, 6, 8, 10],
        "description": "Diminished mode — flattened 2nd and 5th. Very tense, rarely used melodically.",
    },
    # ── Minor variants ───────────────────────────────────────────────────────
    {
        "slug": "harmonic_minor",
        "name": "Harmonic Minor",
        "category": "Minor Variants",
        "intervals": [0, 2, 3, 5, 7, 8, 11],
        "description": "Natural minor with a raised 7th. Creates the characteristic augmented 2nd.",
    },
    {
        "slug": "melodic_minor",
        "name": "Melodic Minor (ascending)",
        "category": "Minor Variants",
        "intervals": [0, 2, 3, 5, 7, 9, 11],
        "description": "Minor with raised 6th and 7th ascending. The jazz melodic minor.",
    },
    # ── Major variants ───────────────────────────────────────────────────────
    {
        "slug": "harmonic_major",
        "name": "Harmonic Major",
        "category": "Major Variants",
        "intervals": [0, 2, 4, 5, 7, 8, 11],
        "description": "Major scale with a flattened 6th. Creates an exotic augmented 2nd in the upper tetrachord.",
    },
    # ── Jazz scales ──────────────────────────────────────────────────────────
    {
        "slug": "bebop_dominant",
        "name": "Bebop Dominant",
        "category": "Jazz",
        "intervals": [0, 2, 4, 5, 7, 9, 10, 11],
        "description": "Mixolydian with an added natural 7th. 8-note scale used in bebop.",
    },
    {
        "slug": "altered",
        "name": "Altered (Super Locrian)",
        "category": "Jazz",
        "intervals": [0, 1, 3, 4, 6, 8, 10],
        "description": "The 7th mode of melodic minor. All extensions altered (♭9, ♯9, ♭5, ♯5). Classic over dominant 7th chords.",
    },
    {
        "slug": "lydian_dominant",
        "name": "Lydian Dominant (Acoustic)",
        "category": "Jazz",
        "intervals": [0, 2, 4, 6, 7, 9, 10],
        "description": "Lydian with a flattened 7th. 4th mode of melodic minor.",
    },
    {
        "slug": "phrygian_dominant",
        "name": "Phrygian Dominant",
        "category": "Jazz",
        "intervals": [0, 1, 4, 5, 7, 8, 10],
        "description": "5th mode of harmonic minor. Spanish / Flamenco dominant sound.",
    },
    # ── Pentatonic & Blues ───────────────────────────────────────────────────
    {
        "slug": "major_pentatonic",
        "name": "Major Pentatonic",
        "category": "Pentatonic & Blues",
        "intervals": [0, 2, 4, 7, 9],
        "description": "5-note major scale (no 4th or 7th). Universal folk and pop scale.",
    },
    {
        "slug": "minor_pentatonic",
        "name": "Minor Pentatonic",
        "category": "Pentatonic & Blues",
        "intervals": [0, 3, 5, 7, 10],
        "description": "5-note minor scale (no 2nd or 6th). The backbone of blues and rock.",
    },
    {
        "slug": "blues",
        "name": "Blues",
        "category": "Pentatonic & Blues",
        "intervals": [0, 3, 5, 6, 7, 10],
        "description": "Minor pentatonic plus the ♭5 blue note.",
    },
    # ── Symmetric scales ─────────────────────────────────────────────────────
    {
        "slug": "whole_tone",
        "name": "Whole Tone",
        "category": "Symmetric",
        "intervals": [0, 2, 4, 6, 8, 10],
        "description": "Six equal whole steps. Only 2 distinct transpositions. Debussy's favourite.",
    },
    {
        "slug": "octatonic_hw",
        "name": "Octatonic / Diminished (H–W)",
        "category": "Symmetric",
        "intervals": [0, 1, 3, 4, 6, 7, 9, 10],
        "description": "Alternating half-whole steps. Used over diminished 7th chords.",
    },
    {
        "slug": "octatonic_wh",
        "name": "Octatonic / Diminished (W–H)",
        "category": "Symmetric",
        "intervals": [0, 2, 3, 5, 6, 8, 9, 11],
        "description": "Alternating whole-half steps. Used over dominant 7th chords.",
    },
    {
        "slug": "augmented",
        "name": "Augmented",
        "category": "Symmetric",
        "intervals": [0, 3, 4, 7, 8, 11],
        "description": "Alternating minor-third and half-step. Only 4 distinct transpositions.",
    },
    {
        "slug": "tritone",
        "name": "Tritone Scale",
        "category": "Symmetric",
        "intervals": [0, 1, 4, 6, 7, 10],
        "description": "Symmetric hexatonic. Two interlocking augmented triads a tritone apart.",
    },
    {
        "slug": "prometheus",
        "name": "Prometheus",
        "category": "Symmetric",
        "intervals": [0, 2, 4, 6, 9, 10],
        "description": "Scriabin's mystic chord scale. Lydian flavour with ♭7 and ♯4.",
    },
    # ── Exotic & World ───────────────────────────────────────────────────────
    {
        "slug": "double_harmonic",
        "name": "Double Harmonic (Byzantine)",
        "category": "Exotic & World",
        "intervals": [0, 1, 4, 5, 7, 8, 11],
        "description": "Two harmonic tetrachords. Also called Arabic or Gypsy major. Very exotic.",
    },
    {
        "slug": "hungarian_minor",
        "name": "Hungarian Minor",
        "category": "Exotic & World",
        "intervals": [0, 2, 3, 6, 7, 8, 11],
        "description": "Harmonic minor with a raised 4th. Also called Double Harmonic Minor. Rich and dramatic.",
    },
    {
        "slug": "hungarian_major",
        "name": "Hungarian Major",
        "category": "Exotic & World",
        "intervals": [0, 3, 4, 6, 7, 9, 10],
        "description": "Major variant with an augmented 2nd between the 1st and 2nd degrees.",
    },
    {
        "slug": "neapolitan_major",
        "name": "Neapolitan Major",
        "category": "Exotic & World",
        "intervals": [0, 1, 3, 5, 7, 9, 11],
        "description": "Phrygian lower tetrachord + Lydian upper. Unique double-augmented relationship.",
    },
    {
        "slug": "neapolitan_minor",
        "name": "Neapolitan Minor",
        "category": "Exotic & World",
        "intervals": [0, 1, 3, 5, 7, 8, 11],
        "description": "Phrygian lower tetrachord + harmonic minor upper. Eastern European flavour.",
    },
    {
        "slug": "enigmatic",
        "name": "Enigmatic",
        "category": "Exotic & World",
        "intervals": [0, 1, 4, 6, 8, 10, 11],
        "description": "Verdi's enigmatic scale. Starts with a half step, then all whole tones until the last two.",
    },
    {
        "slug": "persian",
        "name": "Persian",
        "category": "Exotic & World",
        "intervals": [0, 1, 4, 5, 6, 8, 11],
        "description": "Ancient Persian scale with two augmented 2nds. Very exotic Middle-Eastern flavour.",
    },
    {
        "slug": "ukrainian_dorian",
        "name": "Ukrainian Dorian (Romanian Minor)",
        "category": "Exotic & World",
        "intervals": [0, 2, 3, 6, 7, 9, 10],
        "description": "Dorian with a raised 4th. Found in Eastern European folk music.",
    },
    {
        "slug": "locrian_natural2",
        "name": "Locrian ♮2 (Half-Diminished)",
        "category": "Exotic & World",
        "intervals": [0, 2, 3, 5, 6, 8, 10],
        "description": "6th mode of melodic minor. Locrian with a natural 2nd. Used over half-diminished chords.",
    },
    {
        "slug": "locrian_natural6",
        "name": "Locrian ♮6",
        "category": "Exotic & World",
        "intervals": [0, 1, 3, 5, 6, 9, 10],
        "description": "5th mode of harmonic major. Locrian with a natural 6th.",
    },
    # ── Japanese scales ──────────────────────────────────────────────────────
    {
        "slug": "hirajoshi",
        "name": "Hirajoshi",
        "category": "Japanese",
        "intervals": [0, 2, 3, 7, 8],
        "description": "Traditional Japanese pentatonic. Contemplative, sparse feel.",
    },
    {
        "slug": "in",
        "name": "In (Japanese)",
        "category": "Japanese",
        "intervals": [0, 1, 5, 7, 8],
        "description": "Japanese pentatonic scale found in shakuhachi music.",
    },
    {
        "slug": "insen",
        "name": "Insen",
        "category": "Japanese",
        "intervals": [0, 1, 5, 7, 10],
        "description": "Japanese pentatonic. Related to the Phrygian mode.",
    },
    {
        "slug": "iwato",
        "name": "Iwato",
        "category": "Japanese",
        "intervals": [0, 1, 5, 6, 10],
        "description": "Japanese pentatonic named after a Shinto shrine. Very sparse and mysterious.",
    },
]

# Group catalog by category for display
def get_catalog_by_category():
    from collections import OrderedDict
    result = OrderedDict()
    for entry in CATALOG:
        cat = entry["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(entry)
    return result
