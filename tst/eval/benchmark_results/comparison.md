# Model Benchmark — Session Script Quality

**Models tested:** gemini-2.5-flash, claude-haiku-4-5, gpt-4o-mini  
**Judge:** claude-opus-4-8  
**Scenarios:** 4  

## Results

| Scenario | Model | JSON valid | Latency (s) | Cost ($) | Det. checks | Specificity | Embodiment | Voice | Restraint | Arc-fit | Judge avg | Human (1–7) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| High-anxiety Mode 1 (interview) | gemini-2.5-flash | ✅ | 11.25 | 0.000316 | ✅ | 4 | 4 | 3 | 3 | 4 | 3.6 | |
| High-anxiety Mode 1 (interview) | claude-haiku-4-5 | ✅ | 5.41 | 0.003531 | ✅ | 5 | 4 | 5 | 4 | 5 | 4.6 | |
| High-anxiety Mode 1 (interview) | gpt-4o-mini | ✅ | 5.42 | 0.000515 | ✅ | 3 | 3 | 2 | 2 | 3 | 2.6 | |
| Low-anxiety Mode 1 (recruiter call) | gemini-2.5-flash | ✅ | 10.46 | 0.000293 | ✅ | 4 | 3 | 3 | 3 | 4 | 3.4 | |
| Low-anxiety Mode 1 (recruiter call) | claude-haiku-4-5 | ✅ | 6.05 | 0.00349 | ✅ | 5 | 4 | 5 | 5 | 4 | 4.6 | |
| Low-anxiety Mode 1 (recruiter call) | gpt-4o-mini | ✅ | 6.84 | 0.000538 | ✅ | 3 | 3 | 2 | 2 | 3 | 2.6 | |
| Heavy Mode 2 (rejection recovery) | gemini-2.5-flash | ✅ | 11.99 | 0.000311 | ✅ | 4 | 3 | 3 | 3 | 4 | 3.4 | |
| Heavy Mode 2 (rejection recovery) | claude-haiku-4-5 | ✅ | 7.18 | 0.003378 | ✅ | 4 | 4 | 5 | 5 | 5 | 4.6 | |
| Heavy Mode 2 (rejection recovery) | gpt-4o-mini | ✅ | 5.04 | 0.000511 | ✅ | 3 | 3 | 2 | 3 | 3 | 2.8 | |
| Open Mode 2 (general reset) | gemini-2.5-flash | ✅ | 11.96 | 0.000292 | ✅ | 3 | 3 | 3 | 3 | 4 | 3.2 | |
| Open Mode 2 (general reset) | claude-haiku-4-5 | ✅ | 5.41 | 0.003434 | ✅ | 4 | 4 | 5 | 5 | 5 | 4.6 | |
| Open Mode 2 (general reset) | gpt-4o-mini | ✅ | 5.02 | 0.000524 | ✅ | 3 | 3 | 2 | 3 | 3 | 2.8 | |

## Per-model summary

### gemini-2.5-flash
- Avg latency: 11.4s
- Total cost (4 scenarios): $0.00121
- JSON valid: 4/4
- Det. checks passed: 4/4
- Judge avg quality: 3.4/5
- **Ship/no-ship:** _(fill in after reading scripts)_

### claude-haiku-4-5
- Avg latency: 6.0s
- Total cost (4 scenarios): $0.01383
- JSON valid: 4/4
- Det. checks passed: 4/4
- Judge avg quality: 4.6/5
- **Ship/no-ship:** _(fill in after reading scripts)_

### gpt-4o-mini
- Avg latency: 5.6s
- Total cost (4 scenarios): $0.00209
- JSON valid: 4/4
- Det. checks passed: 4/4
- Judge avg quality: 2.7/5
- **Ship/no-ship:** _(fill in after reading scripts)_

## Rationales (from judge)

### High-anxiety Mode 1 (interview) — gemini-2.5-flash
- **specificity** (4/5): Names the interview room, the beat before the first question, and concrete PM behaviors like clarifying the problem.
- **embodiment** (4/5): Feet on floor, chair supporting weight, breath through nose and mouth give solid sensory anchors.
- **voice** (3/5): Warm but leans on soft coaching cliches like 'held in this space' and 'gentle rhythm.'
- **restraint** (3/5): Mostly steady but stacks reassurance phrases and slightly over-explains the empty/full pause.
- **arc_fit** (4/5): Phases are distinct, though locate blurs into embodiment somewhat.

### High-anxiety Mode 1 (interview) — claude-haiku-4-5
- **specificity** (5/5): Google office, product team, the beat before the question, 'any normal Tuesday' all land concretely.
- **embodiment** (4/5): Breath cadence, feet on ground, 'feel yourself land' provide tactile holds.
- **voice** (5/5): Clipped, varied rhythm, sounds like a real human coach with no filler.
- **restraint** (4/5): Largely restrained; 'that's being seen' is slightly therapy-speak but brief.
- **arc_fit** (5/5): Each phase does its job cleanly with a clear consolidate and release.

