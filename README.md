# Yu-Gi-Oh Card Scrambler
This tool was created to scramble the effects of Yu-Gi-Oh cards to create a brand new set of cards for you to play with on EDOPro. This can create never-before-seen interactions and make the most unexpected cards meta-defining.

And if you and your opponent are using separate scrambles, you can recreate that feeling of not knowing what your opponent's cards do until you play into them, just like in the anime.

## How to Use
1. Install Project Ignis's [EDOPro](https://projectignis.github.io).
2. Open EDOPro to ensure that it has downloaded the latest card scripts.
3. Get your .cdb (card database) file. You can download the most up-to-date one from Project Ignis [here](https://github.com/ProjectIgnis/BabelCDB/blob/master/cards.cdb). Both players should use the same original .cdb file.
4. Download `YGO_Scrambler.py` or `YGO_Scrambler.exe`, as well as `scramble_flavor_text.txt` from this repository. Save them in a convenient location.
5. If you are using the `YGO_Scrambler.py` Python script, make sure you have Python installed, and that it is version 3.10 or newer.
6. In the location where those files are saved, run the YGO_Scrambler Python script (`python .\YGO_Scrambler.py`) or the executable.
7. In the GUI window that appears, select the .cdb file from step 4, the `ProjectIgnis` directory (on Windows, this is `C:\ProjectIgnis` if you did not change the default installation location), and which player number you are using. You may also make any of the following optional adjustments:
  * Select a banlist file to remove some cards from the cardpool before cards are scrambled.
    * The Scrambler will only remove cards the banlist file sets as banned. Cards set as limited or semi-limited are treated as if they were unlimited.
    * Note that the Scrambler currently only supports current TCG and OCG cards, not pre-errata cards that banlists for historic formats frequently use.
    * Banlists for Goat and Edison formats are included in [the releases](https://github.com/TheLetterJ0/YGO-Scrambler/releases) in `OptionalFiles.zip`.
  * Check any of the boxes to allow some categories of cards to be mixed together. For example, checking the "Field and Continuous Spells" box will mean that some Field Spells may get the effects of Continuous Spells, and some Continuous Spells may get the effects of Field Spells.
  * You can use the dropdown box to allow the stats of Monster Cards (Attribute, Type, Level/Rank, ATK, DEF, Pendulum Scales, and Link Arrows) to be changed. (Due to technical limitations, Link Ratings are not changed under any option.) In addition to the option not to change the stats, there are two levels of randomization to choose from:
    * "Shuffle Stats" takes all the existing stats and shuffles them around between Monsters. It does not keep sets of stats together. This means that for example, Warriors, Darks, and Level 4s will still be common, while Sea Serpents, Fires, and Level 11s will still be rarer.
    * "Randomize Stats" generates completely new stats for each Monster, with stats having equal chances for almost all values. (The exceptions being that Divine and Divine-Beast are still rare, Creator God is extremely rare, and ATK and DEF values are much more likely to be a multiple of 100 than to end in 50.)
  * You can select how many cards to allow in your card pool, allowing for simpler formats and quicker deck building. Setting this value to `0` will leave all cards available. Setting it to any other number will create a banlist file with that many cards set as Unlimited. The entire card pool is still scrambled and the rest of the cards are still available to you, but are marked as Banned. So you can still look through them to see what you missed, or to use them anyway when both players agree. (For example, you might agree to allow the use of the card with the effect of Polymerization, or to allow the use of a card like Dark Magician or a Ritual Spell that your allowed cards need to function.)
  * You may select a seed to use to scramble the cards, or leave it as the randomly selected value. Using the same seed on multiple scrambles will give the same result each time (as long as the same .cdb file, the same options, and the same version of the Scrambler are also used each time). So you can use this to let both players use the same scramble, or to regenerate lost files, if necessary.
8. Press the `Scramble!` button to begin the scrambling.
9. The status of the scrambling and any error messages will be printed in the terminal you ran the Scrambler from, or that appeared when you ran the executable, in step 6. This may take a few minutes to run the first time (or after you delete the card images), depending on how many card images need to be downloaded. Subsequent scrambles should take under 30 seconds, depending on your computer. If you are using the executable file instead of the Python script, this step will be slower.
10. When the messagebox appears saying that the scramble is done, you can close the GUI window and the terminal.
11. All of your generated files will all be placed in `ProjectIgnis\expansions` and its subfolders, except for the banlist file, which is placed in `ProjectIgnis\lflists`.
12. A file named `P1ScrambledForOpponent.cdb` or `P2ScrambledForOpponent.cdb` is generated in the directory where the Scrambler was run. This file has all the data for your cards, but without their effect text. If you and your opponent are using separate scrambles, and you don't want to be able to read each other's cards, give this file to them. If you are using separate scrambles and you do want to be able to read each other's cards, give them a copy of the `P1Scrambled.cdb` or `P2Scrambled.cdb` file in `ProjectIgnis\expansions`. If you want to both be using the same scramble, just make sure that both of you selected the same settings in step 7, including the same seed and player number.
13. The scripts for your cards are saved in `ProjectIgnis\expansions\script`. If you and your opponent are using separate scrambles, make sure the player who is hosting the duel has copies of both player's scripts.
14. When your opponent sends you their .cdb file and script files, put them in the same locations as yours.
15. In the EDOPro deck builder, you can see your scrambled cards by setting the banlist to `Scrambled Card Pool`. If you chose to limit the card pool in step 7, go to the `Limit:` dropdown and select `Unlimited` to see only your allowed cards.
16. To duel using custom cards, you will need to use the `LAN + AI` option, and one player will need to create a virtual network. [This video from leafbladie](https://youtu.be/a_q79uDa3BM?si=DpN9x2cdZ816YAl5&t=124) contains instructions for creating and using a virtual network, starting at 2:04.
17. The person hosting the duel should make sure the `Forbidden List` is set to `N/A` and the `Allowed Cards` is set to `Anything Goes`.
18. Enjoy your duel.

## Removing Files After Use
After you are done using a scramble, you can safely delete all the generated files. You can do this manually, or the Scrambler can be used to do it by following the steps below. This is not necessary to do before generating a new scramble.
1. Run the Scrambler, as in Step 6 above.
2. Select the `Delete` tab at the top of the GUI.
3. Select your scrambled .cdb file, or the original .cdb file used to generate it, and your `ProjectIgnis` directory.
4. Check the boxes of which files you want to delete. The Scrambled .cdb file will not be deleted if you selected the original .cdb file in step 3.
5. Press the `Delete` button.
6. The status of the deletion will be shown in the terminal you ran the Scrambler from, or that appeared when you ran the executable, in step 1. This should take under 30 seconds, depending on your computer.

## Options for Playing and Customizing Your Experience
The three main options for playing are:
* Let both players use the same scramble to focus on building decks within the new cardpool.
* Let both players use different scrambles, but give each other the `P_Scrambled.cdb` files instead of the `P_ScrambledForOpponent.cdb` files, so you are building from different cardpools, but will know what your opponent's cards do when you see them.
* Let both players use different scrambles, and give each other the `P_ScrambledForOpponent.cdb` files, so you have no idea what your opponent's cards do, just like in the anime.
In addition to the customization options available in the GUI, you can:
* Edit the `scramble_flavor_text.txt` file to change the flavor texts generated for your cards that your opponent sees instead of their effects.

## "I Want To See Someone Play with Scrambled Cards To See What it's Like"
Good news! Wham Bam Duel and I have been doing a scrambled version of the Progression Series formula on [his YouTube channel](https://www.youtube.com/@whambamduel). You can see the playlist [here](https://www.youtube.com/playlist?list=PLWB6oGocBDhSjoIEvsT857FMLtcbTSnY4). It is just as chaotic as you might imagine, and it didn't take long for amazing interactions to start appearing.

Or watch [this one-off video](https://youtu.be/0kiZMgUK9S8?si=OmD7ny3ImLrj-BH6) he made with another cohost, which also used the Battle Pack "all monsters are all types" rule.

## "Can I Make Content Using the YGO Scrambler Too?"
Of course you can! Please let me know if you do, because I want to see it. (The best place to reach me is probably Discord, where I am `The Letter J`. You can find me in several Yu-Gi-Oh servers, including the Project Ignis server.)

## Known Issues/Bugs
The following cards have parts of their effects coded outside of their script files, so they are set to never scramble. "Scrambled" versions of them will still be generated, but may not work properly. If you want to use one of these, just use the original card instead:
* Cosmic Flare
* Malefic Paradox Gear
* Malefic Territory
* Millennium-Eyes Illusionist
* Neo Space
* Neos Fusion
* S-Force Chase
* Spirit Elimination
* Tellarknight Constellar Caduceus
* Thunder Dragon Thunderstormech
* Ultimate Dragonic Utopia Ray

The following cards are known to have unfixed issues when scrambled, but have not been set to never scramble:
* The First Sarcophagus (The other Sarcophagus cards will be put on the field, but "Spirit of the Pharaoh" will not be summoned.)
* Assault Mode Activate (Unable to be activated at all.)

Other known issues:
* Ritual Spells and Ritual monsters will list the incorrect cards they are "paired" with. Despite what the cards say, Ritual Monsters are summoned by the Spells that have the effects of the Ritual Spells that originally summoned the Ritual Monster whose effects they now have. And the Ritual Spells will list the level of the original Ritual Monster as their tribute requirement, but they actually require the level of the new Ritual Monster. (For example, if "Giant Soldier of Stone" has the effect of "Hungry Burger", and "Raigeki" has the effect of "Hamburger Recipe", then "Giant Soldier of Stone" can be summoned by using "Raigeki" and tributing 3 stars worth of monsters. "Raigeki" will not summon "Hungry Burger", and "Hamburger Recipe" will not summon "Giant Soldier of Stone".)

The following are not bugs, they are just the way this format works:
* Some effects may be completely unusable because of the card they are scrambled onto. For example, Monarch effects on level 4 monsters.
* Archetypal Ritual Spells will not summon Ritual Monsters that have the effects of a member of that archetype, but are not of that archetype themselves. (For example, the card with the effect of "Gishki Aquamirror" will not summon a "Mystical Elf" that has the effect of "Evigishki Soul Ogre".)
  * However, an archetypal monster scrambled to become a Ritual Monster will be able to be summoned by a card with its archetype's Ritual Spell effect.
* Other cards that must be summoned by the effect of another card cannot be summoned. For example, the card with the effect of "A Deal with Dark Ruler" will summon "Berserk Dragon", regardless of its effect, but the monster with the effect of "Berserk Dragon" will be unsummonable.

## Contributing to the YGO Scrambler and Reporting Broken Effects and Other Bugs
All contributions are welcome!

If you find a card effect that doesn't work like it should, please let me know. I tried to find all the problem cards I could, but there are over 13,000 of them now, and more keep coming. You can report bugs by creating an issue on the Issues tab on this repository. Be sure to include the card(s) with the problem, what card(s) the effect(s) originally came from, what it is doing wrong, the current gamestate and relevant interactions, and anything else important. Please make sure you are not reporting one of the examples above that are known problems or specifically not problems.

Feature requests are also accepted on the Issues tab.

If you want to assist with development, pull requests are welcome.

## "Help! I Need to Regenerate my Scramble, but I Don't Know What My Seed Was!"
Don't worry, concerned stranger with an oddly specific problem. Your scrambled card database contains one illegal card named "Scramble Seed" which lists your seed in its effect text. You can view it in the EDOPro deck builder by selecting `Illegal` from the `Limit:` dropdown and searching for "Scramble Seed".

## Future Plans
I make no guarantees when any of these will happen, if ever. But my plans for future enhancements include:
* Support for more than two players.
* Support for YGO Omega (using manual mode, as that is the only way to use custom cards there).
* Built-in support for alternate format cardpools and pre-errata versions of cards.
* Maybe more?
