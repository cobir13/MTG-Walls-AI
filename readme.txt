
Notes comparing this program to the real Magic:The Gathering rules:
    - cannot activate mana abilities WHILE casting a spell. (must pre-float
        all mana to pay for the spell)
    - "Gold" mana that can be used to pay for any colored cost, to simplify
        choices during goldfish games.
    - fetchlands are deliberately templated as an enter-the-battlefield
        effect rather than as an activated ability, to simplify choices
        during goldfish games.

Notes on actually-correct things:
    - "casting" a land doesn't use the stack
    - mana abilities don't use the stack
    - "as-enters" triggers don't use the stack



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

