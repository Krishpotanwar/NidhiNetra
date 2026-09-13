# NidhiNetra — Pitch Script (5 speakers)

**SIH 2026 · SIH26102 · TechBashers · 6 slides · ~6 min 10 s**

Written to be read aloud, not read off a slide.

---

## Run of show

| # | Speaker | Slide | What they own | Time |
|---|---------|-------|---------------|------|
| 1 | [name] | 1 — Title | The problem, and why it goes unnoticed | 70 s |
| 2 | [name] | 2 — Proposed solution | What the system does and what it refuses to do | 80 s |
| 3 | [name] | 3 — Technical approach | The five-step pipeline | 80 s |
| 4 | [name] | 4 — Feasibility | Why it is buildable, and the three honest risks | 75 s |
| 5 | [name] | 5 and 6 — Impact, sources | Who benefits, the evidence, the close | 65 s |

Each speaker owns one part of the argument. Nobody repeats what the person before them said. Practise the handover lines out loud, because that is where teams normally lose ten seconds each.

---

## 1 — Slide 1 · 70 s
### The money moves. Nobody is watching.

> *Cue: Stand still. Do not read the slide. The slide is only the problem statement ID, so look at the judges instead.*

Good morning. We are team TechBashers, and our problem statement is SIH26102, from the Ministry of Statistics and Programme Implementation.

Every Member of Parliament gets a fund to build things in their own constituency. Roads, classrooms, water tanks, streetlights. The scheme is called MPLADS.

Here is how it works today. The money is released. The work is sanctioned. The bills are paid. And then, mostly, nobody looks closely until an audit arrives years later.

By that time, two things have already gone wrong. Some money has leaked out through inflated bills, or through works marked complete that were never actually built. And a much larger amount has simply sat there, unused. **Public reports put roughly 1,729 crore rupees as lying unspent.**

Now here is the part that bothers us. The data needed to catch all of this already exists. It is sitting in the MPLADS portal right now. **Nobody is reading it fast enough.**

So we built NidhiNetra. Nidhi means funds. Netra means eye. An eye on the money, while the money is still moving.

**Handover →** "[Name 2] will show you what the system actually does."

---

## 2 — Slide 2 · 80 s
### What goes in, what comes out

> *Cue: Use your hand to show "in" and "out". Slow down on the three categories. They are the spine of the whole pitch.*

NidhiNetra takes the raw MPLADS data and turns it into a ranked list of projects that deserve a closer look.

What goes in: fund release records, work sanction records, costs, and the geotagged photos of completed work.

What comes out: **every project gets a risk score from 0 to 100, and one line of plain language saying why.**

We look for three kinds of trouble.

First, anomalies. A road that costs three times what the same road costs in the next district. A work sanctioned two years ago that has not moved. The same entry filed twice.

Second, fraud signals. Billing that looks inflated. A photo that is missing, or that does not match the location claimed. The same vendor winning again and again.

Third, inefficiency. Long delays, funds lying idle, and the SC and ST spending quota not being met.

One thing matters more than everything else on this slide. **The system never accuses anyone.** It produces a recommendation with a reason attached, and a human officer decides what happens next. Nothing is published automatically.

**Handover →** "[Name 3] will take you through how it works, step by step."

---

## 3 — Slide 3 · 80 s
### Ingest, standardize, detect, explain, review

> *Cue: Point at each box on the flow diagram as you name it. Five steps, five points. Do not rush step two, it is the answer to a question judges love asking.*

Five steps. Ingest, standardize, detect, explain, review.

**Step one, ingest.** We pull the records from the MPLADS portal and store them.

**Step two, standardize.** Every state writes the same thing differently. One state writes "Community Hall", another writes "Comm. Hall". We map all of it into one common format. This step is unglamorous, and it is where most of the real work sits.

**Step three, detect.** Four engines run in parallel. Isolation Forest finds numbers that do not belong, mainly cost outliers. DBSCAN groups similar projects together, so we compare like with like instead of comparing a hill road to a plains road. Sentence-BERT reads the work descriptions and catches duplicates written in different words. And OpenCV checks the geotagged photo against the location that was claimed.

**Step four, explain.** This is the part we care about most. For every flag, we use SHAP or a plain rule trace to show exactly which fields pushed the score up. No black box. If we cannot explain a flag, we do not raise it.

**Step five, review.** Everything lands on a dashboard where an officer records what the inspection actually found. And every recorded outcome becomes training data for the next round. **The reviewers train the model, not the other way round.**

**Handover →** "[Name 4] will tell you why we think we can actually build this, and where it can go wrong."

---

## 4 — Slide 4 · 75 s
### Buildable, and honest about the risks

> *Cue: Say "now the honest part" and pause for one beat. Judges remember teams that name their own weaknesses before being asked.*

Three reasons this is buildable.

One. Every model we named is open source and light. Isolation Forest, DBSCAN, rule engines. No GPU farm required. This can run on the infrastructure the government already has.

