# AI-assisted topology synthesis: piezoelectric energy-harvester interface

Gemma 4 31B proposes interface-circuit structures for a piezoelectric harvester, up to three per round.
Each new structure is **screened** cheaply (net power at a fixed 1.8 V output), then **evaluated** in
full with LTspice on six operating conditions, then **sized** by an evolution strategy while the model
thinks about the next round. The measurements, screen powers and plain-language diagnoses drive the
next round. The program runs as CPU jobs on Panda, started from a notebook. The paper describing it is
in `paper/`.

**Deliverable:** `piezo_synth.ipynb`. It contains the whole package (written to `piezo_synth/` by
`%%writefile` cells), the job submission, progress checks and the analysis. Upload that one file.

## How to run

1. In JupyterLab on Panda, make a folder of your own under `/work` and upload `piezo_synth.ipynb` into it
   (jobs run in the notebook's folder and write their files there).
2. Run **1. Setup** and the collapsed **2. Package files** cells. They write `piezo_synth/`.
3. Adjust **3. Settings** if you want, and run it.
4. First time only: run **4. Smoke test** (about 2 minutes) and check it as described in "First run" below.
5. Run **5. Single run**. It submits the job (`image=ltspice-cpu`, `gpus=0`, `cpus=8`, `16Gi`, 4 h
   limit) and follows its log. You can close the laptop; reopen the notebook and run the **Progress** cell
   to see where it is. Stopping `log()` only stops watching; `cancel(job)` stops the job.
6. When it finishes, run **Results**, **Figures** and **Waveforms**.
7. For the paper: run **7. Experiment campaign** (8 variants x 5 seeds, one job per variant, all with the
   same simulation budget), check it with the status cell, then run **Aggregate**. Download
   `paper_generated.zip`, unpack it into `paper/generated/` and compile `paper/main.tex`.

Expected run time with the default settings: 30-60 minutes, dominated by the model's thinking time.
LTspice runs under Wine with a shared prefix in `/work/.wine-ltspice`. If parallel jobs interfere (Wine
errors in `sims/*/*.log`), submit the campaign's variants one after another instead of all at once.

To run the code from GitHub on Panda and publish the results back (a `results` branch), use
`panda_sync.ipynb` and `docs/panda-sync.md` (in Vietnamese). To let Claude Code run the experiments itself from the notebook's terminal on Panda, see
`docs/panda-claude-setup.md` (setup, in Vietnamese) and `CLAUDE.md` (its instructions);
`tools/panda_submit.py` and `tools/panda_campaign.py` submit jobs from that terminal.

Without the cluster, `python -m piezo_synth.run --fake --out runs/dry` runs the whole pipeline with a
scripted model and an analytic stand-in for LTspice (numbers are not circuit simulations), and
`python -m unittest discover -s tests -t .` runs the tests.

## The specification

A piezo transducer is modelled as a sinusoidal current source `Ip sin(2 pi f t)` in parallel with
`Cp` (25 nF nominal) and 20 MOhm. It must supply a sensor-node load `RL` from a storage capacitor at node
`out`. Under **every** condition, in a 0.8 s cold-start transient from 0 V:

| criterion | requirement | why |
|---|---|---|
| vout_min | mean V(out) over 0.7-0.8 s >= 1.8 V | minimum supply of the load |
| vout_max | V(out) never above 3.6 V | absolute maximum of the load |
| ripple | peak-to-peak over 0.7-0.8 s <= 50 mV | supply quality |
| startup | first reaches 1.8 V within 0.4 s | cold start |
| settled | mean changes <= 20 mV between 0.6-0.7 s and 0.7-0.8 s | the measurement is steady state |

Conditions used during the search (S) and held out (H):

| id | description | Ip uA pk | f Hz | Cp nF | RL kOhm | T C |
|---|---|---|---|---|---|---|
| S1 | nominal | 50 | 100 | 25 | 330 | 27 |
| S2 | heavy load | 50 | 100 | 25 | 150 | 27 |
| S3 | strong excitation, light load | 100 | 100 | 25 | 2200 | 27 |
| S4 | weak excitation | 30 | 100 | 25 | 1000 | 27 |
| S5 | low frequency | 40 | 80 | 25 | 470 | 27 |
| S6 | Cp +20 %, hot | 50 | 100 | 30 | 330 | 60 |
| H1 | weak excitation, mid load | 35 | 100 | 25 | 470 | 27 |
| H2 | high frequency, Cp -15 % | 60 | 120 | 21.25 | 220 | 27 |
| H3 | very strong excitation, open load, cold | 120 | 100 | 25 | 10000 | -20 |
| H4 | hot, heavy load | 50 | 100 | 25 | 200 | 85 |

Why it is challenging: the open-circuit piezo voltage is only about 3.2 V at nominal excitation, so the
full-bridge rectifier (the **reference**) loses much of it to diode drops and to charging `Cp` every half
cycle. It cannot reach 1.8 V under weak excitation or heavy load, and with strong excitation and a light
load it overshoots 3.6 V. Passing everything needs a different structure, for example synchronous
switched-inductor inversion (SSHI-type), a voltage multiplier, an overvoltage clamp, or combinations,
plus a storage capacitor that balances ripple against start-up time. These estimates are checked by the
smoke test; edit the tables in `piezo_synth/spec.py` to change the spec.

## Design choices

- **Circuits as structured data.** The model returns `{"proposals": [...]}`, each design a JSON list of
  components over a fixed vocabulary: R, C, L, diodes (`DSCH` Schottky, `DSI` silicon, `DZ33` 3.3 V zener),
  switches and `SYNC` controllers, connected through named nodes, with reserved nodes `pzp`, `pzn`
  (piezo), `out` and `0`. The program adds the piezo model, the load, the measurements and the device
  models, so the model can change connectivity freely but cannot alter the test. Every design is
  validated before simulation (including diode orientation: a diode from `out` to ground is rejected).
- **Structures, not values, are the model's job.** Two designs with the same connectivity (canonical graph
  hash, node names and values ignored) are the same structure; a repeat is not simulated again.
