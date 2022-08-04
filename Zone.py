from __future__ import annotations

import types
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from GameState import GameState, Player
    from Stack import StackObject
    from Cardboard import Cardboard
    import Getters


class Zone:

    class RelativeError(Exception):
        pass

    class NotSpecificPlayerError(Exception):
        pass

    def __init__(self, player: int | None | Getters.GetPlayers = None,
                 location: int | slice | None = None):
        """
        Represents the Game Zone, e.g. for a Cardboard to be
        in. `player` is the index of the player who controls
        this zone, or None if it is a shared zone (like the
        stack). `location` is the specific location within
        the zone (like index 0 to mean the top of the deck),
        or None if the zone is unordered (like battlefields).
        """
        self.player: int | None | Getters.GetPlayers = player
        self.location: int | slice | None = location

    @property
    def is_fixed(self) -> bool:
        """Does the Zone refer to constant fixed players, or
        is it using a Getter to determine player?"""
        return isinstance(self.player, (int, types.NoneType))

    @property
    def is_single(self) -> bool:
        """Does the Zone refer to a single specific known
        player? Or to either multiple players or a Getter?"""
        return isinstance(self.player, int)

    def _get_whole_zone_list(self, player: Player
                             ) -> List[Cardboard | StackObject]:
        """Return a reference to the correct zone."""
        raise Exception

    def get(self, state: GameState) -> List[StackObject | Cardboard]:
        """Get the list of objects which exist in this zone
        in the given GameState. If nothing exists in the
        given location, returns empty list.
        The Zone MUST be absolute in order for this function
        to work! If it is relative, raises RelativeError.
        """
        if not self.is_fixed:
            raise Zone.RelativeError
        if isinstance(self.player, int):
            # single player. grab it and return it
            pl = state.player_list[self.player]
            whole_zone = self._get_whole_zone_list(pl)
            if self.location is None or len(whole_zone) == 0:
                return whole_zone
            elif isinstance(self.location, int):
                # slice to ensure we return a list. also avoids index errors.
                loc = self.location % len(whole_zone)  # avoid issues with -1.
                return whole_zone[loc:loc+1]
            else:  # slice
                return whole_zone[self.location]
        elif self.player is None:  # look at all players
            acc = []  # return concatenated zones of all players
            for ii in range(len(state.player_list)):
                # "recurse" by defining a new temporary Zone object
                temp_zone = self.__class__(ii, self.location)
                acc += temp_zone.get(state)
            return acc

    def __str__(self):
        text = type(self).__name__
        text += str(self.player) if self.player is not None else ""
        return text

    def copy(self):
        new_zone = Zone(self.player, self.location)
        new_zone.__class__ = self.__class__  # set the class type directly
        return new_zone

    def get_absolute_zones(self, state: GameState, asking_player: int,
                           asking_source: Cardboard | None) -> List[Zone]:
        """Returns a list of zones of the same type as self,
        except that they contain absolute Player information
        rather than relative. If self is already absolute,
        just returns a copy of self (wrapped in a list)."""
        if self.is_fixed:
            return [self.copy()]
        else:
            # self.player is a Getter.GetPlayers
            pl_list = self.player.get(state, asking_player, asking_source)
            zone_list = []
            for ii in pl_list:
                new_zone = self.copy()
                new_zone.player = ii
                zone_list.append(new_zone)
            return zone_list

    def add_to_zone(self, state: GameState, card: Cardboard):
        """Add the given object to the given zone. Raises a
        NotSpecificPlayerError is the player is not uniquely
        specified as an int.
        Does not check whether obj is the correct type.
        MUTATES THE GIVEN GAMESTATE.
        """
        if not self.is_single:
            raise Zone.NotSpecificPlayerError
        else:
            raise Exception  # not implemented

    def remove_from_zone(self, state: GameState, card: Cardboard):
        """Remove the given object from the given zone. Raises
        a RelativeError if self is not absolute. Does not check
        whether obj is the correct type.
        MUTATES THE GIVEN GAMESTATE.
        """
        if not self.is_single:
            raise Zone.NotSpecificPlayerError
        else:
            raise Exception  # not implemented

    def __eq__(self, other):
        return (type(self) == type(other)
                and self.player == other.player
                and self.location == other.location)


class Deck(Zone):
    # index -1 is the top of the deck. Index 0 is the bottom.
    def __init__(self, player: int | None | Getters.GetPlayers, location=None):
        super().__init__(player, location)

    def _get_whole_zone_list(self, player: Player) -> List[Cardboard]:
        return player.deck

    def add_to_zone(self, state: GameState, card: Cardboard):
        if not self.is_single:
            raise Zone.NotSpecificPlayerError
        elif isinstance(self.player, int):
            dist_from_bottom = self.location
            if dist_from_bottom is None:
                dist_from_bottom = -1  # add to top of deck by default
            state.player_list[self.player].add_to_deck(card, dist_from_bottom)

    def remove_from_zone(self, state: GameState, card: Cardboard):
        """Remove the given object from the given zone. Raises
        a RelativeError if self is not absolute. Does not check
        whether obj is the correct type.
        MUTATES THE GIVEN GAMESTATE.
        """
        if not self.is_fixed:
            raise Zone.RelativeError
        elif isinstance(self.player, int):
            state.player_list[self.player].remove_from_deck(card)
        elif self.player is None:  # look at all players
            for ii in range(len(state.player_list)):
                # "recurse" by defining a new temporary Zone object
                temp_zone = self.__class__(ii, self.location)
                temp_zone.remove_from_zone(state, card)


