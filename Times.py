from typing import TYPE_CHECKING
from enum import IntEnum, unique

if TYPE_CHECKING:
    from GameState import GameState
    from Cardboard import Cardboard

@unique
class Phase(IntEnum):
    UNTAP = 0
    UPKEEP = 1
    DRAW = 2
    MAIN1 = 3
    COMBAT = 4
    MAIN2 = 5
    ENDSTEP = 6
    CLEANUP = 7


class RelativeTime:
    def __init__(self, phase: Phase, player: str | int):
        """
        `phase`: which phase of the turn it is
        `player`: whose turn are you referring to. Can be "mine",
                "your", or "any", or it can be a player's integer
                ID number.
        """
        assert isinstance(player, int) or player in ["mine", "your", "any"]
        self.phase: Phase = phase
        self.player: str | int = player

    def __str__(self):
        if isinstance(self.player, int):
            pl_text = "Player%i" % self.player
        else:
            pl_text = self.player  # string
        return "%s %s" % (pl_text, self.phase.name)