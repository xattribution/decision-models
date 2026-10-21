# Synthetic set: content ladders

Goal: teach a small model to judge what a bullet says, with the structure held fixed. For each seed you write six versions that all have the same good shape and differ only in how strong the content is, from 5 (best) down to 0.

## Shape, the same in every version

"- [past-tense action]; [how or what]--[why it mattered / result]", one accomplishment, parts in order, 85 to 115 characters, normal clipping (f/, w/, mbrs, msn, sq, wg, prsnl, trng, coord'd, ID'd, spt, hrs and approved acronyms). Keep the six versions within about 15 characters of each other. A reader judging shape alone should call all six equal.

## The six levels

Build each version from the seed's career area and situation. If the seed is weak or has no real accomplishment, invent one plausible accomplishment in the same career area. The numbers may change between levels, because that is part of content.

- 5: a specific action the member led or owned; a concrete how; a measured result with a believable number; scope past the member's own work center (sq, wg, MAJCOM, Service, joint); the result follows from the action.
- 4: the same kind of action and a real result, but the scope is the member's own unit or the number is softer (an estimate, a count instead of an outcome).
- 3: a real action and how, but the result is generic ("improved readiness", "boosted ops") with no number, or the number counts effort (hrs worked, items touched) instead of an outcome.
- 2: a routine duty dressed as an accomplishment, or a result the action can't plausibly have caused. Vary the wording: a strong-sounding verb on a routine task ("Managed sq sign-in rosters"), a passive role ("Served as", "Was POC for", "Supported"), or an inflated claim from a small act. Don't open most level 2 versions with the same verb.
- 1: vague on every part: no clear action of the member's own, no specifics, no checkable result, but written in a professional voice ("Contributed to multiple sq initiatives; aided various efforts--bolstered msn spt").
- 0: professional-sounding filler that says nothing anyone could check: buzzwords in every slot ("Drove excellence across all lines of effort; leveraged synergies--maximized readiness"), or a result that only restates the action. Every word should be real and the sentence should read smoothly; it fails on content, not on readability.

Keep the voice, tone and readability the same at every level: no casual words (stuff, things, okay, fine), no garbled or repeated-word text, no jokes. A reader judging tone or readability alone should call all six equal. Clipping is neutral too: use about as much shorthand at levels 2, 1 and 0 as at 5, 4 and 3.

Don't add hype words, rankings, pushes or banned content (WAPS or test scores, PME attendance, CFC) at any level. Use [NAME] if a person is needed. Vary career fields, verbs and numbers across groups.

Levels must be clearly separated: a careful reader shown the six in random order should put them back in order by content alone.

## Output

Tab-separated lines, no header, six lines per seed, in any order:

seed id	level	text

No tabs or line breaks inside a text. Write nothing else.
