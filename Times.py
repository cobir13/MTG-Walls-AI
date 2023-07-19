from enum import IntEnum, unique


@unique
class Phase(IntEnum):
    UNTAP_UPKEEP = 0
    DRAW = 1
    MAIN1 = 2
    COMBAT = 3
    MAIN2 = 4
    ENDSTEP = 5
    CLEANUP = 6


class RelativeTime:
    """
    A way to describe 'the next <phase>.  For example, "the next
    end step" would be (ENDSTEP, "any") while "my next end step"
    would be (ENDSTEP, "mine").
    """

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


class UntilEndOfTurn(RelativeTime):
    def __init__(self):
        super().__init__(Phase.UNTAP_UPKEEP, "any")

    def __str__(self):
        return "EndOfTurn"
