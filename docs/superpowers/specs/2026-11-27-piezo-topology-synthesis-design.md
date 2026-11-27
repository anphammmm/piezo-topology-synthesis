# Piezoelectric harvester topology synthesis — design

## Requirements (from the researcher)

1. A program run from a Jupyter notebook on Panda (CAIR, JupyterLab at `/work`) that submits a
   cluster job which keeps running without the laptop.
2. A meaningful, challenging specification for a piezoelectric energy-harvesting interface circuit.
3. The experiment starts automatically: Gemma 4 31B proposes circuits, LTspice (Wine, batch mode,
   `ltspice-cpu` image, `/opt/ltspice/ltspice_run.py`) simulates them, results are checked against
   the spec, and the feedback improves later proposals. Changes in **connectivity** as well as values.
4. Every candidate is tested over several operating conditions (load, excitation, component
   parameters), compared with a reference circuit under the same conditions, and the selected
   design is checked on held-back conditions. If nothing meets the full spec, return the best
   candidate and list the failed conditions and criteria.
5. Practical run time, no repeated work, progress that shows whether the job is waiting for the
   model, simulating, or processing.
6. Report: spec, conditions, reference results, proposals, per-condition measurements and
   pass/fail, stop reason, time on model calls vs simulation, token counts; the selected circuit
   and raw results saved for reproduction and for figures/tables.

## Design decisions

- **Problem.** A piezo transducer (sinusoidal current source `Ip` at `f`, in parallel with `Cp`
  and `Rp`) must power a sensor-node load `RL` from a storage capacitor: output must reach and stay
  inside 1.8–3.6 V with low ripple, start up quickly from 0 V, and be settled. The full-bridge
  rectifier (FBR) is the reference; it fails at weak excitation (cannot reach 1.8 V), heavy load,
  and strong excitation/light load (overvoltage). Meeting all conditions needs a different
  topology class (e.g. SSHI-type switched-inductor inversion, voltage multipliers, clamps).
- **Circuit representation.** The model returns a JSON component list over a small primitive
  vocabulary (R, C, L, diode models, ideal-ish switch, synchronous switch controller) with
  reserved nodes `pzp`, `pzn`, `out`, `0`. The harness owns the piezo model, load, test bench
  and measurements, so the model cannot alter the test. This makes connectivity a first-class
  search variable and enables validation and duplicate detection.
- **Controller abstraction.** `SYNC` is an ideal synchronous pulse generator locked to the
  excitation's current zero crossings (where the piezo voltage peaks), a standard idealisation
  in SSHI/SECE literature. Its cost is charged as a 0.5 µA sink from `out` per instance.
- **Division of labour.** Gemma (thinking on) spends its reasoning on structure; a cheap
  coordinate search tunes component values between model calls, overlapping simulation with the
  model wait. Prompts are rebuilt each iteration from a compact state summary (no growing chat).
- **Held-out hygiene.** Held-out conditions never appear in prompts, scoring or stopping; they
  are evaluated once, on the selected design and the reference, after the search stops.
- **Deliverable.** One notebook that writes the package with `%%writefile` cells (single upload),
  submits the job, follows progress, and loads the results for tables and figures.
