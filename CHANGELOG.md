# Changelog

Each entry is one update to this repo. To update: in your repo folder run `git pull`, then from `ios-server` run `docker compose build && docker compose up -d`. Your save isn't touched. Open the game twice afterwards so it picks up the new data.

## 2026-11-14: Trial checkpoint progression

- Each profile's next uncleared trial checkpoint limits dated Vortex events, summon banners and Home event banners. The active trial remains playable at every difficulty; all trials sharing a checkpoint date must be cleared before progression advances.
- Direct Vortex mission loads are checked server-side. After the final checkpoint, dated content is limited to Global's 2024-10-30 closure.
- Undated recurring Vortex events now require a known first-release date. Daily Eggstravaganza, Monthly Fortune Hunt and each Series Boss Battle unlock only from their historical Global release.
- Removed the Rare, Premium 10+1, 5★ Guaranteed 10+1, 5+1 Ticket and EXVIUS summons; the regular Standard Summon remains.
- The per-checkpoint main-story mission cap is not included yet; exact mission IDs for the named story destinations still need to be resolved.

## 2026-11-14: Enhance drops and banner availability

- Enhance dungeon drop entries now have a guaranteed 100% chance and triple their configured quantity.
- Enhance banners already present in the Vortex stay active by extending their availability dates; no extra banners are added and story progression remains in effect.

## 2026-11-13: Farplane exchanges for owned currencies

- The Moogle Guard Captain lists every catalogued exchange with stock for currencies you hold, including exchanges not yet reached by the replay.

## 2026-11-13: Medal exchange descriptions

- Medal exchange products now show an English description of their reward instead of the unresolved `mst_medal_exchange_explain_<id>` key.

## 2026-11-13: Client reports after login

- Optional heavy client reports are requested after the Home screen loads instead of during login, and only once per profile per server process.

## 2026-11-13: Orbonne Vortex image

- Orbonne Monastery Vaults includes its Vortex image without needing a download from the wiki.

## 2026-11-13: Android sound bank version fallback

- Android requests for sound banks now fall back to the newest available bank with the same filename when the requested `Ver` prefix is missing.

## 2026-11-13: Android, multiple players and Vortex images

- Android devices can download the server certificate at `http://100.x.y.z/ca.pem`. The README explains how to install it.
- New devices connecting to the server automatically get their own save and a player ID starting at `300000001`. Existing profiles and device associations stay unchanged.
- To continue an existing default save or share a save between devices, associate their Tailscale addresses with that profile as explained in the README.
- Improved Vortex image loading on iPhone, including Orbonne Monastery Vaults. Open the game twice after updating.

## 2026-11-12: Quest, replay and gameplay improvements

- Completed town quests stay completed after restarting, and Quest Report shows ongoing and cleared quests.
- Historical summons and events now last for their original runs, with more late-game and missing banners. Story-season unlocks still apply.
- Fixed summon image download errors by showing a temporary image when artwork is not ready.
- Improved unit conversion to prisms and fragments, including NV-awakened units.
- Battle results show the EXP actually earned, and used items and item sets are saved correctly.
- Fixed missing treasure rewards; recoverable unpaid rewards are mailed once. Fixed missing fights in Big Bridge and other explorations.
- Game data downloads now use the project's new data host; existing installed data and saves are unchanged.

## 2026-11-12: Summons, LB EXP, Kira and Vision Cards

- The friend point Standard Summon has a 10x button: 10 units for 2,000 friend points.
- Clearing a quest now gives LB EXP to every unit in your party, as on Global: 100 per stamina, 250 per raid orb, 100 per weapon-enhancement orb. Losing or retiring gives none.
- Kira's abilities that showed no name in battle now have English names and descriptions.
- Fixed the game crashing when you view the Metal Gigantuar's Here! vision card in the VIP Shop (and other vision cards sold or won the same way).
- `EXVIUS_SUMMON_ROTATION` set to `0` shows the full summon archive, subject to story-season locks, and turns the historical replay off.
- Open the game twice after updating.

- The summon list now removes banners whose featured units are repeated in another banner's lineup. When lineups are subsets or identical, the newest banner is kept regardless of its offer; if the dates match, the lineup with more featured units wins.
- Banner detail previews now cycle through all featured units. Banners without featured units still load only one representative unit.
- Newly generated Vortex gate rows use archived event names to match the full wiki lists for Enhance, Special Vortex and Nemeses instead of all appearing under Event. Existing native rows are unchanged; Chronicle Battle event names are not present in the current archive yet.

## 2026-11-11: Farplane, awakening and quest Gil fixes

- The Farplane no longer plays its intro on every visit: two scene packs containing a copy of the intro are skipped.
- The Convert-to-Prism/Fragments screen now downloads the missing `F_SACRIFICE_MST` table and builds its index. Open the game twice after updating.
- Neo Vision awakening no longer requires max level or full Super Trust mastery, matching Global's Version 7.0.0 rules. A refused awakening now shows a message instead of opening a broken animation, and 6★ units can use an Omniprism to awaken to 7★.
- Quests now pay their listed clear Gil and include it on the results screen; the Chamber of Riches no longer pays zero.

