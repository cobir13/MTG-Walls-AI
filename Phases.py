from enum import IntEnum, unique


@unique
class Phases(IntEnum):
    UNTAP = 0
    UPKEEP = 1
    DRAW = 2
    MAIN1 = 3
    COMBAT = 4
    MAIN2 = 5
    ENDSTEP = 6
    CLEANUP = 7


