# MutationRx — 3-minute pitch (voice-over + screen)

*Delivery: calm, unhurried. Pause at each blank line. ~3 minutes.*
*Pronunciation: MutationRx = "Mutation R-X". imatinib = "ee-mah-TEE-nib". diagnosed = "die-ag-NOHZD".*
*Format: voice-over only (no face). Opening = animation; from "So we built MutationRx" = screen recording of the live site.*

---

**[SCREEN: opening animation, no text, no faces. A glowing medicine molecule clicks neatly into a pocket on a large protein, like a key into a lock, in warm hopeful light. Then the protein slowly warps, the pocket changes shape, and the molecule drifts away into soft darkness.]**

Imagine you are sick with cancer. You finally find a drug that works. The tumor gets smaller. For a while, you have your life back.

Then one day, it stops working. Not because the drug changed. Because the cancer changed. It changed its shape, just a little, so the drug can no longer hold on.

This happens to almost everyone who takes these targeted drugs. It is not rare. It is the expected ending. And when it happens, the question is simple and painful: what do we try next?

**[SCREEN: simple animation — a screen fills with dozens of drug names, each getting a green check; too many, cluttered; then most of the checks flip to red.]**

Today, answering that means slow and costly lab work. Many months, and real money. Computers can guess faster, but they have one big problem. They say yes to too many drugs. They give good scores to drugs that would never really work. So scientists stop trusting them, and the slow search goes on.

**[SCREEN: cut to screen recording — open mutationrx.onrender.com, the home page with the spinning 3D structure.]**

So we built MutationRx. You give it a tumor's mutation.

**[SCREEN: left sidebar, under "Real patient tumors," click TCGA-L9-A50W-01. The staged pipeline plays: modeling, docking, rescoring, classifying.]**

It takes a group of approved drugs, and it measures how well each one still fits the changed protein.

**[SCREEN: the result appears — the three tiles (Avoid / Still binds / To review) and the green "Reproduces known biology" badge.]**

It shows you, with honest error bars, which drugs lose their grip, and which ones still hold on.

**[SCREEN: scroll to "Claude's read" — the plain-English review.]**

But here is the key idea. A good score is not the same as a real drug. So after the measuring, Claude reviews every result, and asks one question: does this drug make sense for this target? It keeps the real leads, and it removes the lucky matches.

**[SCREEN: expand "Full evidence," scroll to the "Improved" section — show the surprising drug names: rimonabant, moxifloxacin, amitriptyline, and the rest.]**

Let me show you why this matters. We tested a library of three hundred approved drugs against a resistant lung tumor. The math marked ten of them as strong, confident hits.

Every single one was a false alarm. Antidepressants. Antibiotics. Drugs with nothing to do with this cancer. They simply happened to fit the shape. A tool without Claude would send the scientist to test all ten, and waste months.

**[SCREEN: scroll up to Claude's read, to the "Library screen" paragraph; land on the sentence naming imatinib. Then flick to the "Orthogonal evidence" strip: imatinib leads it as in-class, while the coincidental hits below are flagged off-pathway with no dependency (grey), so the reasoning is shown, not just asserted.]**

Claude removed all ten. And it saved one quiet lead that the math almost missed: a blood cancer drug called imatinib. Nobody uses it for lung cancer. But imatinib works by blocking the same kind of protein this lung cancer depends on. So it makes biological sense. It is not a random match. And something surprising happened in our tests: most drugs fit the mutated protein worse, but imatinib fit it even better, every single time. That is a real lead — an idea worth testing in the lab.

**[SCREEN: back to the top of the result — the verdict tiles. Then a closing card: "The docking finds candidates. Claude decides which to believe." and mutationrx.onrender.com]**

So that is the whole point. The computer finds the candidates. Claude decides which ones to believe.

For a scientist, this turns weeks of guessing into minutes. For a patient, it makes the path from "my drug stopped working" to "here is the next thing to try" shorter.

A few months ago, my cousin was diagnosed with cancer. So for me, this is not abstract. Behind every one of these mutations, there is a person, and a family, waiting for that next answer. That is why we built it.

Thank you.
