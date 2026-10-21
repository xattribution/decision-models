# Synthetic set: near-miss edits of real bullets

Goal: teach a model the small differences that separate real bullets, on one dimension at a time. Ladders that run from excellent to useless are too easy; real bullets differ by about one point. For each seed bullet you write four versions on the dimension named in your task.

- Level 2: the seed itself, copied exactly, character for character.
- Level 3: one careful edit that makes the seed one step better on the dimension.
- Level 1: one edit that makes the seed one step worse on the dimension.
- Level 0: a second edit on top of level 1 that makes it one more step worse.

Each step should be the size of a real difference a reviewer would notice and agree with, not a rewrite. Change only what the dimension covers and keep everything else as close to the seed as you can: the same voice, the same amount of shorthand, about the same length (within 20 characters unless length is the flaw), and no new hype words, rankings, pushes or banned content. If the seed is weak on the dimension, level 3 can still be a clear improvement; if it is already excellent, make level 3 a smaller polish that a reviewer would still prefer.

## STRUCTURE (content held fixed)

Structure is the shape "- action; how--why": one accomplishment, parts in order, separators doing their job, fitting about 115 characters with normal clipping. Normal shorthand is not a flaw, and spelling words out is not an improvement. Keep the same facts and numbers in all four versions. Keep the seed's shorthand in every version: never spell clipped words out (pkg'd, lcls, mbrs, f/, w/) or add filler words as the way to make a version worse, and never clip words as the way to make it better, unless the edit is fitting an over-long seed under the line.

Steps worse, pick what fits the seed and vary across groups: move the result to the front; join the parts into a run-on without separators; cram a second accomplishment in with a slash; restate the action as the "why"; let it run long past the line; turn the action into a duty or a trait. Steps better: put the parts in order; tighten loose wording; replace a weak separator; split off a crammed second accomplishment (drop it); fit it under the line.

## CONTENT (structure held fixed)

Content is what it says: a specific action the member owned, a concrete how, a measured and believable result that follows from the action, and scope past the member's own work center. Keep the same shape, separators and length in all four versions; keep the four within about 10 characters of the seed, so length never tells the levels apart.

Steps worse, vary across groups: replace a measured result with a generic one ("improved readiness"); shrink the scope to the member's own shop; swap an outcome number for an effort count (hrs, items); soften an owned action to a supporting role (assisted, supported); make the result something the action could not have caused; remove the how. Steps better: replace a generic result with a believable measured outcome; name the wider scope the work touched; make the member's own role clear; connect the result to the action.

## IMPACT (action, how, shape and length held fixed)

Impact is the "why it mattered" part: what changed for the mission, the unit or people because of the work, and how far that effect reached. Edit only the part after the "--" (or wherever the seed states its effect) and keep the action and the how word for word. Length and shorthand must not tell the levels apart: keep every version within 5 characters of the seed, so a weaker effect gets about as many words as the stronger one (a generic phrase padded to the same length, not a short stub), and a stronger effect must fit in the same space. Use the seed's own amount of shorthand in the effect at every level.

Steps worse, vary across groups: replace a mission effect with one that restates the action ("completed the inspection"); shrink the effect to the member's own task or shop; swap a concrete effect for a generic phrase ("enhanced ops", "boosted morale"); claim an effect the work could not have caused; drop the effect to a bare number with no meaning attached. Steps better: name what the work enabled or prevented for the mission; tie the number to an outcome a reader cares about (time saved for whom, risk removed, capability delivered); name how far the effect reached when the seed implies it (flight, sq, wg, Delta, MAJCOM, joint).

## Output

Tab-separated lines, no header, four lines per seed, in any order:

seed id	level	text

No tabs or line breaks inside a text. Write nothing else.
