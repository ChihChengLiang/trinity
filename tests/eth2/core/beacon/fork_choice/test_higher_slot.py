import pytest

from eth2.beacon.fork_choice.higher_slot import HigherSlotScore, HigherSlotScoring
from eth2.beacon.types.blocks import SignedBeaconBlock


@pytest.mark.parametrize("slot", (i for i in range(10)))
def test_higher_slot_fork_choice_scoring(slot):
    block = SignedBeaconBlock.create().transform(["message", "slot"], slot)

    expected_score = HigherSlotScore(slot)

    scoring = HigherSlotScoring()
    score = scoring.score(block)

    assert score == expected_score