Two. We are not starting blind. CAG audit reports and RTI replies already describe real fraud patterns in this exact scheme. We use those as our test cases, before we ever touch a live dataset.

Three. MPLADS uses the same fields in every state. So **one pipeline covers the whole country.** We do not rebuild it twenty-eight times.

Now the honest part. Three real risks.

Confirmed fraud is rare, so the data is heavily imbalanced. Our answer is to lead with unsupervised detection, which needs no labels, and add supervised models later, once confirmed cases build up.

State and district formats disagree with each other. Our answer is to spend real hackathon hours on standardization, not only on the models.

And the third one we take most seriously. **A false alarm against a named officer is not a small mistake. It damages a person.** Our answer is the human reviewer on every single flag. The system recommends. It never accuses.

**Handover →** "[Name 5] will close with who this helps, and what it is built on."

---

## 5 — Slides 5 and 6 · 65 s
### Who it helps, and what it stands on

> *Cue: Move through slide 5 and 6 without stopping. The last three sentences are the close. Land them slowly, then stop talking.*

Who this helps.

The Ministry gets a live risk view. Today they wait for the next audit cycle, which can take years. With this, a problem shows up in weeks.

That 1,729 crore of unspent funds becomes visible **early enough to actually spend it, inside the same financial year.**

And each user sees only what they need. An MP sees their own constituency. A district officer sees their district. The Ministry sees the country.

The benefits are three. Economic: less money lost to inflated bills and to works marked complete that were never built. Social: the SC and ST quota gets verified from the data, instead of being self-reported. Institutional: problem statement SIH26103 asks for an MPLADS monitoring portal. **We are not competing with it. NidhiNetra is the intelligence layer that plugs into it.**

All of this is grounded in public sources. The official MPLADS dashboard at mplads.mospi.gov.in. CAG and RTI records. And reported cases, including three officers chargesheeted in an MPLAD funds case, which is exactly the pattern we want to catch earlier.

To close. The data already exists. The misuse already leaves a trail. **NidhiNetra reads that trail while the money is still moving, and hands a ranked, explained list to a human who can act on it.**

Thank you. We are happy to take your questions.

---

## Questions the judges will ask

Whoever owned that slide answers the question, so nobody has to think about who speaks.

**How is this different from SIH26103?** (Speaker 5)
26103 is a monitoring portal. It shows what happened. We are the layer that decides what deserves attention, and explains why. We plug in rather than compete.

**Where does the data come from? Is there an API?** (Speaker 3)
The official MPLADS dashboard publishes state-level data through public endpoints, and we have tested them. Work-level detail is thinner than we need. So our ingest layer is built to accept an official feed the day it is available, and to work from published extracts until then.
*Do not oversell this. "We designed the ingest layer to swap sources" is a stronger answer than pretending the API is complete.*

**What if the model flags an honest officer?** (Speaker 4)
Three defences. Every flag carries a plain-language reason, so it can be argued with. Every flag goes to a human before anything is recorded. And we track precision on reviewed flags, so a noisy rule gets switched off.

**Cost variation is normal. Hills cost more than plains.** (Speaker 3)
Agreed, which is why we never compare against a national average. DBSCAN clusters projects by work type and region first, and we only look for outliers inside a cluster.

**With no labelled fraud data, how do you measure accuracy?** (Speaker 4)
Two ways. We replay known CAG and RTI cases and check whether our system would have ranked them highly. And in production, the measure is precision at the top of the list: of the flags a reviewer opens, how many were worth opening.

**Why not deep learning?** (Speaker 3)
Because we have to explain every flag to a government officer, we have very few confirmed cases to learn from, and it has to run on existing infrastructure. Classical models win on all three.

**What will you actually have built by the end of the hackathon?** (Speaker 2)
The full pipeline running end to end on real MPLADS data for a few states, a dashboard with ranked flags, and the explanation panel showing why each one was raised.

---

## Check these before you present

**The 1,729 crore figure.** The deck cites it without a year or a source. Pin down which financial year it refers to and which report it comes from. If a judge asks "as of when?" and nobody knows, the whole slide weakens.

**The data access answer.** From earlier probing, the MPLADS state-level endpoint responds but the work-level detail you need is not fully exposed. Agree as a team on the exact wording of that answer before you walk in, so all five of you say the same thing.

---

## Delivery notes

- Speak slower than feels natural. At six minutes you have room. Rushing is the most common way teams lose this round.
- Nobody reads the slide aloud. The slide is the evidence, you are the argument.
- Every speaker starts by looking at the judges, not the screen.
- Practise handovers as a chain, three times in a row, without the content. That alone saves half a minute.
- If a judge interrupts mid-pitch, answer it, then say "coming back to where we were" and continue. Do not restart the section.

### If you are cut to three minutes

Keep speaker 1 (drop the last two paragraphs), speaker 2 (keep the three trouble categories and the "never accuses" line), speaker 3 (name the five steps only, skip the model names), and speaker 5's closing three sentences. Speaker 4 becomes a single line: "every model we use is open source, and every flag goes to a human."
