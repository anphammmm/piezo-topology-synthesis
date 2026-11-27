# Paper: LLM-guided topology synthesis of piezoelectric harvesting interfaces

`main.tex` (IEEEtran, journal format) with `refs.bib`. Build with `pdflatex main && bibtex main &&
pdflatex main && pdflatex main`, or upload the folder to Overleaf. Packages: IEEEtran, amsmath,
graphicx, booktabs, xcolor, tikz, algorithm, algpseudocode, siunitx, cite.

## Where the numbers come from

Nothing in the results is typed by hand except the pilot run (Section VI-A), whose numbers come from the
first Panda runs (smoke test and the first search, before the screen and diagnostics existed).

- `generated/tab_conditions.tex`, `generated/tab_criteria.tex`: written from `piezo_synth/spec.py`.
- `generated/tab_reference.tex`, `generated/tab_screen_validation.tex`: reference and witness per condition, and the
  screen against full simulation, from the smoke-test run folder (already filled from the 2026-11-27 Panda smoke test).
- `generated/tab_variants.tex`, `generated/tab_cost.tex`, `generated/tab_screen_audit.tex`, `generated/macros.tex`:
  from the experiment campaign (`python3 -m piezo_synth.experiments runs/exp --paper paper/generated --smoke runs/smoke`).
- `generated/fig_variants.pdf`, `generated/fig_progress.pdf`: `python3 tools/paper_figures.py runs/exp paper/generated`.

All of `generated/` is currently filled from the 2026-11-27 campaign (40 runs). Cell 4 of `panda_sync.ipynb`
regenerates it on Panda into `runs/paper_generated` and publishes it on the `results` branch.

## Before submission

1. Re-run the random baseline at the full budget (`TASK = "random_rerun"`), regenerate `generated/`.
2. Only the author list is still marked `\pending`. The results text uses the macros of `generated/macros.tex`
   and counts from the run folders; re-check it if the random re-run changes the numbers.
3. Check every entry of `refs.bib` against the publisher's record; entries marked `VERIFY` were written
   from memory. Replace the Gemma entry with the model card or report of the exact model version.
4. Fill in authors and affiliations.
5. Add a schematic of the best synthesized design (Section VI-D) from `runs/exp/full/seed*/selected/circuit.json`.