## 2026-11-11: Missed rewards, Chamber drops, search and summons

- First-clear rewards for already-cleared quests with no payment record can now be sent by mail, after the existing one-time back-pay. Units and recipes already owned are excluded; `EXVIUS_FIRST_CLEAR_MISSED=preview` logs the proposed rewards without mailing them.
- Added the missing Global drops to the always-open Chambers and esper Tests.
- Vision Card search now recognizes English names, Neo Vision summons use the NV animation fallback instead of a chest animation, and unit pots dropped in battles are credited to enhancement points.

## 2026-11-11: Vision Cards and Aquapolis

- Vision Cards equipped on Neo Vision units (such as Blade of Vengeance Ibara) now stay equipped; before, the slot looked empty. Loading a saved party no longer takes units' Vision Cards off.
- Memories from the Aquapolis is hidden from the Vortex for now: its stage files were lost, so it had no treasure chests and no proper ending.
- A summoned Neo Vision unit now comes with a random Vision Card from the cards Global had in its summon pool at that point in the replay, like in Global. A unit's own card comes from EX awakening (EX+1 and EX+3), as before.

## 2026-11-11: Farplane Tower of Earth gifts

- If you beat a Tower of Earth boss in the Farplane (White Dragon, Demon Chimera, Brachiosaur, Erinyes) but never got its gift (Murasame, Force Armor, Killer Bow, Apollo Harp), it now arrives by mail the next time you start the game. Gifts you already have aren't sent again.

## 2026-11-11: Story recipes, the Guide

- Fixed recipes the story gives never unlocking: the crafting tutorial's Bronze Knife recipe (with 3 Copper Ore) now comes after Earth Shrine - Exit, and the Magic Key recipe with the first clear of Grandshelt Castle - Throne Room. If you're already past those points, they arrive by mail the next time you start the game.
- The Guide now checks off units, items, equipment, materia and Vision Cards you have, including the lower forms of units you've awakened (for example 2★ Rain and Lasswell). Monsters are checked off from battles you fight from now on, with their knockdown counts and Libra scans. Units and items you sold or used up before this update can't be recovered.

## 2026-11-11: Daily summons, Mana Mystery shop

- Fixed once-a-day summons (such as the Lunar New Year free summon) showing a pull available again in the evening after you'd used it. The day now resets at 04:00 UTC (11 pm New York time in winter), like the server's other daily resets, and the summon screen shows it the same way.
- Fixed "A connection error has occurred" when buying Aura Glove or Ninja's Trump in the Mana Mystery (Secret of Mana) shop. Both can be bought now, and they also show in the Shop's exchange list. Every other exchange item was checked and buys fine.

## 2026-11-10: Free summons after ticket summons, extra ticket banners

- Fixed a free daily summon (such as Celebrating Lunar New Year) showing a white crystal and giving nothing after you'd used a ticket summon. The game was still naming the last ticket you used; the server now ignores a ticket the summon doesn't take, and a free summon never uses up a ticket.
- A summon that fails no longer shows "Already Summoned" when it wasn't counted.
- Holding a ticket now only adds that ticket's own summon. The 2019 "5★ Select Ticket Lapis Summon" no longer appears in Limited Time, and exact duplicate ticket summons show once; reruns with different reward pools remain separate.

## 2026-11-10: More units in the 5★ Select Summon

- The 5★ Select Summon now also offers Global's limited and collaboration 5★ units (80 more, such as 2B, Sora, Edward Elric and Lilith), at the same 10 tickets. Open the game twice so it picks up the new list.

## 2026-11-10: 5★ Select Summon works

- Fixed the 5★ Select Summon's "Ticket Summon" button doing nothing. It now opens the unit list; pick a unit and 10 5★ Select tickets are spent on it.
- The 5★ Select Summon shows its animated field again.

## 2026-11-10: Ticket summons show up

- Fixed bought summon tickets with no summon to use them on, such as the 1/10 NV Summon Tickets from the VIP Shop. While you hold them, NV Guaranteed EX Summon shows on the summon screen; one summon takes 10 tickets. The same fix covers the 5★ Select, Arena and 5+1 ticket summons.
- Summon tickets aren't listed under Items. They show on the summon that uses them, with how many you have.

## 2026-11-10: Mana Mystery listed once

- Mana Mystery now lists its five quests once instead of twice. The second set (same stages, double mission Lapis) is gone. Producer of the Crystal is now a single quest.
- If you cleared quests in Mana Mystery's second set, the matching quests in the remaining set pay their first-clear rewards again.

## 2026-11-10: Copied quests removed

- Events that listed the same quest several times now list it once: Chamber of Challenges (each area went from up to 110 quests to 20), Elemental Turn Challenge and Producer of the Crystal. Only exact copies were removed: same battle, missions and rewards.

## 2026-11-10: Event currency on every event quest

