<!--
Optional hints for one task. Copy to authoring/<task-name>/hint.md — the
workspace authoring folder, never tasks/<task-name>/. It is not part of the
task: it never moves the digest, never ships, and is read only by the optional
Step 3a hinted diagnostic (prompts/step3a.md). A hinted run never counts: it is
not a Step 3c trial and never enters a pass rate or a master-checklist verdict.

What it is for: when every model attempt fails and you cannot tell whether the
task is hard or broken. If attempts start passing once a hint says where the
difficulty is, the task is hard but fair; if they fail the same way however
much you hint, look for a missing requirement, a verifier that rejects valid
work, or an environment that blocks the work, and fix it under Step 2b.

How to write them: gentlest first. Each hint should say a little more than the
one before, the way a helpful colleague would if you were stuck — never the
answer. If the last hint hands over the result, a pass after it tells you
nothing. A requirement the agent could only meet because a hint stated it
belongs in instruction.md instead.

No canary or GUID anywhere in this file. Three hints is a sensible default;
delete a section you do not fill rather than leaving it empty. The HTML
comments are guidance for you and are removed before a hint is pasted into the
staged copy's instruction.md.
-->

## Hint 1

<!-- Point at where the hard part is, without naming a method: the part of the
data, the step of the analysis, or the property of the result that most
attempts get wrong. One or two sentences. -->

## Hint 2

<!-- Name the kind of approach someone in the field would reach for — the
family of model, estimator, correction or transform — but not how to set it up
for this data. -->

## Hint 3

<!-- The most concrete guidance that still leaves the work to the solver: the
order of the steps, or the check that tells a right result from a wrong one.
No parameter values, thresholds, intermediate numbers or final answer. -->
