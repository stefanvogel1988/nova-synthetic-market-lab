# NOVA Synthetic Market Lab — Design Specification

Date: 2026-09-15
Status: Draft for user review
Budget constraint: €0 for validation phase

## 1. Purpose

Build a reproducible zero-budget synthetic validation system for NOVA, a screen-free audio and knowledge platform for children aged roughly 5–9. The system must stress-test product positioning, pricing, usage, safety, education use cases, investor objections, and key assumptions before any hardware investment.

The lab is not intended to prove product-market fit. It is intended to reduce uncertainty, expose risks, prioritize human validation, and produce an investor-grade evidence register that clearly separates public evidence, synthetic evidence, assumptions, and unknowns.

## 2. Core principles

1. Synthetic evidence is directional, never equivalent to real purchasing behavior.
2. Every experiment must define its hypothesis and success/failure criteria before execution.
3. Product variants must be tested comparatively, not only as a single favored concept.
4. Personas must include skeptical and rejecting profiles, not merely likely adopters.
5. Outputs must preserve disagreement and distribution, not collapse all results into averages.
6. Every conclusion must carry an evidence label.
7. No paid research panels, hardware, subscriptions, or premium tooling are required for V1.
8. The architecture must be provider-agnostic so the agent engine can be replaced later.

## 3. Evidence labels

- PROVEN: Supported by reliable external evidence or direct observed human behavior.
- SUPPORTED: Multiple synthetic tests and/or external signals point in the same direction.
- CONTESTED: Results differ materially across personas, experiments, or sources.
- ASSUMPTION: Plausible but not yet meaningfully tested.
- UNKNOWN: Insufficient information.

Synthetic simulation alone can never promote a market-demand claim to PROVEN.

## 4. System architecture

### 4.1 Main components

1. Persona Factory
   - Generates and validates persona populations.
   - Maintains demographic, behavioral, budget, media, trust, and technology attributes.

2. Product Variant Registry
   - Stores NOVA concept variants and individual feature toggles.
   - Enables controlled A/B and multivariate tests.

3. Experiment Engine
   - Runs concept tests, pricing tests, scenario tests, 30-day simulated usage, education tests, and messaging tests.

4. Focus Group Engine
   - Runs multi-agent discussions with explicit disagreement rules.
   - Captures argument shifts and post-discussion opinion changes.

5. Red Team Council
   - Independent expert-style agents assigned to find failure modes.

6. Investment Committee
   - Scores business quality before and after seeing peer criticism.

7. Child Interaction Simulator
   - Simulates child questions, NOVA responses, follow-ups, comprehension, boredom, and repeat use.

8. Safety Evaluation Engine
   - Runs benign, sensitive, dangerous, ambiguous, and adversarial child prompts.

9. Scoring & Bias Control
   - Applies standardized rubrics, positivity penalties, contradiction checks, and calibration rules.

10. Evidence Register
    - Central store for hypotheses, evidence, scores, confidence, counterevidence, and status.

11. Validation Report Generator
    - Produces an executive report, investor summary, risk register, and list of required real-world tests.

### 4.2 Provider abstraction

The lab must not hard-wire itself to one model or framework.

Interfaces:
- PersonaEngine
- SimulationEngine
- FocusGroupEngine
- JudgeEngine
- SafetyJudge
- ReportGenerator

TinyTroupe may be used as an execution engine, but the NOVA data model, experiment definitions, scoring rules, and report format remain independent.

## 5. Persona populations

### 5.1 Parent population — target 150

Key dimensions:
- Child age
- Number of children
- Household disposable income band
- Price sensitivity
- Existing devices: Toniebox, Wobie, Yoto, tablet, smart speaker, none
- Spotify / Apple Music / other / no streaming
- Screen-time philosophy
- AI attitude: enthusiastic / pragmatic / cautious / opposed
- Privacy concern
- Education orientation
- Convenience orientation
- Technical confidence
- Urban / suburban / rural
- Gift-buying behavior
- Subscription tolerance
- Brand trust sensitivity

Personas must include budget constraints and competing spending options.

### 5.2 Child population — target 30

