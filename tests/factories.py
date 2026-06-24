import factory
from factory.django import DjangoModelFactory

from pieces.models import Piece, PracticeLog, TrickyBit


class PieceFactory(DjangoModelFactory):
    class Meta:
        model = Piece

    name = factory.Sequence(lambda n: f"Test Piece {n}")
    composer = "Test Composer"
    is_active = True


class TrickyBitFactory(DjangoModelFactory):
    class Meta:
        model = TrickyBit

    piece = factory.SubFactory(PieceFactory)
    label = factory.Sequence(lambda n: f"Passage {n}")
    difficulty = 3
    # No tempo defaults: tempo-less bits go straight to rating in the session,
    # so most E2E tests work without navigating the ladder.
    # Set current_tempo/desired_tempo explicitly in tests that need the ladder.


class PracticeLogFactory(DjangoModelFactory):
    class Meta:
        model = PracticeLog

    tricky_bit = factory.SubFactory(TrickyBitFactory)
    rating = 3
    interval_before = 0
    interval_after = 1
