# Write-ups — <task-name>

<!--
Write-ups skeleton (Master #103). Copy to authoring/<task-name>/write-ups.md and
replace <task-name> with the slug. This is a WORKSPACE record: it never ships and is
never given to the agent -- the task folder carries no README.md. scripts/task_check.py
requires this file with the three headings below, each with real prose; the Step 3b
review and the auditor read it as workspace evidence.

Write for a reader who is not in the field. Never write a pass rate, a model score,
a k/5 result or a tier word (Master #62). Editing it later touches no task file, so
no re-seal is needed. Delete these comments once the sections are written.
-->

## Difficulty

<!-- Why this is hard for a person who knows the field and for an agent: the
judgment, domain knowledge or chain of reasoning it takes, not how long it
runs. Say whether the data is real or synthetic and where it comes from, name
the paper, dataset, pipeline or project the work is drawn from (Master #99),
and say who does this kind of work for a living. -->

## Reference solution

<!-- The approach solution/ takes and the insight that makes it work, at the
level of method rather than code. It must describe what solution/ actually
does today, not an earlier draft. -->

## Verification

<!-- What the tests check and why passing them means the work is right. Where
each graded value comes from — an independent reference, or derived from the
oracle and defended (Master #100). For every tolerance or threshold: what
variation it allows and how it was measured, including at least one
independent correct implementation built differently from solution/, with
each named method classified correct or defective and the 10% margins on the
shipped graded instances (Master #101; no fresh-draw study is required).
Where instances come from a generator and a method's smallest shipped-set
margin is under 20%, the default internal check is 3 fresh unselected draws
(6 only if those 3 are borderline or inconsistent). A correct method that fails a draw, or a
defective method that passes one, is a margin finding. Not running the probe
is never a finding.
Every withheld instance is one no science-free guess (a constant, the range
midpoint, copy-through) reaches — a null that reaches an instance is a
finding to fix, not something to disclose and ship (Master #102). -->
