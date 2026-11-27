# Paper: LLM-guided topology synthesis of piezoelectric harvesting interfaces

`main.tex` (IEEEtran, journal format) with `refs.bib`. Build with `pdflatex main && bibtex main &&
pdflatex main && pdflatex main`, or upload the folder to Overleaf. Packages: IEEEtran, amsmath,
graphicx, booktabs, xcolor, tikz, algorithm, algpseudocode, siunitx, cite.

## Where the numbers come from

Nothing in the results is typed by hand except the pilot run (Section VI-A), whose numbers come from the
first Panda runs (smoke test and the first search, before the screen and diagnostics existed).

- `generated/tab_conditions.tex`, `generated/tab_criteria.tex`: written from `piezo_synth/spec.py`.
- `generated/tab_reference.tex`: reference and witness per condition, from the smoke-test run folder.
- `generated/tab_variants.tex`, `generated/tab_screen_audit.tex`, `generated/macros.tex`,
  `generated/fig_variants.pdf`, `generated/fig_progress.pdf`: from the experiment campaign.

All of `generated/` is produced by the notebook's **Aggregate** cell (it calls
`python -m piezo_synth.experiments runs/exp --paper paper_generated --smoke runs/smoke` and draws the
figures). Download `paper_generated.zip` from Panda and unpack it here as `generated/`. Until then the
tables say "pending" and the figures are placeholder boxes.

## Before submission

1. Run the smoke test again (device models changed), then the campaign, then Aggregate; replace `generated/`.
2. Search `main.tex` for `\pending`: each marks text that can only be written from the results
   (red in the PDF). Write those paragraphs from the generated tables; claim differences between
   variants only where the five seeds support them.
3. Check every entry of `refs.bib` against the publisher's record; entries marked `VERIFY` were written
   from memory. Replace the Gemma entry with the model card or report of the exact model version.
4. Fill in authors and affiliations.
5. Add a schematic of the best synthesized design (Section VI-D) from `runs/exp/full/seed*/selected/circuit.json`.