class DeckBottom(Deck):
    # index -1 is the top of the deck. Index 0 is the bottom.
    def __init__(self, player: int | None | Getters.GetPlayers):
        super().__init__(player, 0)


class DeckTop(Deck):
    # index -1 is the top of the deck. Index 0 is the bottom.
    def __init__(self, player: int | None | Getters.GetPlayers):
        super().__init__(player, -1)


class Hand(Zone):
    def __init__(self, player: int | None | Getters.GetPlayers):
        super().__init__(player, None)  # hand resorts itself, so no location

    def _get_whole_zone_list(self, player: Player) -> List[Cardboard]:
        return player.hand

    def add_to_zone(self, state: GameState, card: Cardboard):
        if not self.is_single:
            raise Zone.NotSpecificPlayerError
        elif isinstance(self.player, int):
            state.player_list[self.player].add_to_hand(card)

    def remove_from_zone(self, state: GameState, card: Cardboard):
        """Remove the given object from the given zone. Raises
        a RelativeError if self is not absolute. Does not check
        whether obj is the correct type.
        MUTATES THE GIVEN GAMESTATE.
        """
        if not self.is_fixed:
            raise Zone.RelativeError
        elif isinstance(self.player, int):
            state.player_list[self.player].remove_from_hand(card)
        elif self.player is None:  # look at all players
            for ii in range(len(state.player_list)):
                # "recurse" by defining a new temporary Zone object
                self.__class__(ii).remove_from_zone(state, card)


class Field(Zone):
    def __init__(self, player: int | None | Getters.GetPlayers):
        super().__init__(player, None)  # field resorts itself, so no location

    def _get_whole_zone_list(self, player: Player) -> List[Cardboard]:
        return player.field

    def add_to_zone(self, state: GameState, card: Cardboard):
        if not self.is_single:
            raise Zone.NotSpecificPlayerError
        elif isinstance(self.player, int):
            state.player_list[self.player].add_to_field(card)

    def remove_from_zone(self, state: GameState, card: Cardboard):
        """Remove the given object from the given zone. Raises
        a RelativeError if self is not absolute. Does not check
        whether obj is the correct type.
        MUTATES THE GIVEN GAMESTATE.
        """
        if not self.is_fixed:
            raise Zone.RelativeError
        elif isinstance(self.player, int):
            state.player_list[self.player].remove_from_field(card)
        elif self.player is None:  # look at all players
            for ii in range(len(state.player_list)):
                # "recurse" by defining a new temporary Zone object
                self.__class__(ii).remove_from_zone(state, card)


class Grave(Zone):
    def __init__(self, player: int | None | Getters.GetPlayers):
        super().__init__(player, None)  # grave is not ordered

    def _get_whole_zone_list(self, player: Player) -> List[Cardboard]:
        return player.grave

    def add_to_zone(self, state: GameState, card: Cardboard):
        if not self.is_single:
            raise Zone.NotSpecificPlayerError
        elif isinstance(self.player, int):
            state.player_list[self.player].add_to_grave(card)

    def remove_from_zone(self, state: GameState, card: Cardboard):
        """Remove the given object from the given zone. Raises
        a RelativeError if self is not absolute. Does not check
        whether obj is the correct type.
        MUTATES THE GIVEN GAMESTATE.
        """
        if not self.is_fixed:
            raise Zone.RelativeError
        elif isinstance(self.player, int):
            state.player_list[self.player].remove_from_grave(card)
        elif self.player is None:  # look at all players
            for ii in range(len(state.player_list)):
                # "recurse" by defining a new temporary Zone object
                self.__class__(ii).remove_from_zone(state, card)


class Stack(Zone):
    def __init__(self):
        super().__init__(None, None)  # stack is shared. Zone doesn't order.

    @property
    def is_fixed(self):
        return True

    @property
    def is_single(self):
        return True

    def _get_whole_zone_list(self, player: Player) -> List[StackObject]:
        return player.gamestate.stack

    def add_to_zone(self, state: GameState, card: Cardboard):
        """Cardboard doesn't live on the stack, so just change
        the Cardboard's Zone without actually adding anything
        to any list."""
        card.zone = Stack()

    def remove_from_zone(self, state: GameState, card: Cardboard):
        """Cardboard doesn't live on the stack, so removing it
         from the stack doesn't actually change anything."""
        return


class Unknown(Zone):
    """For new cards which have not yet been given a home."""
    def __init__(self):
        super().__init__(None, None)

    @property
    def is_fixed(self):
        return True

    @property
    def is_single(self):
        return True

    def _get_whole_zone_list(self, player: Player):
        return []

    def get(self, state: GameState) -> List[StackObject | Cardboard]:
        return []

    def add_to_zone(self, state: GameState, card: Cardboard):
        return  # does nothing

    def remove_from_zone(self, state: GameState, card: Cardboard):
        return  # does nothing