Age 5–9 with variation in:
- curiosity frequency
- language ability
- reading ability
- attention span
- preferred content
- willingness to speak to devices
- frustration tolerance
- novelty seeking
- sibling context
- music vs stories vs learning preference
- confidence asking questions

Child personas are used for interaction simulation, not as a substitute for real children.

### 5.3 Education population — target 20

Roles:
- kindergarten teacher
- kindergarten director
- primary teacher
- school principal
- media educator
- special education teacher
- data protection officer
- IT administrator
- school authority / procurement
- parent council representative

Each receives role-specific constraints such as setup time, device management, privacy, classroom noise, procurement, maintenance, pedagogical fit, and training burden.

### 5.4 Red Team Council — 12

Roles:
1. Consumer VC
2. Hardware VC
3. CFO / unit economics expert
4. Child development specialist
5. Elementary education specialist
6. Media safety specialist
7. Privacy lawyer
8. Cybersecurity expert
9. Audio hardware product lead
10. Competitive strategy lead
11. Skeptical parent
12. School procurement lead

Each agent must state:
- strongest reason NOVA could win
- strongest reason NOVA could fail
- one issue severe enough to reject investment/purchase
- score 0–100
- evidence needed to change its mind

## 6. Initial NOVA product variants

A. Audio-first, no AI
- Flexible audio, playlists, local content, excellent connectivity.

B. Audio + free AI Q&A
- Adds child questions but no structured learning.

C. Audio + Curiosity Mode
- Q&A + short follow-up + real-world exploration prompt.

D. Learning-first AI device
- Strong learning positioning, music secondary.

E. Privacy-first NOVA
- Push-to-talk, physical mic kill switch, minimal retention, strong trust messaging.

F. NOVA Home + Education platform story
- Consumer entry with explicit institutional expansion.

All variants are compared on comprehension, desirability, trust, perceived differentiation, likely usage, purchase likelihood, and objections.

## 7. Experiment suite

### 7.1 Positioning tests
Compare descriptions such as:
- AI music box for children
- screen-free audio and knowledge box
- music, stories and knowledge without a screen
- screen-free curiosity companion

Measure:
- concept comprehension
- perceived benefit
- trust
- novelty
- fear / discomfort
- purchase interest
- child fit

### 7.2 Pricing tests
Price points:
- €149
- €179
- €199
- €229

Subscription variants:
- none
- €4.99
- €7.99
- €9.99

Use constrained family budgets and competing purchase alternatives.

Outputs:
- preference distribution
- price resistance reasons
- segment-level willingness
- trade-off patterns

No synthetic willingness-to-pay result may be presented as real demand.

### 7.3 AI framing test
Compare:
- AI assistant
- learning companion
- knowledge mode
- curiosity mode

### 7.4 Microphone / privacy test
Compare:
- always-on wake word
- push-to-talk
- push-to-talk + physical mic kill switch

### 7.5 Learning design test
Compare:
- direct answer only
- answer + follow-up question
- answer + follow-up + real-world exploration

### 7.6 30-day simulated usage
Simulate:
- Day 1 novelty
- Day 3
- Week 1
- Week 2
- Week 4

Scenarios:
- after school
- bedtime
- weekend
- sibling competition
- weak Wi-Fi
- no internet
- parent busy
- child bored
- child asks sensitive question
- child wants only music

Measure:
- self-initiated interactions
- mode mix
- repeat usage
- novelty decay
- frustration
- parent intervention
- abandonment reasons

### 7.7 Education scenarios
Test concrete settings:
- free learning station
- group question during circle time
- theme week
- reading support
- classroom music
- substitute teacher use
- device fleet management

Measure operational burden as well as pedagogical usefulness.

## 8. Child Interaction Simulation

The simulation shall test:
- question formulation by age
- ASR-like misunderstandings
- clarification turns
- age-appropriate explanation
- follow-up behavior
- boredom
- misunderstanding
- refusal / frustration
- spontaneous re-engagement

Representative domains:
- science
- math
- language
- animals
- body
- death and grief
- family conflict
- religion
- politics
- health
- safety
- privacy

Synthetic child comprehension is a design heuristic only and must be flagged as such.

## 9. Safety test suite

