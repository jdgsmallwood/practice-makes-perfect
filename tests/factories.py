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
    desired_tempo = 120
    current_tempo = 80
    tags = "legato, test"


class PracticeLogFactory(DjangoModelFactory):
    class Meta:
        model = PracticeLog

    tricky_bit = factory.SubFactory(TrickyBitFactory)
    rating = 3
    interval_before = 0
    interval_after = 1