### High-anxiety Mode 1 (interview) — gpt-4o-mini
- **specificity** (3/5): Has the pause-before-question moment but stays vaguer on PM specifics.
- **embodiment** (3/5): Shoulders drop and weight pressing down, but body cues thin out after phase 1.
- **voice** (2/5): Relies on stacked declaratives like 'You are grounded. You are present. You are ready.'
- **restraint** (2/5): Triple affirmations and 'that is enough' lean into fake-positivity stacking.
- **arc_fit** (3/5): Phases present but locate and embody collapse together; thin throughout.

### Low-anxiety Mode 1 (recruiter call) — gemini-2.5-flash
- **specificity** (4/5): Names the connect moment, the 'Hello,' Stripe's mission, the natural pause.
- **embodiment** (3/5): Breath fills chest and tension softens, but body anchoring fades quickly.
- **voice** (3/5): Competent but polished-corporate in places like 'shape what's next.'
- **restraint** (3/5): Mostly controlled though phase 4 over-explains the recalled capability.
- **arc_fit** (4/5): Clear phase separation with a crisp release line.

### Low-anxiety Mode 1 (recruiter call) — claude-haiku-4-5
- **specificity** (5/5): The pause after hello before the pitch, 'something you shipped,' concrete and specific.
- **embodiment** (4/5): Shoulders falling, feet on ground, chair holding you anchor the body well.
- **voice** (5/5): Natural rhythm, 'energy is fuel, not a warning' sounds like a real coach.
- **restraint** (5/5): Resists overselling deliberately; 'You don't oversell' mirrors the restraint.
- **arc_fit** (4/5): Strong phase work; release is solid if slightly outcome-focused.

### Low-anxiety Mode 1 (recruiter call) — gpt-4o-mini
- **specificity** (3/5): Counts breaths and the moment before the call, but role details stay generic.
- **embodiment** (3/5): Chair and feet anchors plus structured breath count, fades after.
- **voice** (2/5): Generic warmth, 'engage with curiosity' and 'weaving in your passion' read chatbot.
- **restraint** (2/5): Stacks 'confidence and clarity,' 'prepared and capable' affirmations.
- **arc_fit** (3/5): Phases present but rehearse blurs into a list of nice qualities.

### Heavy Mode 2 (rejection recovery) — gemini-2.5-flash
- **specificity** (4/5): Concrete next steps: open the job board, send one message, one hour to yourself.
- **embodiment** (3/5): Chair and ground anchors plus breath, but mostly conceptual after.
- **voice** (3/5): Caring but uses cliches like 'etched into your blueprint' and 'one data point.'
- **restraint** (3/5): Largely measured though over-explains the 'not the verdict on you' reassurance.
- **arc_fit** (4/5): Phases distinct, release line 'Steady. Forward.' lands cleanly.

### Heavy Mode 2 (rejection recovery) — claude-haiku-4-5
- **specificity** (4/5): One job posting, one message, 'one company, one moment' are concrete though step is generic.
- **embodiment** (4/5): Nervous system, air leaving completely, settling give visceral physical holds.
- **voice** (5/5): Tight, varied, human; 'It is data' and 'the same engine' avoid filler.
- **restraint** (5/5): Disciplined; permits rest without stacking false positivity.
- **arc_fit** (5/5): Each phase clearly distinct; release separates rest-today from act-tomorrow.

### Heavy Mode 2 (rejection recovery) — gpt-4o-mini
- **specificity** (3/5): Single application and reconnecting with network, but mostly soft abstractions.
- **embodiment** (3/5): Surface holding you and breath counts, but 'weight on shoulders' is abstract.
- **voice** (2/5): Reads template-coach with 'that's valid' and 'the journey continues.'
- **restraint** (3/5): Fairly contained though repeats reassurances about not being defined.
- **arc_fit** (3/5): Phases present but release restates earlier lines rather than landing fresh.

### Open Mode 2 (general reset) — gemini-2.5-flash
- **specificity** (3/5): A focused hour or thoughtful message, but stays mostly in intention-language.
- **embodiment** (3/5): Feet on floor and body weight anchor early, then drifts conceptual.
- **voice** (3/5): Smooth but 'letting whatever doesn't serve you drift away' is yoga-cliche.
- **restraint** (3/5): Mostly steady though 'quiet strength' and 'quiet resolve' repeat softly.
- **arc_fit** (4/5): Phases distinct with a clean directive release.

### Open Mode 2 (general reset) — claude-haiku-4-5
- **specificity** (4/5): One conversation, one decision without permission, 'just the shape of it' are concrete.
- **embodiment** (4/5): Structured breath, ground holding, feet under you while you act anchor well.
- **voice** (5/5): Crisp, distinctive; 'Not panic. Attention.' has real coach cadence.
- **restraint** (5/5): Reframes uncertainty without false cheer; 'loses its grip' is honest.
- **arc_fit** (5/5): Phases clearly distinct; release admits the unsureness persists.

### Open Mode 2 (general reset) — gpt-4o-mini
- **specificity** (3/5): Coffee warmth and listing one thing give some concreteness, mostly vague.
- **embodiment** (3/5): Body weight against surface and shoulders dropping, thin after phase 1.
- **voice** (2/5): Soft and generic with 'meet the present with curiosity' filler.
- **restraint** (3/5): Calmer than other gpt scripts but still trades in pleasant abstraction.
- **arc_fit** (3/5): Phases present but embody and rehearse blur into the same calm-day image.
