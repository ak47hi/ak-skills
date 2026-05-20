# Postmortem: <incident title>

Date: YYYY-MM-DD (incident date)
Author: <name>
Status: Draft | Under review | Final
Severity: SEV1 | SEV2 | SEV3
Customer impact: <user-visible effect, scope, duration>

> Blameless. Focus on systemic causes and learnings, not individual
> mistakes. Errors are how systems teach us.

## Summary

<2–3 sentences. What broke, who was affected, how long, what fixed it.>

## Impact

- **Affected**: <fraction of users / specific tenants / specific endpoints>
- **Duration**: <detection → mitigation → full recovery>
- **Business effect**: <revenue, SLO breach, support load, etc., if measurable>
- **Data loss / corruption**: <none | description>

## Timeline (all times in <timezone>)

| Time | Event |
|---|---|
| HH:MM | <change deployed / external event / first signal> |
| HH:MM | <first alert fired> |
| HH:MM | <on-call paged> |
| HH:MM | <investigation began> |
| HH:MM | <root cause hypothesized> |
| HH:MM | <mitigation applied> |
| HH:MM | <metrics confirmed recovery> |
| HH:MM | <incident declared over> |

## Root cause

<The actual binding cause, identified after diagnosis. Avoid "human
error" — name the systemic gap that allowed the error to reach
production. If multiple causes contributed (often), list them.>

### Contributing factors

- <Latent issue 1 that made this incident worse / more likely>
- <Latent issue 2>
- <...>

## Detection

- **How was it detected**: <alert / customer report / dashboard / external>
- **Time to detect**: <minutes/hours from cause to first signal>
- **Was the right alert in place?**: <yes / no — what should have fired>

## Mitigation

- **How was it mitigated**: <action taken to restore service>
- **Time to mitigate**: <minutes/hours from detection to mitigation>
- **Was a runbook available?**: <yes / no — should one exist now?>

## What went well

- <Concrete things that worked: monitoring caught it; runbook applied
  cleanly; on-call rotation responded; rollback worked.>
- <...>

## What went badly

- <Concrete things that didn't: alert was delayed; runbook was stale;
  rollback procedure didn't work; bystander services degraded.>
- <...>

## Lessons learned

<2–4 short paragraphs. What does this incident teach us about the
system that we didn't know before? What assumption was violated? What
do we now believe that we didn't before?>

## Action items

| Action | Owner | Priority | Due | Status |
|---|---|---|---|---|
| <P0 item — must fix to prevent recurrence> | <name> | P0 | YYYY-MM-DD | open |
| <P1 item — improves resilience / detection> | <name> | P1 | YYYY-MM-DD | open |
| <P2 item — nice to have> | <name> | P2 | YYYY-MM-DD | open |

**Track to completion.** Action items that don't close mean the
postmortem failed.

## Related

- <Link to incident ticket / war room transcript>
- <Link to relevant ADR or RFC>
- <Link to prior similar incidents, if any>