- **Stage 1, power screen** (`screen.py`). The storage node is fixed at 1.8 V by a source behind a 100 Ohm
  sense resistor and the net power into it is averaged over 4 cycles of a 10-cycle run, on S2, S4 and S6.
  If the net power is below the load's need `1.8^2/RL` the output cannot hold 1.8 V there whatever the
  storage capacitor, so this is a necessary condition for `vout_min`. Values are untuned at this point,
  so the screen tries a few presets (proposed values, `ton = pi sqrt(L Cp)` and half of it, random
  spreads) and passes a structure if the best preset reaches `screen_alpha` (0.5) of the need. This is
  the same idea as a relaxed DC-gain filter for unsized amplifiers (Zhao and Zhang, TCAD 2022). A screen
  run costs about 1/8 of a full simulation. The `audit` variant measures how often it rejects a structure
  that sizing could have made to work.
- **Stage 2, full evaluation** with the best preset's values: 0.8 s cold start on the six search conditions.
- **Stage 3, sizing** (`sizer.py`): an elitist (1+8) evolution strategy in log-value space with a
  success-based step size. Each generation is 8 designs x 6 conditions simulated in parallel. Sizing
  runs while the model is thinking; it is resumable, always works on the most promising unfinished
  structure, stops a structure when it meets the spec, uses up `size_budget` evaluations or converges,
  and after the last round finishes the best `drain_top` structures. Structures whose output never
  reaches 0.9 V are not sized (a wiring error, not a value problem).
- **Diagnoses in the feedback** (`diagnostics.py`): besides the tables, each result is explained in plain
  terms (no output at all and what usually causes it, too little power on which conditions, overvoltage,
  slow start, drift, ripple, simulation failure). They name the symptom, not a fix, so they do not steer
  the model toward a known topology. If the last three designs share a major problem, the prompt says so.
