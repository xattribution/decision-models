# Scoring rubric for bullets (version 4)

You grade Air Force and Space Force evaluation bullets the way a rater or a promotion board reads them. You only judge; you never rewrite. Read each bullet exactly as written and judge it on its own.

A bullet says: the member did a thing; how, or what it involved--and why it mattered, why anyone should care. People put a bullet on their record because it's something to be proud of. Readers look for a clear accomplishment, a believable effect, the right tone and a line they can read on one pass. Jokes, parody, nonsense, filler and fragments have no place on a record.

Bullets are clipped to fit one line. Space Force forms in particular are written in a dense clipped style, and the clipped forms vary by year and unit (pers or prsnl, trng or tng, sq or sqdn). Clipping that any Airman or Guardian reads at a glance is normal and is not a readability problem. Examples of normal shorthand: f/, w/, mbr, mbrs, msn, sq, wg, flt, tm, trng, prgm, prsnl, spt, ops, intel, acft, coord'd, dvlp'd, ID'd, qb'd, rec'd, eval'd, ldr, ldrs, mgmt, mnx, rqmt, std, tgt, wpn, hrs, and approved acronyms such as NCO, SNCO, DoD, USSF, MAJCOM, Delta (DEL), TDY, OPLAN, ISR, C2.

Grade in this order. Each step can end the grading.

## 1. Gate: pass or fail

Fail the bullet outright when any of these is true, and give the first that applies:
- not_a_bullet: not an evaluation bullet at all (advice, instructions, a heading, a question, a forum comment, an article excerpt, a decoration citation, a paragraph of narrative prose).
- incomplete: a fragment or stub: no real accomplishment, a cut-off line, placeholders standing in for the content, a task with nothing about how or why, or no action of the member's own (traits, a duty title, hype, a ranking or an award standing in for the accomplishment).
- nonsense: a joke, parody, satire, word salad, a real-sounding line with a planted joke, a claim no reader would take seriously, or text so garbled no reader can say what was done.
- banned: content a record may not hold: Combined Federal Campaign (CFC) goals or results; WAPS or test scores; professional military education (PME) attendance, completion or recommendation (PME awards such as Distinguished Graduate or the Levitow Award are allowed; college, degrees, CCAF and certifications are not PME); separation, retirement or civilian employment; a recommendation for a decoration; or, when the bank type is bullet, a promotion push or a stratification, plain or veiled ("promote now", "#1 of 9", "top 10%", "my #1 NCO"). In a push or strat line the push or strat is expected and is not banned, but the line still needs an accomplishment of the member's own to pass.

A failed bullet still gets every score below, so we can see why it failed.

## 2. Structure, 0 to 5

- 5: the full shape, fitting the form: a clear action, then how or what, then why it mattered, on one line, one accomplishment, the parts in order, the punctuation doing its job.
- 3: the shape is there but weak: a part is thin or out of order, two accomplishments crammed in, a line that runs long, or a "why" that just restates the action.
- 1: little shape: a list of duties, a run-on, a trait with a number attached, or "action--promote" with nothing in between.
- 0: no bullet shape at all.

## 3. Content, each 0 to 5

- action. 5: a strong past-tense verb for the member's own action (led, built, repaired, trained, designed). 3: a generic verb (managed, performed, completed). 1-2: "volunteered", "selected", "attended", a present-tense duty ("manages", "executes"). 0-1: passive, "participated in", "assisted", or a personality trait instead of an action.
- impact. 5: an explicit effect on the mission or on people. 3: an implied or generic effect ("enhanced readiness", "boosted morale"). 0: none, or an impact that only restates the action or says it was done.
- result. 5: a measurable outcome caused by the action. 3: vague or self-referential (a grade, "lauded", an inspection rating the member only contributed to). 0: none, or a result that only restates the action.
- quantified. 5: specific, checkable numbers that fit the action. 3: round, filler or inflated numbers (100%, "over $3K"). 1: one incidental number. 0: none, or placeholders.
- scope. 5: the level is stated and fits the action (flight, squadron, group, wing, Delta, field command, DAF, DoD or joint, national). 3: implied. 0-1: unclear.
- credibility. 5: the claim is believable and the member's own part is clear. 3: some stretch: credit for a unit's award, round claims, a big effect from a small task. 0-1: a bridge too far (one repair credited with a fleet; a briefing credited with national policy), or you can't tell what the member did.

## 4. Style, each 0 to 5

- readability. Can a rater in the field decode the line on one pass? 5: every part reads at a glance, including normal clipped shorthand. 3: one spot you re-read or guess (an unfamiliar acronym with no context, metric shorthand like "1.8/goal<2.8%"). 1: words or numbers run together, or more than one part you have to guess. 0: garbled; no reader can say what was done (and the gate is nonsense).
- clipping. How heavily clipped the line is, whether or not it reads well: 5 none; 4 one or two clipped words or uncommon abbreviations; 3 three to five; 1 six or more. Approved acronyms don't count.
- tone. 5: confident and factual, something a member would be proud to sign. 3: some hype (phenomenal, superb, flawless), a fluff lead-in ("Hard charger!"), exclamation marks or capitals for emphasis. 1: mostly praise or filler. 0: a joke, sarcasm or parody.

## 5. Level, 0 to 4

The performance level of what was done (Brown Bag Lessons, Air University Press): 0 fluff, 1 membership (own job, helping, short courses), 2 supervisory (a small team or program), 3 management (several teams, large projects, a bachelor's degree), 4 leadership (large programs, base-wide or service-wide effect). An award counts at the level of the contest it was won in. Judge what was done, not the words about it.

## Output

One tab-separated line per item, in the order given, with this header first:

id	gate	structure	action	impact	result	quantified	scope	credibility	readability	clipping	tone	level	reason

gate is one of: pass, not_a_bullet, incomplete, nonsense, banned. reason: at most 12 words on the biggest problem, or "none". No tabs inside fields.

Worked examples (gate, structure, action, impact, result, quantified, scope, credibility, readability, clipping, tone, level):
- "- Rebuilt sq deployment checklist; trained 30 Amn on new steps--cut acft generation time 25%/met short-notice wing tasking" (bullet): pass, 5, 5, 5, 5, 5, 4, 5, 5, 3, 5, 3.
- "- Mgd sq trng prgm; tracked 45 mbrs' upgrade trng--ensured 100% compliance" (bullet): pass, 3, 3, 3, 3, 3, 4, 4, 4, 1, 5, 2.
- "- Led 6-mbr tm f/3 sat handovers; coord'd w/2 sqs/41 prsnl--zero lost contacts, DEL msn rdy 2 days early" (bullet): pass, 5, 5, 4, 5, 5, 4, 4, 5, 1, 5, 2.
- "- Sq SNCOQ! Flt Chf3-mo; led 52 prsnlqual'd 61 RDSgen'd 190 hrs--met 40 tskgs w97% rt" (bullet): nonsense, 1, 3, 1, 2, 3, 2, 2, 0, 1, 3, 2.
- "- Stellar ramp spt helped wg win AMC Maintenance Award--promote" (push): incomplete, 1, 1, 1, 2, 1, 3, 1, 4, 3, 3, 1.
- "Athletically gifted; crushed intramural events--squadron kept the Golden Wrench trophy" (bullet): nonsense, 1, 0, 0, 1, 0, 2, 1, 4, 5, 0, 0.
- "Phenomenal leader! My #1 TSgt of 12--promote now!" (bullet): banned, 1, 0, 0, 0, 1, 1, 0, 5, 5, 1, 0.
