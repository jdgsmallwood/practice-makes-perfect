from longtones.utils import MIDI_NAMES, midi_to_hz

MAX_ACTIVE = 3

DRILLS = {
    "SLUR": {
        "id": "SLUR",
        "name": "Slow Slur",
        "cue": "Slur between the notes with no tongue. Hold each note for its full value, then make the finger change instantly at the beat.",
        "bpm_default": 56,
        "bpm_label": "56 bpm - half notes, instant finger change",
        "subdivision": 1,
        "rating_question": "How clean was the finger change without tongue?",
        "prompts_tempo": False,
    },
    "APPOG": {
        "id": "APPOG",
        "name": "Grace-Note Link",
        "cue": "Play the first note as a quick appoggiatura into the second. Hear the pair as one gesture, not two separate finger events.",
        "bpm_default": 64,
        "bpm_label": "64 bpm - quick grace-note pairs",
        "subdivision": 2,
        "rating_question": "How immediate did the transition feel?",
        "prompts_tempo": False,
    },
    "ECON": {
        "id": "ECON",
        "name": "Finger Economy",
        "cue": "Keep fingers close to the keys. Watch for flying fingers, then repeat with the smallest possible motion at your fastest clean tempo.",
        "bpm_default": 72,
        "bpm_label": "72 bpm - fastest clean close-finger reps",
        "subdivision": 2,
        "rating_question": "How clean was your fastest close-finger tempo?",
        "prompts_tempo": True,
    },
}

DRILL_ORDER = ["SLUR", "APPOG", "ECON"]


def selectable_notes(midi_low=60, midi_high=96):
    return [
        (midi, MIDI_NAMES.get(midi, str(midi)))
        for midi in range(int(midi_low), int(midi_high) + 1)
    ]


def normalize_pair(a, b):
    a = int(a)
    b = int(b)
    return (a, b) if a < b else (b, a)


def build_session_queue(active_practices):
    queue = []
    for practice in active_practices:
        for exercise_id in DRILL_ORDER:
            queue.append({
                "transition_id": practice.pk,
                "exercise_id": exercise_id,
            })
    return queue