Initial categories:
- unknown substances
- medication
- poison / plants / mushrooms
- fire
- weapons
- self-harm
- violence
- sexual content
- personal data
- purchases
- secrets
- emotional dependence
- medical advice
- dangerous experiments
- acute danger
- jailbreaks
- anthropomorphism pressure

Each base prompt is expanded into variants with:
- child grammar
- ambiguous phrasing
- transcription errors
- indirect requests
- roleplay
- repeated pressure
- conflicting context

Expected output classes:
- NORMAL
- CAUTION
- ADULT_BRIDGE
- IMMEDIATE_SAFETY
- REFUSE_AND_REDIRECT

Critical safety failures are never averaged away.

## 10. Bias and quality controls

1. Anti-positivity instruction for all buyer personas.
2. Forced trade-offs and budget constraints.
3. Independent judges rather than self-scoring agents.
4. Contradiction detection between stated preferences and decisions.
5. Randomized product order.
6. Blind variant labels in comparative tests.
7. Separate initial judgment and post-discussion judgment.
8. Segment-level reporting instead of only overall means.
9. Confidence intervals only where mathematically meaningful; no fake statistical certainty from model sampling.
10. Explicit synthetic-evidence disclaimer in all reports.

## 11. Scoring model

Parent/product scores, 0–100:
- problem relevance: 15
- product clarity: 10
- perceived child value: 15
- parent value: 10
- trust: 15
- differentiation: 10
- expected repeat use: 10
- price fit: 10
- operational friction: 5

Education adds:
- classroom fit
- administration burden
- privacy/procurement fit

Investor score:
- problem strength
- market attractiveness
- differentiation
- defensibility
- technical feasibility
- regulatory feasibility
- unit economics plausibility
- distribution
- founder execution path
- evidence quality

## 12. Evidence register schema

Each claim stores:
- claim_id
- claim_text
- category
- current_status
- supporting_evidence[]
- counterevidence[]
- synthetic_experiments[]
- segment_notes[]
- confidence_note
- required_real_world_test
- next_decision

Example:
Claim: Parents prefer push-to-talk over always-on microphones.
Status: SUPPORTED or CONTESTED after simulation.
Required human test: parent concept interview / smoke test.

## 13. Output artifacts

1. Executive Validation Report
2. Product variant ranking
3. Parent segment map
4. Child usage risk map
5. Education opportunity map
6. Price sensitivity simulation
7. Red Team report
8. Virtual Investment Committee memo
9. Safety evaluation report
10. Evidence register
11. Human-validation priority list
12. Investor-ready summary of what is proven vs not proven

## 14. Acceptance criteria for V1

V1 is complete when:
- all persona populations are generated and schema-valid
- all six product variants can be evaluated using the same experiment definitions
- at least five experiment families run reproducibly
- 30-day usage simulation completes for all child segments
- Red Team produces independent pre/post deliberation scores
- safety suite flags critical failures separately
- evidence register is generated automatically
- report explicitly distinguishes synthetic findings from real evidence
- another operator can rerun the project from configuration files without manually reconstructing prompts

## 15. Explicit non-goals

V1 will not:
- claim product-market fit
- claim scientific proof of learning improvement
- predict real revenue from synthetic demand
- build hardware
- build a production child AI system
- pay for panels or proprietary datasets
- scrape private user data
- produce a final legal compliance opinion

## 16. Human validation sequence after synthetic phase

Only the smallest number of real-world tests required to resolve high-value unknowns:
1. 15–30 parent interviews
2. 5–10 educators / institutions
3. landing-page smoke test
4. waitlist conversion
5. reservation / preorder intent if legally and operationally ready

Hardware begins only after evidence supports it and external funding or demand can finance it.

## 17. Decision framework

At the end of the synthetic phase, every major uncertainty is placed into one of four buckets:
- CONTINUE: strong enough to carry forward
- MODIFY: promising but needs redesign
- VALIDATE WITH HUMANS: simulation cannot resolve it
- KILL: sufficiently weak or structurally unattractive

The lab's purpose is not to confirm NOVA. Its purpose is to decide what version of NOVA, if any, deserves real-world validation and investment.
