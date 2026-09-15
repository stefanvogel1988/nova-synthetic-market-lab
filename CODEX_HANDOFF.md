# NOVA Synthetic Market Lab — Codex Handoff

## Objective
Execute the approved NOVA Synthetic Market Lab implementation plan with true subagent-driven development.

## Binding documents
1. `docs/superpowers/specs/2026-09-15-nova-synthetic-market-lab-design.md` — approved design/spec; binding authority.
2. `docs/superpowers/plans/2026-09-15-nova-synthetic-market-lab-implementation.md` — implementation plan.

## Execution method
Use the installed Superpowers skills and follow them strictly:

1. `superpowers:using-superpowers`
2. `superpowers:subagent-driven-development`
3. `superpowers:using-git-worktrees` before implementation
4. Execute all plan tasks continuously, one fresh implementer/reviewer cycle per task as required by the SDD skill.
5. Use TDD as specified in the implementation plan.
6. Run the final whole-branch review and `superpowers:verification-before-completion` before claiming completion.
7. Finish with `superpowers:finishing-a-development-branch` and present integration options; do not push or merge without explicit user approval.

## Non-negotiable constraints
- Validation-phase budget: EUR 0.
- No hardware requirement for V1.
- No paid research panels, premium tools, or paid API requirement for V1 acceptance.
- The deterministic/local provider must make the complete V1 test suite and end-to-end run possible without external credentials.
- Synthetic evidence must never be represented as observed human behavior, real purchase intent, scientific learning proof, PMF, or a revenue forecast.
- Market-demand claims cannot become `PROVEN` from synthetic simulations alone.
- Preserve skeptical/rejecting personas, disagreement, distributions, counterevidence, and critical safety failures.
- Provider architecture remains replaceable.

## User intent
The user wants a serious zero-capital pre-seed validation system for NOVA, not a toy demo. The output should help determine what is strong, what is weak, what should be killed or modified, and which claims must next be validated with real parents, children, educators, or investors.

## Completion definition
Completion means:
- every implementation-plan task completed and reviewed;
- full test suite passing;
- deterministic fixed-seed end-to-end run succeeds with no external credentials;
- persona/product/experiment/safety/evidence/report outputs are generated;
- final validation report contains explicit synthetic-evidence disclaimers and required human-validation gaps;
- repo is left in a clean, reviewable branch/worktree with final verification evidence.