- **Controller abstraction.** `SYNC` is an ideal pulse generator locked to the zero crossings of the piezo
  current, where the piezo voltage peaks, as in SSHI/SECE studies. It tracks frequency automatically.
  Its cost is modelled as a 0.5 uA supply current drawn from `out` per controller. Inductors carry a
  series resistance of 2 Ohm + 5 Ohm/mH. The Monte Carlo check perturbs the switch timing to show how
  much the result depends on the ideal controller.
- **Stateless prompts.** Each prompt is rebuilt from a compact summary (best four structures with tables,
  screen powers, sizing status and diagnoses, every result of the last round, all structures explored)
  instead of a growing chat, which keeps prompt size, and with it the model's time, bounded.
- **Avoiding repeated work.** Successful simulations are cached by the exact netlist text; repeated
  structures are not re-simulated; screen presets, conditions and sizing generations run in parallel.
- **Held-out hygiene.** Held-out conditions never appear in prompts and are not used for scoring,
  selection or stopping. They are simulated once, for the selected design and the reference, after the
  search has stopped. The selected design is the best one on the search conditions.
- **Robustness** (`robust.py`): the selected design is simulated on all 10 conditions for `mc_samples`
  samples with R +/-5 %, C +/-20 %, L +/-10 %, switch on-time +/-5 % and switch timing +/-2 % of a period.
- **Scoring.** Per check, margin = (measured - limit)/scale (sign so that positive passes; a missing
  measurement counts as -1). Score = 10 x conditions fully passed + checks passed + the sum of negative
  margins (each clipped at -1) + 0.05 x the sum of positive margins (each clipped at 0.5). Ties go to the
  design with fewer components.
- **Stop rules** (first that applies): `search_spec_met`, `model_done` (after `min_rounds`),
  `model_unavailable` (three failed model calls in a row), `stagnation` (no gain of 0.01 in the best
  proposed design for `stagnation` rounds, after `min_rounds`), `time_budget`, `sim_budget`,
  `round_budget`. A model call that hangs is abandoned `model_grace_s` after the wall-clock budget.
- **Comparisons for the paper.** `--baseline random` replaces the model by random valid circuits through
  the same screen and sizing; config switches turn off the screen, the diagnoses, multiple designs per
  round, the evolution strategy (back to coordinate search) or the model's reasoning. All variants share
  a simulation budget (`max_sims`) so they are compared by simulations used, which does not depend on the
  load on the shared model server. `python -m piezo_synth.experiments runs/exp --paper paper/generated`
  aggregates them.

## Interpreting the results

Everything is in `runs/<RUN_ID>/`:

| file | contents |
|---|---|
| `report.md` | specification, conditions, reference results, every proposal, the selected design per condition, the held-out check, unmet requirements, stop reason, time and tokens |
| `summary.json` | stop reason, whether the spec was met (search / all), selected design, every failed check, timing |
| `selected/circuit.json`, `selected/<cond>.net` | the selected design and its exact LTspice netlist for each of the 10 conditions |
| `proposals.csv` | one row per design the model proposed: invalid, duplicate, screen_failed or evaluated, with screen power ratios and gains over the ideal bridge |
| `candidates.csv` | one row per design evaluated: origin (`reference`, `llm`, `size`, `audit`), move, topology hash, score, conditions passed |
| `robust.json`, `reference_screen.json` | Monte Carlo pass rates; the reference's screen powers |
| `measurements.csv` | every measurement per design and condition (`vavg`, `vmax`, `vpp`, `tup`, `pload`, `pext`, `dv`) |
| `checks.csv` | every pass/fail decision with measured value, limit and margin |
| `llm/iter-NN-a.json` | each prompt, the model's answer, its reasoning text and token counts (NN = round) |
| `events.jsonl` | timeline of the run |
| `timing.json` | wall time, time in model calls, tokens (prompt, completion, reasoning if reported), simulations, cache hits, simulator time |
| `sims/<hash>/` | LTspice netlist and log of every simulation (the `.raw` waveform is deleted once measured, to save disk; `reproduce --waveforms` keeps it) |
| `figures/` | PNG and PDF figures produced by the notebook |

