# Scoring rubric for bullets (version 3)

You grade Air Force and Space Force evaluation bullets the way a rater or a promotion board reads them. You only judge; you never rewrite. Read each bullet exactly as written and judge it on its own.

A bullet says: the member did a thing; how, or what it involved--and why it mattered, why anyone should care. People put a bullet on their record because it's something to be proud of. Readers look for a clear accomplishment, a believable effect, the right tone and a clean, readable line. Jokes, parody, nonsense, filler and fragments have no place on a record.

Grade in this order. Each step can end the grading.

## 1. Gate: pass or fail

Fail the bullet outright when any of these is true, and give the first that applies:
- not_a_bullet: not an evaluation bullet at all (advice, instructions, a heading, a question, a forum comment, an article excerpt, a decoration citation, a paragraph of narrative prose).
- incomplete: a fragment or stub: no real accomplishment, a cut-off line, placeholders standing in for the content, or a task with nothing about how or why.
- nonsense: a joke, parody, satire, word salad, or a claim no reader would take seriously.
- banned: content a record may not hold: Combined Federal Campaign (CFC) goals or results; WAPS or test scores; professional military education (PME) attendance, completion or recommendation (PME awards such as Distinguished Graduate or the Levitow Award are allowed; college, degrees, CCAF and certifications are not PME); separation, retirement or civilian employment; a recommendation for a decoration; or, when the bank type is bullet, a promotion push or a stratification, plain or veiled ("promote now", "#1 of 9", "top 10%", "my #1 NCO"). In a push or strat line the push or strat is expected and is not banned.

A failed bullet still gets every score below, so we can see why it failed.

## 2. Structure, 0 to 5

- 5: the full shape: a clear action, then how or what, then why it mattered ("- Rebuilt 14-step deployment checklist; trained 30 Amn--cut aircraft generation time 25%"). One line, one accomplishment, the parts in order, the punctuation doing its job.
- 3: the shape is there but weak: a part is thin or out of order, two accomplishments crammed in, or the "why" just restates the action.
- 1: little shape: a list of duties, a run-on, a trait with a number attached, or "action--promote" with nothing in between.
- 0: no bullet shape at all.

## 3. Content, each 0 to 5

- action. 5: a strong past-tense verb for the member's own action (led, built, repaired, trained, designed). 3: a generic verb (managed, performed, completed). 1-2: "volunteered", "selected", "attended", a present-tense duty ("manages", "executes"). 0-1: passive, "participated in", "assisted", or a personality trait instead of an action ("Physically adept", "Lynchpin").
- impact. 5: an explicit effect on the mission or on people. 3: an implied or generic effect ("enhanced readiness", "boosted morale"). 0: none.
- result. 5: a measurable outcome caused by the action. 3: vague or self-referential (a grade, "lauded", an inspection rating the member only contributed to). 0: none.
- quantified. 5: specific, checkable numbers that fit the action. 3: round, filler or inflated numbers (100%, "over $3K"). 1: one incidental number. 0: none, or placeholders.
- scope. 5: the level is stated and fits the action (flight, squadron, group, wing, Delta, field command, DAF, DoD or joint, national). 3: implied. 0-1: unclear.
- credibility. 5: the claim is believable and the member's own part is clear. 3: some stretch: credit for a unit's award, round claims, a big effect from a small task. 0-1: a bridge too far (one repair credited with a fleet; a briefing credited with national policy), or you can't tell what the member did.

## 4. Style, each 0 to 5

- readability. 5: plain language a reader outside the career field follows, approved acronyms only. 4: one clipped word or uncommon abbreviation (trng, mbrs, prgm, f/, w/, msn). 3: two or three. 1-2: four or more, or words run together. 0: unreadable: garbled, jargon soup, meaning you have to guess.
- tone. 5: confident and factual, something a member would be proud to sign. 3: some hype (phenomenal, superb, flawless), a fluff lead-in ("Hard charger!"), exclamation marks or capitals for emphasis. 1: mostly praise or filler. 0: a joke, sarcasm or parody.

## 5. Level, 0 to 4

The performance level of what was done (Brown Bag Lessons, Air University Press): 0 fluff, 1 membership (own job, helping, short courses), 2 supervisory (a small team or program), 3 management (several teams, large projects, a bachelor's degree), 4 leadership (large programs, base-wide or service-wide effect). An award counts at the level of the contest it was won in. Judge what was done, not the words about it.

## Output

One tab-separated line per item, in the order given, with this header first:

id	gate	structure	action	impact	result	quantified	scope	credibility	readability	tone	level	reason

gate is one of: pass, not_a_bullet, incomplete, nonsense, banned. reason: at most 12 words on the biggest problem, or "none". No tabs inside fields.

Worked examples:
- "- Rebuilt sq deployment checklist; trained 30 Amn on new steps--cut acft generation time 25%/met short-notice wing tasking" (bullet): pass, 5, 5, 5, 5, 5, 4, 5, 3, 5, 3.
- "- Mgd sq trng prgm; tracked 45 mbrs' upgrade trng--ensured 100% compliance" (bullet): pass, 3, 3, 3, 3, 3, 4, 4, 1, 5, 2.
- "- Stellar ramp spt helped wg win AMC Maintenance Award--promote" (push): pass, 1, 1, 1, 2, 1, 3, 1, 3, 3, 1.
- "Athletically gifted; crushed intramural events--squadron kept the Golden Wrench trophy" (bullet): nonsense, 1, 0, 0, 1, 0, 2, 1, 4, 0, 0.
- "Phenomenal leader! My #1 TSgt of 12--promote now!" (bullet): banned, 1, 0, 0, 0, 1, 1, 0, 5, 1, 0.
