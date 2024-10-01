# Yu-Gi-Oh Card Scrambler
This tool was created to scramble the effects of Yu-Gi-Oh cards to create a brand new set of cards for you to play with on EDOPro. This can create never-before-seen interactions and make the most unexplected cards meta-defining.
And if you and your opponent are using separate scrambles, you can recreate that feeling of not knowing what your opponent's cards do until you play into them, just like in the anime.

## How to Use
1. Install [Python](https://www.python.org/downloads/).
2. Install Project Ignis's [EDOPro](https://projectignis.github.io).
3. Open EDOPro, to ensure that it has downloaded the latest card scripts.
4. Get your .cdb (card database) file. You can download the most up-to-date one from Project Ignis [here](https://github.com/ProjectIgnis/BabelCDB/blob/master/cards.cdb). Make sure that you and your opponent are using the same original .cdb file.
5. Download `YGO_Scrambler.py` and `scramble_flavor_text.txt` from this repository. Save them in a convenient location.
6. In the location where those files are saved, run the YGO_Scrambler script. (On windows, you can do this by shift-right-clicking in the directory where they are saved, selecting `Open PowerShell window here`, and running `python .\YGO_Scrambler.py`.)
7. In the GUI window that appears, select the .cdb file from step 4, the `ProjectIgnis` directory (on Windows, this is `C:\ProjectIgnis` if you did not change the default installation location), which player number you are using, and optionally which categories of cards to allow to be mixed together. Optionally, you may select a seed to use to scramble the cards, or leave it as the randomly selected value. Using the same seed on multiple scrambles will give the same result each time (as long as the same .cdb file is used and the same options are selected), so you can use this to let both players use the same scramble, or to regenerate lost files, if necessary.
8. Press the `Scramble!` button to begin the scrambling.
9. The status of the scrambling and any error messages will be printed in the terminal you ran the Scrambler from in step 6. This will take several minutes to run, and will take extra long the first time, as card arts are copied or downloaded. Any card arts that already exist in your `ProjectIgnis\pics` folder will be copied instead of downloaded, which will be faster. A fresh install with no images downloaded will be significantly slower. In future scrambles, the card arts will not need to be recopied or redownloaded, so the process will go faster.
10. When the message appears in the terminal saying that the scramble is done, you can close the GUI window and the terminal.
11. Your new .cdb file will appear in the directory where the Scrambler was run, with the name `P1Scrambled.cdb` or `P2Scrambled.cdb`, depending on the player number you selected. Move that file to the `ProjectIgnis\expansions` directory.
12. A file named `P1ScrambledForOpponent.cdb` or `P2ScrambledForOpponent.cdb` is also generated in the directory where the Scrambler was run. This file has all the data for your cards, but without their effect text. If you and your opponent are using separate scrambles, and you don't want to be able to read each other's cards, give this file to them. If you are using separate scrambles and you do want to be able to read each other's cards, give them a copy of the `P1Scrambled.cdb` or `P2Scrambled.cdb` file. If you want to both be using the same scramble, just make sure that both of you selected the same settings in step 12, including the same seed and player number.
13. The scripts for your cards are saved in `ProjectIgnis\script\custom_scrambled`. If you and your opponent are using separate scrambles, zip all of these files up and send them to them.
    * Note that Player 1's scripts will all start with `c31...`, and Player 2's will start with `c32...`. Only send the scripts that match your player number.
    * The YGO Scrambler will automatically remove existing scripts from previous scrambles matching your player number, but not those from the other player. If you are duleing an opponent who is using a new scramble, be sure to delete any existing old scripts matching their player number before adding their scripts.
14. When your opponent sends you their .cdb file and script files, put them in the same locations as yours. (And again, delete any existing scripts for your opponent's player number before adding their scripts, as explained in the previous step.)
15. In the EDOPro deck builder, you can see your scrambled cards by setting the banlist to `N/A`, enabling the `Alternate formats` checkbox, and selecting `Custom` from the `Limit:` dropdown.
16. To duel using custom cards, you will need to use the `LAN + AI` option, and one player will need to create a virtual network. [This video from leafbladie](https://youtu.be/a_q79uDa3BM?si=DpN9x2cdZ816YAl5&t=124) contains instructions for creating and using a virtual network, starting at 2:04.
17. The person hosting the duel should make sure the `Forbidden List` is set to `N/A` and the `Allowed Cards` is set to `Anything Goes`.
18. Enjoy your duel.

## Options for Playing and Customizing Your Experience
The three main options for playing are:
* Let both players use the same scramble to focus on building decks within the new cardpool.
* Let both players use different scrambles, but give each other the `P1Scrambled.cdb` files instead of the `P1ScrambledForOpponent.cdb` files, so you are building from different cardpools, but will know what your opponent's cards do when you see them.
* Let both players use different scrambles, and give each other the `P1ScrambledForOpponent.cdb` files, so you have no idea what your opponent's cards do, just like in the anime.
In addition to the customization options available in the GUI, you can:
* Use a .cdb file other than the current one from Project Ignis to scramble only the cards in that database for a format with fewer cards, like Goat or Edison.
* Edit the `scramble_flavor_text.txt` file to change the flavor texts generated for your cards that your opponent sees instead of their effects.

## "I Want To See Someone Play with Scrambled Cards To See What it's Like"
Good news! Wham Bam Duel and I have been doing a scrambled version of the Progression Series formula on [his YouTube channel](https://www.youtube.com/@whambamduel). You can see the playlist [here](https://www.youtube.com/playlist?list=PLWB6oGocBDhSjoIEvsT857FMLtcbTSnY4). It is just as chaotic as you might imagine, and it didn't take long for amazing interactions to start appearing.

## "Can I Make Content Using the YGO Scrambler Too?"
Of course you can! Please let me know if you do, because I want to see it. (The best place to reach me is probably Discord, where I am `The Letter J`. You can find me in several Yu-Gi-Oh servers, including the Project Ignis server.)

## Known Issues/Bugs
* The YGO Scrambler has only been tested on Windows so far. I *think* it should work on other systems, but I make no guarantees.
* The following cards have parts of their effects coded outside of their script files, so they are set to never scramble. "Scrambled" versions of them will still be generated, but may not work properly. If you want to use one of these, just use the original card instead:
  * Millennium-Eyes Illusionist
  * Malefic Paradox Gear
  * Neos Fusion
  * Spirit Elimination
  * Cosmic Flare
  * Malefic Territory
  * Neo Space
  * S-Force Chase
  * Ultimate Dragonic Utopia Ray
  * Tellarknight Constellar Caduceus
  * Thunder Dragon Thunderstormech
* The following cards are known to have unfixed issues when scrambled, but have not been set to never scramble:
  * The First Sarcophagus (The other Sarcophagus cards will be put on the field, but "Spirit of the Pharaoh" will not be summoned.)
  * Assault Mode Activate (Unable to be activated at all.)
* Other known issues:
  * Ritual Spells and Ritual monsters will list the incorrect cards they are "paired" with. Despite what the cards say, Ritual Monsters are summoned by the Spells that have the effects of the Ritual Spells that originally summoned the Ritual Monster whose effects they now have. And the Ritual Spells will list the level of the original Ritual Monster as their tribute requirement, but they actually require the level of the new Ritual Monster. (For example, if "Giant Soldier of Stone" has the effect of "Hungry Burger", and "Raigeki" has the effect of "Hamburger Recipe", then "Giant Soldier of Stone" can be summoned by using "Raigeki" and tributing 3 stars worth of monsters. "Raigeki" will not summon "Hungry Burger", and "Hamburger Recipe" will not summon "Giant Soldier of Stone".)
* The following are not bugs, they are just the way this format works:
  * Some effects may be completely unusable because of the card they are scrambled onto. For example, Monarch effects on level 4 monsters.
  * Archetypal Ritual Spells will not summon Ritual Monsters that have the effects of a member of that archetype, but are not of that archetype themselves. (For example, the card with the effect of "Gishki Aquamirror" will not summon a "Mystical Elf" that has the effect of "Evigishki Soul Ogre".)
    * However, an archetypal monster scrambled to become a Ritual Monster will be able to be summoned by a card with its archetype's Ritual Spell effect.
  * Other cards that must be summoned by the effect of another card cannot be summoned. For example, the card with the effect of "A Deal with Dark Ruler" will summon "Berserk Dragon", regardless of its effect, but the monster with the effect of "Berserk Dragon" will be unsummonable.

## Contributing to the YGO Scrambler and Reporting Broken Effects and Other Bugs
All contributions are welcome!
If you find a card effect that doesn't work like it should, please let me know. I tried to find all the problem cards I could, but there are over 13,000 of them now, and more keep coming. You can report bugs by creating an issue on the Issues tab on this repository. Be sure to include the card(s) with the problem, what card(s) the effect(s) originally came from, what it is doing wrong, the current gamestate and relevant interactions, and anything else important. Please make sure you are not reporting one of the examples above that are known problems or specifically not problems.
Feature requests are also accepted on the Issues tab.
If you want to assist with development, pull requests are welcome.

## "Help! I Need to Regenerate my Scramble, but I Don't Know What my Seed Was!"
Don't worry concerned stranger with an oddly specific problem. Your scrambled card database contains one illegal card named "Scramble Seed" which lists your seed in its effect text. You can view it in the EDOPro deck builder by selecting `Illegal` from the `Limit:` dropdown and searching for "Scramble Seed".

## Future Plans
I make no guarantees when any of these will happen, if ever. But my plans for future enhancements include:
* Actually testing on Linux and Macs.
* Support for more than two players.
* More randomization options.
* Support for YGO Omega (using manual mode, as that is the only way to use custom cards there).
* Support for alternate format cardpools pre-errata versions of cards.
* And more?