- **Unmet requirements** in `report.md` (and `failed_checks` in `summary.json`) list every condition and
  criterion the selected design fails, with measured value, requirement and margin. This is how a run
  that did not meet the full spec reports its best candidate.
- **Held-out check**: compare the selected design and the reference on H1-H4. Failures there and not on
  the search set show over-fitting to the search conditions.
- **Time**: model and simulation times overlap (sizing runs while the model thinks) and simulations run
  in parallel, so the sums can exceed the wall time.
- `pext` is the average power delivered by the piezo source; `pload` the power in `RL`. Their ratio is
  a rough end-to-end efficiency, useful for comparing topologies.

## Reproducing and inspecting

- Disk: each run prints the free space at start and warns below 2 GiB. Runs made before this change left
  their `.raw` files behind: `python3 tools/clean_raw.py runs` reports how much they take, `--delete` removes them.

- Re-simulate any design: `python3 -m piezo_synth.reproduce runs/<RUN_ID>/selected/circuit.json --out
  <dir> --conditions all --waveforms` (as a job with `image=LTSPICE, gpus=0`; the Waveforms cell does this).
  `--waveforms` keeps full, uncompressed `.raw` files; `piezo_synth.rawread.read_raw` loads them.
- Rebuild the report of any run, including one that was killed: `python3 -m piezo_synth.report runs/<RUN_ID>`.
- Open `selected/<cond>.net` in LTspice on your computer to look at it interactively.
- Screen presets and sizing are seeded (`seed`); the model is not deterministic, so repeated runs differ.

## First run (smoke test checklist)

1. The smoke job finishes 26 simulations (20 full, 6 screen), each in under about 15 s, and writes
   `runs/smoke/report.md`.
2. The reference's `P_ext` on S1 is positive. If the job printed a WARNING that it is not, flip the sign of
   the `pext` `.meas` line in `piezo_synth/netlist.py` (only the `P_ext` column is affected).
3. The reference fails at least S2, S3 and S4. If it passes everything, the spec is too easy: lower `rl`
   for S2 or `ip` for S4 in `spec.py` and repeat.
4. The witness's `t_up` values are crossing times (not all exactly 1.8); the job prints a WARNING otherwise,
   meaning ltspice_run reads the wrong number from the `tup` line.
5. The witness (a hand-made SSHI + bridge + zener clamp, never shown to the model) passes more conditions
   than the reference. If it passes none, look at `runs/smoke/sims/*/*.log` for convergence errors
   before starting the full run. The witness does not have to pass everything: it only shows that the
   building blocks work.
6. The `[screen]` lines give the net power of the reference and the witness at 1.8 V. The reference's
   powers must be positive (the job warns otherwise: then the sense-resistor measurement has the wrong
   sign). The witness should pass the screen; if it does not, lower `screen_alpha` in the settings.
7. Then run a single run and check for `[model] waiting ...` heartbeats, `[screen]`, `[size]` and `[sim]`
   lines, a final `search stopped:` line, and `report.md`, `summary.json` and `figures/` in the run folder.

## Observed performance

(Fill in after the first runs: Wine start-up per simulation, seconds per simulation, seconds per model call.)

## Known limitations

- The controller is ideal (perfect synchronisation, fixed supply current); real peak detectors add delay
  and consume more power at start-up. The Monte Carlo check perturbs its timing but does not model a
  real detector.
- The screen fixes the output at 1.8 V; a structure that only works at a higher storage voltage could
  be rejected. The `audit` variant measures this.
- Device models are generic (Schottky, silicon, zener, switch); there is no layout, no parasitic
  capacitance beyond the models, and no mechanical coupling (the piezo current does not depend on the
  electrical load).
- The 0.8 s window measures cold start and early steady state; designs with much longer time constants
  are judged as not settled.
