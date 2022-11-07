

Cards are represented by two things:
    1)  A Cardboard object, which describes the physical state of the card.
        Tapped vs untapped, summoning-sick (entered the battlefield this turn),
        current zone, stuff like that.
    2)  A RulesText object, which describes the game rules associated with the
        card. Card name, card types, abilities, power and toughness (for
        creatures), stuff like that.
Each Cardboard points to the RulesText that governs it, just like a physical
MtG card has printed text describing the MtG rules that govern it.

A GameState is a frozen slice of time describing the current situation of the
MtG game. This is the equivalent of walking over to a table and seeing an
MtG game abandoned mid-tournament. GameStates are mutable, but the best way to
describe a game progressing is usually to build new GameStates based on the
original GameState rather than modify the existing gamestate. This is because
there are many abilities and choices that can be executed in multiple ways, but
a single GameState object can only ever describe a single one of those ways.

Most of the heavy lifting of the code is done by Verbs and Getters.

Verbs describe any manipulation or change to the GameState. Examples include:
tapping a permanent, drawing a card, losing life, putting a counter on a
permanent, casting a spell, declaring a creature as a blocker. As a general
rule, any action that a player could verbally declare during a tournament
should be described in the code as a Verb. This centralizes all possible
actions so that other things can trigger off of them or modify them.

Getters describe any information it is possible to learn from the GameState.
Examples include: getting the mana value of a card, counting the number of
artifacts in play, finding the power of a creature. This centralizes all
information-gathering so that other abilities can easily modify the effective
values without disturbing the text printed on the cards, so to speak.

-------------------------------------------------------------------------------

Notes comparing this program to the real Magic:The Gathering rules:
    - cannot activate mana abilities WHILE casting a spell. (must pre-float
        all mana to pay for the spell)
    - "Gold" mana can be used to pay for any colored cost, to simplify
        choices during goldfish games.
    - fetchlands are deliberately templated as an enter-the-battlefield
        effect rather than as an activated ability, to simplify choices
        during goldfish games.
    - There is no difference between "choosing" a target and "targeting" one.
    - Triggered abilities can only trigger from play. Cards like Narcomoeba
        or Bridge From Below, whose triggers operate from non-battlefield
        zones, do not yet work. Implementing them would require messing with
        the add-to-zone functions in Player so that they report their
        abilities properly.
    - If two cards are identical EXCEPT that one of them is the source or
        target of something on the stack, the game will treat them as fully
        identical. It cannot distinguish cards based on pointers from the
        stack.
    - Players do not get priority during combat unless something triggers
        during combat. All combat tricks must be done pre-combat. (Also I
        still need to properly code up combat at all, whoops.)
    - Right now, timed abilities (e.g. "at end of turn") will occur at that
        time on EACH turn.  There is no way to specify that it should only
        occur on yours, or on your opponents, or whatever. (Might be a way
        to add this info to Phases?)

Notes on actually-correct things:
    - "casting" a land doesn't use the stack
    - mana abilities don't use the stack
    - "as-enters" triggers don't use the stack

-------------------------------------------------------------------------------

Notes for future improvements or speedups:
    - Some sort of 'animate' or 'change form' Verb which creates a new
        RulesText and swaps the Cardboard's pointer to point at the new
        RulesText. This effectively turns the Cardboard into the new thing.
        The new thing will have a pointer back to the original so that it can
        revert at end of turn, and an end-of-turn trigger to revert it. Make
        sure reversion is recursive in case something is animated twice!
        Also make sure the card reverts if it moves zones.
        Maybe store the revert info within the verb, not within the RulesText?
    - Add delayed triggers, hook them into the timed trigger lists
    - Add field to abilities to say what zones they are active from?
    - I am copying abilities and verbs when I might not need to? I should
        go through carefully later, for speedup, if I want.
    - Make Defer a decorator or abstract class to inherit from?
    - Speedup by getting rid of GameState.has_options?
    - Only need one intermediate set in PlayTree, not one per phase?
    - Might be bug in cleanup where you can cast instants even with an empty
        stack, as long as something already triggered during endstep.
    - PlayTree does a lot of copying. At least once per phase. Can maybe
        do better than that by grouping some of the beginning phases?

-------------------------------------------------------------------------------



The process of taking an action, in GameState.do_priority_action:

1)  The GameState asks the player with priority to choose an action to take,
    or choose to pass to the next player. Possible actions are found using:

    A) Player.get_valid_castables
        Look at all cards in the Player's hand to see if any of them are
        castable (as determined by Cardboard.valid_caster). For each one that
        can be cast, return a Verbs.UniversalCaster object which will be
        responsible for casting that card.

    B) Player.get_valid_activations
        Same idea, but for abilities. For each ability that can be activated
        right now, return a Verbs.UniversalCaster object which is responsible
        for casting it

    Note: the UniversalCasters already contain StackObjects, which in turn
    refer to the thing (Cardboard or ability) which that StackObject would
    hold while on the stack. The StackObject holds Verbs for paying the cost
    of the spell/ability and carrying out the effect of the spell/ability,
    but these are not populated yet. They still lack execution details.

2) The Player's Pilot selects one of these actions to try, or chooses to pass.

3) The UniversalCaster is performed (`do_it`):
    A) Populate the Verb that will pay the cost of this casting/activation.
        The Verb has still not been performed, but all choices or variables
        or targets have now been locked in. (For example: choices for
        sacrificing creatures, or the final mana cost to pay given that
        Thalia is making the spell cost 1 more to cast.)
    B) Populate the Verb that will perform the effect, such as by choosing
        targets.
    C) Put StackObject containing the card/ability onto the stack
    D) Execute the payment Verb (`do_it`). Costs have now been paid.
    E) Put any triggers from paying the cost onto the super_stack, then
        divvy up those triggers onto the stack itself. (For example: if the
        cost included sacrificing creatures, and you have a Mayhem Devil in
        play which triggers whenever a creature is sacrificed.)

4) Items on the stack are resolved (GameState.resolve_top_of_stack)
    A) Removes the StackObject from the stack
    B) Execute the effect Verb (`do_it`)
    C) If the thing on the stack was a card (`Cardboard`), move it to the
        appropriate zone. Generally, permanents go onto the field and spells
        go into the graveyard.
    D) Put any triggers from doing all this onto the super_stack, then
        divvy up those triggers onto the stack itself. (For example: if the
        card was a creature, then Soul Warden would trigger to gain you 1
        life when that creature enters the battlefield.)