- Fixed event currency never dropping in some event quests, such as Mana Mystery's second set of quests (its ELT included). 103 quests in 18 events had no currency drops; their monsters now drop it, about as much as the event's other quests of the same level.

## 2026-11-10: Event currency from battles

- Fixed event currency from enemies (such as Candy in Mana Mystery) not arriving. If the game doesn't count the currency the enemies dropped, the server now adds it at the end of the battle, so every clear pays it.

## 2026-11-10: Tall summon banners and faster loading

- Summon list banners are never cropped or height-limited; oversized art is only scaled to 640 px wide, preserving its natural height. Missing deal banners are fetched when requested; if external access is refused, a titled local placeholder prevents a 404 and the real art is retried on the next start.
- The summon archive can be selected with the profile message: `0` for this week's rotation, `1` for Standard, `2`-`5` for Seasons 1-4, and `6` for Collaborations.
- Pending client error logs are acknowledged and discarded when collection is off; report contents are excluded from request captures.
- Game action requests are serialized while state is updated, and logs include time spent waiting for that lock.
- The game loads faster: the server no longer asks it to upload its error log over and over (about 22 MB every 15 seconds). Uploads are now off by default; when you turn them on to get a log, the game sends it once per launch. See the README ("Logs from the game itself").

## 2026-11-10: Exchanges follow the replay, unit dates, the Captain

- King Mog and the Mog Minister now trade for the event that is on this week, like in Global (for example Candy during Mana Mystery), instead of always Star Quartz and Auracite Shards. Between events they keep the exchange of an event currency you still have.
- Exchanges on the Shop's summon coin screen show up while their event is on or while you hold their currency. The Star Quartz unit exchanges appear when the replay reaches January 2023, when Global added them.
- Events only show the quests they had at that point in the replay. Trials and stages a later run added (for example Chamber of the Vengeful's later trials) appear when the replay reaches them, so their rewards and exchanges no longer show up early.
- Orbonne Monastery Vaults' enemies drop Auracite Shards while the event is on, for the Mog Minister's exchange.
- The Vortex lists story and limited-time events at the top and the farming chambers at the bottom.
- Fixed units showing up in summons later than they came out on Global, such as Gilgamesh (FFV), who now appears from the start. 187 units' release dates were checked against Global's own history and moved earlier.
- The units Global launched with can be summoned from the start, including Roselia, Miyuki, Gilbert, Xiao, Firion, Maria, Vaan, Penelo, Shantotto and Fran.
- Limited-time, collaboration and seasonal units no longer show up in regular summons. Like in Global, they only come from the summons that feature them.
- The Moogle Guard Captain in the Vortex town now trades for leftover event currency: his menu lists the exchanges for currency you still hold that King Mog and the Mog Minister aren't showing this week, plus his own Super Trust Moogle and Dark Visions exchanges once the replay reaches them. Future and empty exchanges are gone. His menu updates each time you start the game.
- Exchanges now show the name of the merchant you opened them from: the Mog Minister no longer says he's King Mog, and the Captain's exchanges show the Captain.
- The Vortex town is no longer downloaded again every time you enter it.
- The Captain's exchanges show the right currency icon instead of a Star Quartz-like crystal.
- The Shop's exchange list and King Mog, the Mog Minister and the Captain now share one stock: an item limited to 2 can be bought twice in total, like in Global, not twice in each place.
- Unit pictures on the News notices and the summon Drop Rates pages now come from the game's own files instead of the Brave Exvius wiki, so Neo Vision and other 7★ units (Sol -Neo Vision-, Summoner Yuna, Sora (KHIII) and more) show a picture instead of a grey box.

## 2026-11-10: Collection points

- Collection points in explorations now show up (the sparkling spots; Dalnakya Cavern has three) and give what they gave in Global: ore, Lumber, crysts or magicite, or the event's own items in event explorations.
- What you collect shows on the result screen and lands in your bag when you leave the exploration.

## 2026-11-10: Story units

- Story units (Rain, Lasswell, Fina, Lid, Nichol, Sakura, Jake) and event reward units no longer show up in normal summons.
- Story units now join as you reach them in the story. Saves already past that point get them at the next login.
- Extra copies of story units you already pulled can be sold now.

## 2026-11-10: Random battles, drops, first-clear rewards

- Random battles are actually random now. Chamber of Awakening 5★ was only ever dropping Hard Rocks and Fury Seeds because of this, along with about 1,300 other quests.
- Enemy drop tables filled in from Global's records, so some quests that dropped nothing now drop stuff.
- Event currency (Candy etc.) drops in battle like it used to, boosted since there are no packs to buy.
- King Mog exchange shops are back.
- First clear rewards actually pay out now. If you've already cleared quests, check your gift box for a "First-Clear Rewards" mail.
- Some event rewards corrected to match Global's original runs, and missing challenges restored.
- Raid summons and box summons added. They show up when the replay reaches each raid.
- Fixed the Windows / Docker Desktop `exec /app/entrypoint.sh: no such file or directory` error.
