from typing import TYPE_CHECKING
from enum import IntEnum, unique

if TYPE_CHECKING:
    from GameState import GameState
    from typing import List
    from Cardboard import Cardboard


@unique
class Phase(IntEnum):
    UNTAP_UPKEEP = 0
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



def do_special_phase_thing(state: GameState) -> List[GameState]:
    """
    Takes in a GameState which is assumed to be at the beginning of
    whatever phase it says it is in.  Returns a copy of that state
    where the special phase actions have now been done (uptap, draw
    a card, etc).  This may result in triggers on the stack.
    Does not mutate the input state."""
    state2 = state.copy()
    if state2.phase == Phase.UNTAP_UPKEEP:
        state2.step_untap()
        results: List[GameState] = []
        # put any superstack triggers due to untapping onto the stack
        for state_upkeep in state2.clear_super_stack():
            # put any upkeep triggers onto the superstack, then onto stack
            state_upkeep.step_upkeep()
            results.extend(state_upkeep.clear_super_stack())
        return results
    elif state2.phase == Phase.DRAW:
        state2.step_draw()
        return state2.clear_super_stack()
    elif state2.phase == Phase.MAIN1 or state2.phase == Phase.MAIN2:
        return [state2]
    elif state2.phase == Phase.COMBAT:
        state2.step_attack()        # TODO: IMPLEMENT COMBAT PROPERLY
        return state2.clear_super_stack()
    elif state2.phase == Phase.ENDSTEP:
        state2.step_endstep()
        return state2.clear_super_stack()
    elif state2.phase == Phase.CLEANUP:
        return state2.step_cleanup()
    else:
        raise ValueError("Phase isn't in standard phase list!")


