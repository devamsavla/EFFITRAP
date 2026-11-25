# Tomorrow: The Efficiency Trap

**Deck:** https://claude.ai/artifact/BkwQSYMXYQsRBkg9JehDGi · **Playground:** https://claude.ai/artifact/QoYE25MmjTCHMezgWodZzL
**Before you go:** share both links as "anyone with the link" · open the deck in presenter mode (the SAY notes show there) · 35 slides ≈ 17 minutes.

---

## The 3 ideas to really understand (the rest follows from these)

1. **Cheaper answers → many more answers → bigger total.** That's the Jevons paradox. So making each answer cheaper isn't enough; I fixed the *total* instead (a budget).
2. **Hours can be split, jobs can't.**
   - Hours: just take the cleanest ones (greedy). It's the best because swapping a dirty hour for a cleaner free one always helps.
   - Jobs: greedy fails (the A/B/C example: 7 vs 10). So I use a table that tries skip / small / big for each request, one row at a time.
3. **I checked every answer against a slow, trusted method.** 906 checks, 0 mismatches. The tests even caught a bug.

---

## What to say, slide by slide

| # | Slide | Say this |
|---|---|---|
| 1 | 1936 | Turing: one machine can solve anything solvable, given enough time. |
| 2 | Time. | The catch: every step uses electricity. Anything is possible, nothing is free. |
| 3 | Title | My project: what algorithms can do about AI’s energy. |
| 4 | 9 seconds of TV | One AI answer costs about 9 seconds of TV. Tiny. |
| 5 | 2 laptop charges | Press a different button: one 6-second video ≈ 2 laptop charges, ~400× a text answer. |
| 6 | Germany | Add up every data centre: ≈ Germany’s electricity, doubling by 2030. |
| 7 | 23% of Ireland | Already real: data centres use almost a quarter of Ireland’s electricity; new ones near Dublin were refused grid connections. |
| 8 | And water | Querétaro: some homes get water 3 days a week (officials say shortages predate data centres). Uruguay: salt water in taps while Google planned a thirsty data centre. |
| 9 | Who goes first? | AI data centres may triple by 2030. If we don’t set a budget on purpose, a drought or blackout will. |
| 10 | Make it cheaper | So engineers did the obvious thing. |
| 11 | 33× | And it worked: 33× less energy per answer in one year (Google). |
| 12 | +50% | Same year: AI electricity went *up* by half. |
| 13 | Solution became the problem | Cheaper → we use way more. 10× cheaper × 15× more use = 1.5×. The Jevons paradox. |
| 14 | The question | So I asked: what if the total energy is fixed? How do we use it best? |
| 15 | Problem on one slide | Given requests, models, a budget and a forecast. Decide which model and when. Two parts: WHEN and WHICH. |
| 16 | Obvious answers | Run now = dirty. First come first served = refuses people (61%). “Best value first” = wrong… |
| 17 | Greedy fails | …because A grabs the space: 7 vs 10. You can’t run half a job. **Hours split, jobs don’t.** |
| 18 | Real forecast | Real data from 24 Nov. Take the cleanest hours: start at 1 am, not 4 pm: −56%. |
| 19 | Swap proof | If a plan used a dirty hour while a cleaner one was free, swapping helps. So the best plan uses the cleanest. |
| 20 | Two upgrades | Faster: find only the cut-off. Can’t pause: slide a 4-hour window. |
| 21 | Famous hard problem | Choosing models in a budget = knapsack; I call it the backpack trick. Hard in general, but our budget is small, so a table works. |
| 22 | Table by hand | Each row adds a question; each cell picks skip, small or big using the row above. Answer: 2.5, big model for the hard question. |
| 23 | Why fast enough | Trying everything is impossible. The table: double the requests → double the time. I measured it. |
| 24 | Bonus: the bus | Not our problem, the AI company’s: every step reloads the whole model, so the server answers many people per trip. Alone 100%, 20 people ~10% each. |
| 25 | How many fit? | More people = cheaper until memory runs out. Binary search: try the middle, halve the gap. ~6 tries instead of 64. |
| 26 | Bonus 2: the intern | Also the AI company’s trick: a small AI (intern) drafts 8 words, the big AI (boss) checks them all at once. Same answer, ~3× faster. |
| 27 | How many words survive? | Each word right 80% of the time; boss keeps words until the first mistake → ~4.3 words per check. Simulated: 4.31. |
| 28 | Tests | Compared with a trusted solver and with trying everything. 906 checks, 0 mismatches. |
| 29 | Does it help? | Same energy: rate limit answers 61%, mine answers 100%. |
| 30 | Real world | Broke the forecast on purpose (±30%): still 54% less pollution. Never misses a deadline. |
| 31 | No. | It doesn’t beat Jevons. An algorithm spends a budget; people choose it. |
| 32 | What I learned | Read the 4 lines. |
| 33 | Anywhere Door | I packaged both as a tool that sits in front of any AI. |
| 34 | One line | Install, add one line. Open source, tests included. |
| 35 | End | Turing never said it’d be free. Thank you. Questions? |
---

## If he asks…

- **"Why binary search for the bus?"** "Fits in memory / doesn’t fit" flips only once as the bus grows, so you can halve the range each try.

- **"Is it fair to blame data centres for water shortages?"** Not alone: officials in Querétaro say shortages started earlier. My point is that power and water are shared, so someone has to choose. (also on the Q&A slides in the appendix)

- **"Why is greedy optimal for hours?"** The swap argument (slide 19). Energy can be split, so there's never a reason to use a dirtier hour.
- **"Why not greedy for the budget?"** Jobs can't be split: A/B/C, 7 vs 10 (slide 17).
- **"Knapsack is NP-hard, so how is yours fast?"** The table grows with requests × models × budget steps. Our budget is a small number of steps. Fast in practice, not in theory.
- **"Where do the energy numbers come from?"** IEA lab measurements. Companies don't publish theirs. You can plug in your own.
- **"What if the forecast is wrong?"** Tested: ±30% error, still 54% saving; it also re-checks every 30 min.
- **Stuck?** "That's a limit of my project, and here's how I'd fix it."

## Submit
Deck link · `effitrap.zip` (code + 906 tests) · `efficiency-trap-paper.pdf` · playground link.
