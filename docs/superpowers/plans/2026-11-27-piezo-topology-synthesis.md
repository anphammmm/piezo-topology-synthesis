# Piezo Harvester Topology Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A notebook-launched Panda job in which Gemma 4 31B proposes piezoelectric-harvester interface circuits (topology and values), LTspice evaluates them over multiple operating conditions against a fixed spec, feedback drives later proposals, and the selected design is compared with a full-bridge reference and checked on held-out conditions, with a complete reproducible record.

**Architecture:** A stdlib-only Python package `piezo_synth` runs inside one `ltspice-cpu` CPU job. Circuits are JSON component lists over a fixed primitive vocabulary; the harness wraps them in a fixed piezo/load/test-bench netlist per condition, simulates conditions in parallel with a content-hash cache, and scores measurements against criteria. Each iteration runs the Gemma call in a background thread while the main thread spends that time on value refinement of the current best topology. Everything is logged incrementally under `runs/<run_id>/`; a notebook generated from the sources writes the package with `%%writefile`, submits the job, and analyses the outputs.

**Tech Stack:** Python ≥3.8 (stdlib + `requests`) in the job; LTspice 26 via Wine through `/opt/ltspice/ltspice_run.py`; Gemma 4 31B (vLLM, OpenAI-compatible API); pytest locally; pandas + matplotlib in the notebook kernel only.

**Spec:** `docs/superpowers/specs/2026-11-27-piezo-topology-synthesis-design.md` (requirements and design rationale; the numeric experiment spec is pinned in Task 1 below).

## Global Constraints

- Job code imports only the Python standard library and `requests`; no numpy/pandas inside `piezo_synth/` (except `tools/` and the notebook's analysis cells). Python 3.8 syntax: `from __future__ import annotations`, no `match`, no PEP 604 unions at runtime.
- Gemma endpoint `http://gemma-4-31b.cpd-instance.svc:3000/v1/chat/completions`, model `google/gemma-4-31b`, no key; thinking via `"chat_template_kwargs": {"enable_thinking": true}`.
- LTspice backend: `sys.path.append("/opt/ltspice"); from ltspice_run import simulate`; `simulate(netlist_text, folder, timeout=...)` returns an object with `.ok`, `.meas` (dict name→float), `.error`, `.folder`.
- Job submission: `image=LTSPICE` (`image-registry.openshift-image-registry.svc:5000/<namespace>/ltspice-cpu:latest`), `gpus=0`, `cpus=8`, `memory="16Gi"`, `timeout=4*3600`.
- Only one job using `/work/.wine-ltspice` at a time; parallelism is threads inside the job.
- Held-out conditions never appear in any prompt, in scoring during the search, in candidate selection, or in stop rules.
- All outputs live under `runs/<run_id>/` and are written incrementally (append/atomic replace), so a killed job leaves a usable record.
- LTspice and Gemma are not available on the development machine: every automated test uses fakes; real-environment validation is Task 12, run on Panda.

## Review Focus

1. Gemma returns well-formed JSON for a circuit LTspice cannot solve (singular matrix, timestep too small, timeout) → that design scores as failing every check on the affected conditions, the model is told the simulator error, and the loop continues. *(test: Task 9 `test_search_survives_sim_failure`)*
2. The Gemma service is down or returns HTTP 5xx/timeouts → `GemmaClient` retries 3× with backoff and returns an `LLMReply` with `error` set, the iteration is logged as skipped, and after 3 consecutive failed iterations the run stops with reason `model_unavailable` and still writes the report. *(tests: Task 6 `test_ask_retries_then_reports_error`, Task 9 `test_search_stops_when_model_unavailable`)*
3. Output never reaches 1.8 V, so LTspice omits the `tup` measurement (and others may be missing) → missing values count as failed checks with margin −1, never a crash or a pass. *(test: Task 5 `test_missing_measurement_fails_check`)*
4. Gemma re-proposes a circuit it already tried, with renamed nodes/ids → canonical hash detects it, no simulations are re-run, and the next prompt tells the model it was a duplicate. *(tests: Task 2 `test_renamed_circuit_same_hash`, Task 9 `test_duplicate_proposal_not_resimulated`)*
5. The job is killed or hits its timeout mid-run → `python -m piezo_synth.report runs/<id>` rebuilds `report.md`/`summary.json` from the partial `events.jsonl` and CSVs with stop reason `incomplete`. *(test: Task 10 `test_report_from_partial_run`)*

---

## File structure

```
piezo_synth/__init__.py      version string only
piezo_synth/spec.py          conditions, criteria, limits, sim settings (the experiment spec)
piezo_synth/circuit.py       Circuit/Component, parse+validate, canonicalise, hashes, param access
piezo_synth/netlist.py       device models, netlist builder per condition, reference & witness circuits
piezo_synth/sim.py           Simulator: parallel LTspice calls, content-hash cache, timing
piezo_synth/evaluate.py      measurements -> checks -> Evaluation (scalar score), diagnosis text
piezo_synth/llm.py           GemmaClient (retries, token usage), JSON extraction
piezo_synth/prompts.py       system prompt, per-iteration prompt, repair prompt, move policy
piezo_synth/refine.py        coordinate-search value tuning
piezo_synth/records.py       Candidate, RunRecorder (events.jsonl, CSVs, progress.json, timing)
piezo_synth/search.py        SearchConfig, run_search orchestrator, stop rules, held-out check
piezo_synth/report.py        report.md + summary.json from a run folder (CLI)
piezo_synth/rawread.py       LTspice .raw reader (binary + ASCII)
piezo_synth/run.py           CLI entry: full run / --smoke / --fake
piezo_synth/reproduce.py     CLI: re-simulate a saved circuit on chosen conditions, optional waveforms
tests/test_*.py              one per module, plus tests/fakes.py
tools/build_notebook.py      generates piezo_synth.ipynb from the sources
piezo_synth.ipynb            the deliverable notebook (generated)
README.md                    design choices, how to run, how to read results
```

---

### Task 1: Project skeleton and experiment spec

**Files:**
- Create: `piezo_synth/__init__.py`, `piezo_synth/spec.py`, `tests/test_spec.py`, `pytest.ini` (`testpaths = tests`)

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Condition(id: str, split: str, label: str, ip: float, freq: float, cp: float, rp: float, rl: float, temp: float)`; `split ∈ {"search","heldout"}`.
  - `@dataclass(frozen=True) Criterion(id: str, meas: str, op: str, limit: float, scale: float, unit: str, description: str)`; `op ∈ {">=","<="}`.
  - `CONDITIONS: list[Condition]`, `CRITERIA: list[Criterion]`, `LIMITS: dict`, `SIM: dict`, `CTRL_SINK_A = 0.5e-6`.
  - `search_conditions() -> list[Condition]`, `heldout_conditions() -> list[Condition]`, `condition(id) -> Condition`, `spec_dict() -> dict` (JSON-serialisable: conditions, criteria, limits, sim).

Pinned values (copy exactly). All conditions: `rp = 20e6`.

| id | split | label | ip (A pk) | freq (Hz) | cp (F) | rl (Ω) | temp (°C) |
|---|---|---|---|---|---|---|---|
| S1 | search | nominal | 50e-6 | 100 | 25e-9 | 330e3 | 27 |
| S2 | search | heavy load | 50e-6 | 100 | 25e-9 | 150e3 | 27 |
| S3 | search | strong excitation, light load | 100e-6 | 100 | 25e-9 | 2.2e6 | 27 |
| S4 | search | weak excitation | 30e-6 | 100 | 25e-9 | 1e6 | 27 |
| S5 | search | low frequency | 40e-6 | 80 | 25e-9 | 470e3 | 27 |
| S6 | search | Cp +20 %, hot | 50e-6 | 100 | 30e-9 | 330e3 | 60 |
| H1 | heldout | weak excitation, mid load | 35e-6 | 100 | 25e-9 | 470e3 | 27 |
| H2 | heldout | high frequency, Cp −15 % | 60e-6 | 120 | 21.25e-9 | 220e3 | 27 |
| H3 | heldout | very strong excitation, open load, cold | 120e-6 | 100 | 25e-9 | 10e6 | -20 |
| H4 | heldout | hot, heavy load | 50e-6 | 100 | 25e-9 | 200e3 | 85 |

| id | meas | op | limit | scale | unit | description |
|---|---|---|---|---|---|---|
| vout_min | vavg | >= | 1.8 | 1.8 | V | settled mean output reaches the load's minimum supply |
| vout_max | vmax | <= | 3.6 | 3.6 | V | output never exceeds the load's absolute maximum |
| ripple | vpp | <= | 0.05 | 0.05 | V | peak-to-peak ripple in the final window |
| startup | tup | <= | 0.4 | 0.4 | s | cold start: first time output reaches 1.8 V |
| settled | dv | <= | 0.02 | 0.02 | V | mean output changes little between the last two windows |

`LIMITS = {"max_components": 16, "max_switches": 4, "max_sync": 2, "R": (1.0, 1e8), "C": (1e-10, 47e-6), "L": (1e-5, 1e-2), "ton": (1e-7, 1e-3), "phase": (-0.25, 0.25), "l_rser_base": 2.0, "l_rser_per_h": 5000.0}`
`SIM = {"tstop": 0.8, "maxstep": 2e-6, "win": (0.7, 0.8), "win_prev": (0.6, 0.7)}`

- [ ] **Step 1: `git init`, create `pytest.ini`, write failing tests**

```python
from piezo_synth import spec
def test_split_counts():
    assert [c.id for c in spec.search_conditions()] == ["S1","S2","S3","S4","S5","S6"]
    assert [c.id for c in spec.heldout_conditions()] == ["H1","H2","H3","H4"]
def test_pinned_values():
    s4 = spec.condition("S4"); assert (s4.ip, s4.rl, s4.freq) == (30e-6, 1e6, 100)
    h2 = spec.condition("H2"); assert h2.cp == 21.25e-9 and h2.freq == 120
    assert {c.id: (c.op, c.limit) for c in spec.CRITERIA}["startup"] == ("<=", 0.4)
def test_spec_dict_is_json():
    import json; d = json.loads(json.dumps(spec.spec_dict()))
    assert len(d["conditions"]) == 10 and len(d["criteria"]) == 5
```

- [ ] **Step 2: Run `python -m pytest tests/test_spec.py -v`** — Expected: FAIL (module missing).
- [ ] **Step 3: Implement `piezo_synth/spec.py`** with the tables above (tuples become lists in `spec_dict`).
- [ ] **Step 4: Run tests** — Expected: PASS.
- [ ] **Step 5: Commit** `git add -A && git commit -m "feat: experiment spec (conditions, criteria, limits)"`

---

### Task 2: Circuit representation, validation, canonical hashing

**Files:**
- Create: `piezo_synth/circuit.py`, `tests/test_circuit.py`

**Interfaces:**
- Consumes: `spec.LIMITS`.
- Produces:
  - `ALLOWED_TYPES = ("R","C","L","D","S","SYNC")`, `DIODE_MODELS = ("DSCH","DSI","DZ33")`, `RESERVED_NODES = ("0","pzp","pzn","out")`, `MOVES = ("new_topology","modify_topology","resize")`.
  - `@dataclass Component(id: str, type: str, nodes: tuple = (), value: float|None = None, model: str|None = None, ctrl: str|None = None, ton: float|None = None, phase: float|None = None, edges: str|None = None)`.
  - `@dataclass Circuit(name: str, components: list, move: str = "new_topology", rationale: str = "", done: bool = False)`.
  - `class CircuitError(ValueError)` with attribute `problems: list[str]`.
  - `parse_circuit(obj: dict) -> Circuit` (raises `CircuitError` listing **all** problems), `validate(c) -> list[str]`, `canonical(c) -> Circuit`, `topology_hash(c) -> str` (12 hex), `design_hash(c) -> str` (12 hex), `to_dict(c) -> dict` (round-trips through `parse_circuit`), `numeric_params(c) -> list[tuple[str, str]]` (comp id, field ∈ {"value","ton","phase"}), `get_param(c, cid, field) -> float`, `with_param(c, cid, field, value) -> Circuit` (new object, value clamped to `LIMITS`), `describe(c) -> str` (one line per component, for prompts/report).

JSON schema accepted from the model:
```json
{"move": "new_topology", "name": "p-SSHI + bridge + clamp", "rationale": "...", "done": false,
 "components": [
  {"id": "D1", "type": "D", "nodes": ["pzp", "out"], "model": "DSCH"},
  {"id": "C1", "type": "C", "nodes": ["out", "0"], "value": 2.2e-6},
  {"id": "L1", "type": "L", "nodes": ["pzp", "n1"], "value": 4.7e-3},
  {"id": "S1", "type": "S", "nodes": ["n1", "pzn"], "ctrl": "G1"},
  {"id": "G1", "type": "SYNC", "ton": 3.4e-5, "phase": 0.0, "edges": "both"}]}
```

Validation rules (each violation appends one human-readable string naming the component id): type in `ALLOWED_TYPES`; id unique, matches `^[A-Za-z][A-Za-z0-9_]{0,7}$`; R/C/L/D/S have exactly 2 nodes, SYNC has none; node names match `^[a-z][a-z0-9_]{0,11}$` or equal `"0"`; R/C/L have `value` within `LIMITS[type]`; D has `model` in `DIODE_MODELS`; S has `ctrl` naming an existing SYNC; SYNC has `ton` and `phase` within limits and `edges ∈ {"both","pos","neg"}`, and is referenced by ≥1 switch; both terminals of a two-terminal part are not the same node; `pzp`, `pzn` and `out` each appear; every non-`0` node has ≥2 connections, counting the harness's own connections (`pzp`,`pzn`: +1 each; `out`: +1); `out` and `pzp` are in the same connected component; total components ≤ 16, switches ≤ 4, SYNC ≤ 2; `move ∈ MOVES`.

Canonicalisation: refine node labels 3 rounds Weisfeiler–Lehman style (initial label = node name if reserved else `"int"`; new label = sha1 of old label + sorted list of `(type, model, pin role, neighbour label)`, pin role = `"a"/"k"` for diode anode/cathode, `"x"` otherwise); rename internal nodes `n1..nk` by (final label, first appearance in a deterministic component order); sort two-terminal non-polar nodes; rename ids by type and order (`R1..`, `D1..`, `G1..`) updating `ctrl`. `topology_hash` = sha256 over canonical components without values/ton/phase; `design_hash` adds values rounded to 3 significant figures. Isomorphic ties may occasionally get different names (a missed duplicate = harmless cache miss); different circuits never share a hash.

- [ ] **Step 1: Write failing tests**

```python
def test_valid_example_parses(): c = parse_circuit(EXAMPLE); assert len(c.components) == 5
def test_all_problems_reported():
    bad = {"move": "resize", "components": [{"id": "R1", "type": "R", "nodes": ["pzp"], "value": 0.1},
                                             {"id": "X1", "type": "Q", "nodes": ["a", "b"]}]}
    with pytest.raises(CircuitError) as e: parse_circuit(bad)
    msgs = " ".join(e.value.problems)
    assert "R1" in msgs and "X1" in msgs and "out" in msgs   # arity/value, type, missing out
def test_dangling_node_rejected(): ...   # node "n9" used once -> problem mentions n9
def test_sync_unused_rejected(): ...      # SYNC with no switch -> problem mentions G1
def test_renamed_circuit_same_hash():
    a = parse_circuit(EXAMPLE); b = parse_circuit(rename(EXAMPLE, {"n1": "mid", "D1": "Dx", "G1": "Gq"}))
    assert topology_hash(a) == topology_hash(b) and design_hash(a) == design_hash(b)
def test_value_change_keeps_topology_hash():
    a = parse_circuit(EXAMPLE); b = with_param(a, "C1", "value", 4.7e-6)
    assert topology_hash(a) == topology_hash(b) and design_hash(a) != design_hash(b)
def test_rewire_changes_topology_hash(): ...   # move S1 from (n1,pzn) to (n1,out)
def test_with_param_clamps(): assert get_param(with_param(a, "L1", "value", 1.0), "L1", "value") == 1e-2
def test_roundtrip(): assert design_hash(parse_circuit(to_dict(a))) == design_hash(a)
```

- [ ] **Step 2: Run** `python -m pytest tests/test_circuit.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `piezo_synth/circuit.py`** per the rules above.
- [ ] **Step 4: Run tests** — Expected: PASS.
- [ ] **Step 5: Commit** `feat: circuit schema, validation and canonical hashing`

---

### Task 3: Netlist builder, device models, reference and witness circuits

**Files:**
- Create: `piezo_synth/netlist.py`, `tests/test_netlist.py`

**Interfaces:**
- Consumes: `Circuit`, `canonical` (Task 2); `Condition`, `SIM`, `LIMITS`, `CTRL_SINK_A` (Task 1).
- Produces: `MODELS_TEXT: str`, `MEAS_NAMES = ("vavg","vavg_prev","vpp","vmax","tup","pload","pext")`, `build_netlist(c: Circuit, cond: Condition, title: str = "", save_all: bool = False) -> str`, `sync_timing(ton, phase, edges, freq) -> tuple[float, float]` (t0, period), `reference_circuit() -> Circuit`, `witness_circuit() -> Circuit`.

Netlist (the circuit is canonicalised first, so harness names cannot clash):
```
* {title}
Ipz pzn pzp SINE(0 {ip} {freq})
Cpz pzp pzn {cp}
Rpz pzp pzn {rp}
RL out 0 {rl}
Ictl1 out 0 0.5u                       ; one per SYNC
{components}                           ; R/C/D as-is; L: "L1 a b {L} Rser={2+5000*L}"; S: "S1 a b G1_g 0 SWI"
VG1 G1_g 0 PULSE(0 1 {t0} 100n 100n {ton} {period})
Rbleed_n1 n1 0 1G                      ; every internal node
{MODELS_TEXT}
.temp {temp}
.tran 0 0.8 0 2u
.save V(out) V(pzp) V(pzn) I(Ipz)      ; omitted when save_all
.meas TRAN vavg AVG V(out) FROM=0.7 TO=0.8
.meas TRAN vavg_prev AVG V(out) FROM=0.6 TO=0.7
.meas TRAN vpp PP V(out) FROM=0.7 TO=0.8
.meas TRAN vmax MAX V(out) FROM=0 TO=0.8
.meas TRAN tup WHEN V(out)=1.8 RISE=1
.meas TRAN pload AVG V(out)*V(out)/{rl} FROM=0.7 TO=0.8
.meas TRAN pext AVG V(pzp,pzn)*I(Ipz) FROM=0.7 TO=0.8
.end
```
`MODELS_TEXT` (exact):
```
.model DSCH D(Is=5e-8 Rs=1 N=1.05 Cjo=10p BV=30 IBV=1u)
.model DSI D(Is=2.5n Rs=0.6 N=1.75 Cjo=4p BV=75 IBV=1u)
.model DZ33 D(Is=1e-12 Rs=5 N=1.5 BV=3.3 IBV=1u)
.model SWI SW(Ron=2 Roff=1G Vt=0.5 Vh=0)
```
SYNC timing (piezo current `Ip·sin(2πft)` ⇒ open-circuit piezo voltage peaks positive at t = 1/(2f) + k/f, negative at t = k/f): `edges="both"`: period = 1/(2f), t0 = (phase/f) mod period; `"pos"`: period = 1/f, t0 = (1/(2f) + phase/f) mod period; `"neg"`: period = 1/f, t0 = (phase/f) mod period. The controller tracks each condition's frequency (ideal synchronisation, documented in README).

Reference = full-bridge rectifier: `D1 pzp out DSCH`, `D2 pzn out DSCH`, `D3 0 pzp DSCH`, `D4 0 pzn DSCH`, `C1 out 0 2.2u`. Witness (smoke test only, never shown to the model) = parallel SSHI + bridge + clamp: reference plus `L1 pzp n1 4.7m`, `S1 n1 pzn ctrl G1`, `G1 SYNC ton=34u phase=0 edges=both`, `D5 0 out DZ33` (anode 0, cathode out).

- [ ] **Step 1: Write failing tests**

```python
def test_reference_netlist_has_bench_and_meas():
    n = build_netlist(reference_circuit(), spec.condition("S1"))
    for s in ["Ipz pzn pzp SINE(0 5e-05 100)", "RL out 0 330000", ".temp 27", ".tran 0 0.8 0 2u",
              ".meas TRAN tup WHEN V(out)=1.8 RISE=1", ".model DSCH"]: assert s in n
def test_inductor_gets_series_resistance():   # 4.7 mH -> Rser=25.5
    assert "Rser=25.5" in build_netlist(witness_circuit(), spec.condition("S1"))
def test_sync_source_and_sink():
    n = build_netlist(witness_circuit(), spec.condition("S5"))
    assert "Ictl1 out 0 0.5u" in n and "PULSE(0 1 0 100n 100n 3.4e-05 0.00625)" in n
def test_sync_timing_pos(): assert sync_timing(1e-5, 0.0, "pos", 100) == pytest.approx((0.005, 0.01))
def test_bleed_on_internal_nodes_only(): ...   # "Rbleed_n1 n1 0 1G" present, no Rbleed_out
def test_renamed_circuits_same_netlist(): ...  # identical text after canonicalisation
```
(Number formatting: `repr`-style `%.6g`; the test strings above use that format — keep them in sync with the chosen formatter.)

- [ ] **Step 2: Run** `python -m pytest tests/test_netlist.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `piezo_synth/netlist.py`.**
- [ ] **Step 4: Run tests** — Expected: PASS.
- [ ] **Step 5: Commit** `feat: netlist builder, models, reference and witness circuits`

---

### Task 4: Simulator with cache, parallelism and timing

**Files:**
- Create: `piezo_synth/sim.py`, `tests/fakes.py`, `tests/test_sim.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (takes netlist text).
- Produces:
  - `@dataclass SimResult(ok: bool, meas: dict, error: str, seconds: float, folder: str, cached: bool)`.
  - `class Simulator(backend: Callable[[str, str, float], Any], root: Path, workers: int = 8, timeout: float = 120.0)` with `run(jobs: list[tuple[str, str]]) -> list[SimResult]` (jobs are `(label, netlist_text)`, results in input order) and `stats -> dict(n_sims, cache_hits, sim_seconds, wall_seconds)`.
  - `ltspice_backend() -> Callable` (lazy import of `/opt/ltspice/ltspice_run.simulate`, calls `simulate(text, folder, timeout=timeout)`).
  - `tests/fakes.py`: `FakeBackend(fn)` where `fn(netlist_text) -> dict | None` (None = simulation failure), recording `calls`; `FakeLLM = llm.ScriptedLLM` (added in Task 6; until then define a local stand-in with the same signature).

Behaviour: cache key = sha256 of netlist text; folder `root/sims/<key[:16]>`; cache persisted as one JSON line per new result in `root/sim_cache.jsonl` and reloaded on construction (so a resumed run reuses work). Duplicate keys within one `run()` call are simulated once. A backend exception or `ok=False` yields `SimResult(ok=False, error=...)`. Thread pool with `workers` threads; stats guarded by a lock.

- [ ] **Step 1: Write failing tests**

```python
def test_parallel_results_in_order(tmp_path): ...   # 6 jobs, results[i].meas["vavg"] == i
def test_cache_hit_no_backend_call(tmp_path):
    be = FakeBackend(lambda t: {"vavg": 2.0}); s = Simulator(be, tmp_path, workers=2)
    s.run([("a", "X")]); r = s.run([("b", "X")])
    assert len(be.calls) == 1 and r[0].cached and s.stats["cache_hits"] == 1
def test_cache_persists_across_instances(tmp_path): ...
def test_backend_exception_becomes_failed_result(tmp_path):
    r = Simulator(FakeBackend(lambda t: 1/0), tmp_path).run([("a", "X")])[0]
    assert not r.ok and "ZeroDivisionError" in r.error
```

- [ ] **Step 2: Run** `python -m pytest tests/test_sim.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `piezo_synth/sim.py` and `tests/fakes.py`.**
- [ ] **Step 4: Run tests** — Expected: PASS.
- [ ] **Step 5: Commit** `feat: cached parallel simulator wrapper`

---

### Task 5: Evaluation against the spec

**Files:**
- Create: `piezo_synth/evaluate.py`, `tests/test_evaluate.py`

**Interfaces:**
- Consumes: `SimResult` (Task 4), `Condition`, `Criterion`, `CRITERIA` (Task 1).
- Produces:
  - `@dataclass Check(condition: str, criterion: str, measured: float|None, limit: float, op: str, margin: float, passed: bool)`.
  - `@dataclass Evaluation(checks: list[Check], meas: dict, sim_ok: dict, sim_error: dict, scalar: float, cond_pass: int, checks_pass: int, all_pass: bool)`; `meas[cond_id]` includes derived `dv = abs(vavg - vavg_prev)`.
  - `evaluate(results: dict[str, SimResult], conditions: list[Condition], criteria: list = CRITERIA) -> Evaluation`.
  - `diagnose(ev: Evaluation, limit: int = 8) -> str` — failing checks sorted by margin (worst first), one line each: `S4 vout_min: 1.31 V (needs >= 1.8 V, margin -0.27)`; plus `S2: simulation failed: <first 200 chars>` lines.
  - `is_better(a: Evaluation, b: Evaluation|None, ncomp_a: int, ncomp_b: int) -> bool` — higher `scalar`; within 1e-9, fewer components.

Margin: `>=`: (m − limit)/scale; `<=`: (limit − m)/scale; missing/NaN/failed sim → measured None, margin −1, failed. `passed = margin >= 0`.
`scalar = 10*cond_pass + checks_pass + Σ clip(margin, −1, 0) + 0.05 * Σ clip(margin, 0, 0.5)`.

- [ ] **Step 1: Write failing tests**

```python
def test_all_pass(): ev = evaluate({"S1": ok(vavg=2.5, vavg_prev=2.49, vpp=0.02, vmax=2.6, tup=0.2)}, [S1])
    ; assert ev.all_pass and ev.cond_pass == 1 and ev.checks_pass == 5
def test_missing_measurement_fails_check():
    ev = evaluate({"S1": ok(vavg=1.2, vavg_prev=1.2, vpp=0.01, vmax=1.3)}, [S1])   # no tup
    c = {x.criterion: x for x in ev.checks}["startup"]
    assert c.measured is None and not c.passed and c.margin == -1
def test_failed_sim_fails_all_checks_of_that_condition(): ...
def test_margin_values(): ...    # vavg=1.71 -> vout_min margin == pytest.approx(-0.05)
def test_scalar_orders_designs(): ... # more passing conditions beats bigger margins
def test_diagnose_worst_first(): ...
```

- [ ] **Step 2: Run** `python -m pytest tests/test_evaluate.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `piezo_synth/evaluate.py`.**
- [ ] **Step 4: Run tests** — Expected: PASS.
- [ ] **Step 5: Commit** `feat: spec evaluation, scoring and diagnosis`

---

### Task 6: Gemma client

**Files:**
- Create: `piezo_synth/llm.py`, `tests/test_llm.py`

**Interfaces:**
- Produces:
  - `@dataclass LLMReply(answer: str = "", reasoning: str = "", seconds: float = 0.0, prompt_tokens: int|None = None, completion_tokens: int|None = None, reasoning_tokens: int|None = None, finish: str|None = None, error: str|None = None)` (all defaulted so fakes can build `LLMReply(error="503")`).
  - `ScriptedLLM(replies: list[str|LLMReply])` — same `ask()` signature, returns the replies in order (repeating the last), records `received` messages. Lives here so `run.py --fake` and the tests share it; `tests/fakes.FakeLLM` is an alias.
  - `class GemmaClient(url: str = URL, model: str = MODEL, timeout: float = 900, retries: int = 3, backoff: float = 10.0, post: Callable = requests.post, sleep: Callable = time.sleep)` with `ask(messages: list[dict], think: bool, max_tokens: int|None = None, temperature: float|None = None) -> LLMReply` — never raises.
  - `json_from(text: str) -> dict | None`.

Request body as in the demo: `max_tokens` default 16384 (think) / 2048 (no think), temperature 1.0 / 0.3, `chat_template_kwargs.enable_thinking`. Tokens from `usage.prompt_tokens`, `usage.completion_tokens`, `usage.completion_tokens_details.reasoning_tokens` (None when absent). Reasoning from `message.reasoning` or `message.reasoning_content`. Retries on connection errors, timeouts and HTTP ≥500 with `backoff * attempt` sleeps; HTTP 4xx fails immediately. `json_from`: fenced ```json block first, else try `json.JSONDecoder().raw_decode` from each `{` and return the first dict that contains `"components"` (else the first dict).

- [ ] **Step 1: Write failing tests** (inject a fake `post` returning objects with `.status_code`, `.json()`, `.raise_for_status()`)

```python
def test_ask_parses_usage_and_reasoning(): ...   # tokens 120/800/650, reasoning text returned
def test_ask_retries_then_reports_error():
    calls = []; c = GemmaClient(post=failing_post(calls, status=503), sleep=lambda s: None)
    r = c.ask([{"role": "user", "content": "x"}], think=True)
    assert r.error and len(calls) == 3 and r.answer == ""
def test_4xx_not_retried(): ...
def test_json_from_fenced_and_nested(): 
    assert json_from('blah ```json\n{"components": [{"id": "R1"}]}\n``` x')["components"][0]["id"] == "R1"
    assert json_from('text {"a": {"b": 1}} {"components": []}') == {"components": []}
    assert json_from("no json") is None
```

- [ ] **Step 2: Run** `python -m pytest tests/test_llm.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `piezo_synth/llm.py`.**
- [ ] **Step 4: Run tests** — Expected: PASS.
- [ ] **Step 5: Commit** `feat: Gemma client with retries and token accounting`

---

### Task 7: Prompts and move policy

**Files:**
- Create: `piezo_synth/prompts.py`, `tests/test_prompts.py`

**Interfaces:**
- Consumes: `spec` (Task 1), `describe`, `MOVES` (Task 2), `Evaluation`, `diagnose` (Task 5).
- Produces:
  - `system_prompt(reference_eval: Evaluation) -> str`
  - `iteration_prompt(iteration: int, max_proposals: int, top: list[dict], last: dict|None, explored: list[dict], required_move: str|None) -> str` — `top` = up to 5 dicts `{id, name, topo_hash, scalar, cond_pass, circuit_text, diagnosis, table}`; `last` = same shape plus `{"duplicate": bool, "invalid_problems": list[str], "refined_from": str|None}`; `explored` = `[{topo_hash, name, best_scalar}]`.
  - `repair_messages(system: str, user: str, bad_answer: str, problems: list[str]) -> list[dict]`
  - `required_move(moves: list[str]) -> str|None` — returns `"new_topology or modify_topology"` when the last 3 LLM moves were all `"resize"`, else None.
  - `condition_table(ev: Evaluation, conditions) -> str` — compact fixed-width table: condition, vavg, vmax, vpp, tup, pload µW, pass/fail per criterion.

System prompt content (in this order): role (power-electronics designer synthesising a piezo harvester interface); the piezo model and the search conditions table (S1–S6 only) and the five criteria with limits; the harness description (piezo source, `RL`, controller sinks, bleed resistors, 0.8 s cold-start transient, measurement windows); the primitive vocabulary with value bounds, device models and their meaning (DSCH Schottky, DSI silicon, DZ33 3.3 V zener, SWI switch Ron 2 Ω, SYNC semantics incl. edges/phase/ton and the 0.5 µA cost, inductor series resistance 2 Ω + 5 Ω/mH); limits on counts; the JSON schema (Task 2 example); the reference FBR's per-condition results via `condition_table`; instructions: values will be tuned automatically after each proposal, so concentrate reasoning on connectivity; declare `move`; explain the expected effect in `rationale`; set `done: true` only when you believe no structural change can improve the best design; reply with one JSON object only.

- [ ] **Step 1: Write failing tests**

```python
def test_system_prompt_has_spec_and_reference(): p = system_prompt(ref_ev)
    ; assert all(s in p for s in ["S1", "S6", "1.8", "3.6", "DZ33", "SYNC", "\"components\"", "FBR"])
def test_heldout_never_in_prompts():
    p = system_prompt(ref_ev) + iteration_prompt(3, 16, top, last, explored, None)
    for h in spec.heldout_conditions(): assert h.id not in p and h.label not in p
    assert "120 Hz" not in p and "-20" not in p
def test_required_move(): assert required_move(["new_topology", "resize", "resize", "resize"]) \
    and required_move(["resize", "modify_topology", "resize"]) is None
def test_iteration_prompt_mentions_duplicate_and_invalid(): ...
```

- [ ] **Step 2: Run** `python -m pytest tests/test_prompts.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `piezo_synth/prompts.py`.**
- [ ] **Step 4: Run tests** — Expected: PASS.
- [ ] **Step 5: Commit** `feat: prompts and move policy`

---

### Task 8: Value refinement

**Files:**
- Create: `piezo_synth/refine.py`, `tests/test_refine.py`

**Interfaces:**
- Consumes: `numeric_params`, `get_param`, `with_param`, `Circuit` (Task 2); `Evaluation`, `is_better` (Task 5).
- Produces: `refine(circuit: Circuit, start: Evaluation, evaluate_fn: Callable[[Circuit], Evaluation], budget: int, rng: random.Random, should_stop: Callable[[], bool] = lambda: False) -> tuple[Circuit, Evaluation, list[tuple[Circuit, Evaluation]]]` — returns best circuit, its evaluation, and every evaluated (circuit, evaluation) pair.

Algorithm: coordinate search. Step per param: multiplicative factor 2.0 for R/C/L values, 1.3 for `ton`; additive 0.05 for `phase`. Loop over params in `rng`-shuffled order; for each try up then down; accept the first that `is_better`; after a full pass with no acceptance, shrink every step (factor → sqrt(factor), additive → half). Stop when `budget` evaluations are used, all steps are below factor 1.05 / additive 0.005, or `should_stop()` returns True (checked before each evaluation — lets the orchestrator stop refining once the model replies).

- [ ] **Step 1: Write failing tests** (synthetic `evaluate_fn` whose scalar peaks at C1 = 4.7 µF)

```python
def test_refine_improves_and_respects_budget():
    best, ev, tried = refine(c, ev0, fake_eval, budget=10, rng=random.Random(1))
    assert ev.scalar > ev0.scalar and len(tried) <= 10
def test_refine_stops_when_asked(): ...  # should_stop returns True after 2 calls -> len(tried) == 2
def test_refine_no_params_returns_start(): ...
```

- [ ] **Step 2: Run** `python -m pytest tests/test_refine.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `piezo_synth/refine.py`.**
- [ ] **Step 4: Run tests** — Expected: PASS.
- [ ] **Step 5: Commit** `feat: coordinate-search value refinement`

---

### Task 9: Recorder and search orchestrator

**Files:**
- Create: `piezo_synth/records.py`, `piezo_synth/search.py`, `tests/test_search.py`

**Interfaces:**
- Consumes: everything above.
- Produces (`records.py`):
  - `@dataclass Candidate(id: str, iteration: int, origin: str, parent: str|None, circuit: Circuit, topo_hash: str, design_hash: str, evaluation: Evaluation, move: str, name: str, n_components: int)`; `origin ∈ {"reference","witness","llm","refine"}`; ids `c0000`, `c0001`, … .
  - `class RunRecorder(out_dir: Path)`: `event(kind: str, **data)` → `events.jsonl` (`{"t": elapsed_s, "kind": ..., ...}`); `candidate(c: Candidate, split: str = "search")` → `candidates.csv` row + `candidates/<id>/circuit.json` + rows in `measurements.csv` (`candidate,split,condition,<MEAS_NAMES>,dv,sim_ok,sim_error`) and `checks.csv` (`candidate,split,condition,criterion,measured,op,limit,margin,passed`); `progress(**fields)` → atomic `progress.json`; `llm_exchange(iteration, attempt, messages, reply)` → `llm/iter-NN-a.json`; `timing(dict)` → `timing.json`; `log(phase, msg)` prints `[hh:mm:ss] [phase] msg` flush=True, phase ∈ {setup, model, sim, refine, eval, heldout, done}.
- Produces (`search.py`):
  - `@dataclass SearchConfig(max_proposals: int = 16, min_proposals: int = 4, wall_clock_s: float = 3600, stagnation: int = 6, refine_budget: int = 10, think: bool = True, seed: int = 1, continue_after_met: bool = False, heartbeat_s: float = 15)`.
  - `@dataclass SearchOutcome(selected: Candidate, reference: Candidate, stop_reason: str, met_search: bool, heldout_selected: Evaluation, heldout_reference: Evaluation, met_all: bool)`.
  - `run_search(cfg: SearchConfig, llm, sim: Simulator, rec: RunRecorder) -> SearchOutcome`.
  - `evaluate_circuit(c: Circuit, conditions, sim: Simulator, label: str) -> Evaluation` (builds netlists, one `sim.run` call, `evaluate`).

Flow:
1. **setup:** write `spec.json`, `config.json`; evaluate the reference on search conditions (candidate `c0000`, origin `reference`); build the system prompt.
2. **iteration i (1…max_proposals):** start `llm.ask(system + iteration_prompt(...))` in a `threading.Thread`; while it runs, the main thread refines the best candidate whose topology has not been refined since it last improved (`should_stop` = reply arrived), logging `[refine]`, and prints `[model] waiting 45 s (iteration 3)` every `heartbeat_s` if idle. On reply: `json_from` → `parse_circuit`; on parse/validation failure send one repair request with `think=False` and the problem list; if still invalid, log `proposal_invalid` and feed the problems into the next prompt. If `design_hash` already evaluated → `duplicate` event, no sims, flag it for the next prompt. Otherwise evaluate on search conditions (`[sim] 6 conditions …`), record candidate, update best via `is_better`. Each refinement-produced design is also a recorded candidate (origin `refine`, parent id).
3. **stop rules** (checked after each iteration, first that applies): `search_spec_met` (best passes all search checks and not `continue_after_met`); `model_done` (`done: true` and i ≥ `min_proposals`); `model_unavailable` (3 consecutive iterations with `reply.error`); `stagnation` (best scalar not improved by ≥0.01 in `stagnation` consecutive iterations); `time_budget` (elapsed ≥ `wall_clock_s`); `proposal_budget`.
4. **held-out:** evaluate selected (best search candidate) and reference on held-out conditions; record both with `split="heldout"`; `met_all = met_search and heldout all pass`.
5. **finish:** `timing.json` with `wall_s, model_s, model_calls, prompt_tokens, completion_tokens, reasoning_tokens, sim_seconds, sim_wall_s, n_sims, cache_hits, refine_s` (note: model and simulation overlap, so sums can exceed wall time); copy the selected circuit to `selected/circuit.json` and its per-condition netlists to `selected/<cond>.net`; `progress(phase="done", stop_reason=...)`.

`progress.json` fields: `phase, iteration, max_proposals, elapsed_s, best_id, best_scalar, best_cond_pass, n_candidates, model_wait_s` (current wait), `stop_reason`.

- [ ] **Step 1: Write failing tests** (FakeLLM + FakeBackend whose measurements depend on netlist text, e.g. any netlist containing `DZ33` and `SWI` passes everything)

```python
def test_search_meets_spec_and_runs_heldout(tmp_path):
    out = run_search(cfg, FakeLLM([json.dumps(WITNESS_LIKE)]), sim, rec)
    assert out.stop_reason == "search_spec_met" and out.met_search
    assert {c.condition for c in out.heldout_selected.checks} == {"H1","H2","H3","H4"}
    assert (tmp_path / "selected" / "circuit.json").exists()
def test_duplicate_proposal_not_resimulated(tmp_path): ...  # same circuit renamed twice -> backend calls unchanged; event "duplicate"
def test_invalid_then_repaired(tmp_path): ...               # first reply invalid, repair reply valid -> candidate recorded
def test_search_survives_sim_failure(tmp_path): ...         # backend returns None for one proposal -> loop continues, next prompt contains "simulation failed"
def test_search_stops_when_model_unavailable(tmp_path):
    out = run_search(cfg, FakeLLM([LLMReply(error="503")] * 5), sim, rec)
    assert out.stop_reason == "model_unavailable" and out.selected.origin == "reference"
def test_stagnation_and_budget(tmp_path): ...
def test_heldout_not_in_any_prompt(tmp_path): ...          # inspect FakeLLM.received messages
def test_timing_has_tokens(tmp_path): ...
```

- [ ] **Step 2: Run** `python -m pytest tests/test_search.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `records.py` and `search.py`.**
- [ ] **Step 4: Run** `python -m pytest -v` (whole suite) — Expected: PASS.
- [ ] **Step 5: Commit** `feat: search orchestrator with overlapping refinement and run recorder`

---

### Task 10: Report, raw reader, CLIs

**Files:**
- Create: `piezo_synth/report.py`, `piezo_synth/rawread.py`, `piezo_synth/run.py`, `piezo_synth/reproduce.py`, `tests/test_report.py`, `tests/test_rawread.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 9 output files and APIs.
- Produces:
  - `build_report(out_dir: Path) -> str` — writes `report.md` and `summary.json`; works from files alone. `report.md` sections in order: Specification (criteria table); Test conditions (search and held-out tables); Reference results (per condition × criterion, measured / pass); Proposals tried (iteration, origin, move, name, topology hash, valid, duplicate, conditions passed, scalar, model seconds, tokens); Selected design (component list, per-condition measurements and checks); Held-out check (selected vs reference); Unmet requirements (every failed condition × criterion with measured vs limit — or "none"); Stop reason; Time and tokens; File index. `summary.json`: `{stop_reason, met_search, met_all, selected_id, selected_topology, reference_id, failed_checks: [...], timing: {...}}`. Missing `progress.json` "done" ⇒ stop reason `incomplete`.
  - `read_raw(path) -> dict[str, list[float]]` — LTspice `.raw`: header UTF-16LE (fall back to latin-1 when not UTF-16), parse `No. Variables`, `No. Points`, `Flags`, `Variables:`; `Binary:` section: time float64 then others float32 per point (all float64 if `double` in Flags; take `abs()` of time, LTspice stores sign flags there); `Values:` ASCII section supported.
  - `run.py` CLI: `python -m piezo_synth.run --out runs/<id> [--config cfg.json] [--smoke] [--fake] [--workers 8]`. `--smoke`: no model; simulates reference and witness on all 10 conditions, records them, writes report, prints a condition table and checks `pext > 0` for the reference on S1 (prints a WARNING otherwise). `--fake`: `ScriptedLLM` (Task 6) with three proposals (FBR + clamp, witness-like p-SSHI, a duplicate) + `analytic_backend(netlist_text, folder, timeout)` defined in `run.py` (returns plausible measurements keyed on which models appear in the netlist), for a wiring dry-run anywhere. Report is built in a `finally:` block.
  - `reproduce.py` CLI: `python -m piezo_synth.reproduce <circuit.json> --out <dir> [--conditions search|heldout|all|S1,H2] [--waveforms]` — re-simulates, prints the check table, `--waveforms` uses `save_all=True` and adds `.options plotwinsize=0` (uncompressed raw), leaving `.raw` files in `<dir>`.

- [ ] **Step 1: Write failing tests**

```python
def test_report_sections(tmp_path): run fake search; text = build_report(tmp_path)
    ; assert all(h in text for h in ["## Specification", "## Reference results", "## Proposals tried",
                                     "## Held-out check", "## Unmet requirements", "## Stop reason", "## Time and tokens"])
def test_report_from_partial_run(tmp_path):
    # copy a fake run's folder, delete progress.json and truncate events.jsonl to half
    s = json.loads((tmp_path / "summary.json").read_text()) after build_report
    assert s["stop_reason"] == "incomplete"
def test_read_raw_binary(tmp_path): write synthetic UTF-16 header + struct-packed points
    ; d = read_raw(p); assert d["time"][2] == pytest.approx(2e-3) and d["V(out)"][1] == pytest.approx(1.5)
def test_read_raw_ascii(tmp_path): ...
def test_cli_fake_run(tmp_path): subprocess `python -m piezo_synth.run --fake --out <tmp>` exits 0, report.md exists
```

- [ ] **Step 2: Run** `python -m pytest tests/test_report.py tests/test_rawread.py tests/test_cli.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement the four modules.**
- [ ] **Step 4: Run** `python -m pytest -v` — Expected: PASS.
- [ ] **Step 5: Commit** `feat: report, raw reader, run and reproduce CLIs`

---

### Task 11: Notebook and README

**Files:**
- Create: `tools/build_notebook.py`, `piezo_synth.ipynb` (generated), `README.md`, `tests/test_notebook.py`

**Interfaces:**
- Consumes: all sources in `piezo_synth/`.
- Produces: `build(out: Path = "piezo_synth.ipynb") -> None`; notebook in nbformat 4 JSON (no nbformat dependency).

Notebook cells, in order:
1. Markdown: what the experiment does, the spec in brief, the order to run cells, expected run time (~30–60 min).
2. Code: `os.makedirs("piezo_synth", exist_ok=True)`; `from gpu import run, log, jobs, cancel`; `LTSPICE` image string as in the demo; `RUN_ID = time.strftime("%Y%m%d-%H%M%S")`.
3. One `%%writefile piezo_synth/<module>.py` cell per module, contents byte-identical to the source files (collapsed via `"jupyter": {"source_hidden": true}` metadata).
4. Code: `CONFIG = dict(max_proposals=16, min_proposals=4, wall_clock_s=3600, stagnation=6, refine_budget=10, think=True, seed=1)` written to `run_config.json`.
5. Markdown + code (optional, recommended once): smoke job `run("bash -o pipefail -c 'python3 -u -m piezo_synth.run --smoke --out runs/smoke 2>&1 | tee runs/smoke.log'", image=LTSPICE, gpus=0, cpus=8, memory="16Gi", timeout=3600, name="piezo-smoke")`; `log(...)`.
6. Code: full job, same pattern with `--config run_config.json --out runs/{RUN_ID}`, `timeout=4*3600`, `name="piezo-synth"`; then `log(job)` (note: stopping `log` does not stop the job; `cancel(job)` does).
7. Code: progress peek — read `runs/{RUN_ID}/progress.json` and print phase, iteration, best, elapsed.
8. Code: results — `display(Markdown(open(report.md).read()))`; load `candidates.csv`, `measurements.csv`, `checks.csv` with pandas.
9. Code: figures (matplotlib): best scalar vs iteration with proposal markers coloured by move; pass/fail heatmap (selected vs reference × all 10 conditions × 5 criteria); grouped bars of vavg and pload per condition, selected vs reference, with 1.8/3.6 V lines. Saved as PNG and PDF under `runs/{RUN_ID}/figures/`.
10. Code: waveforms — submit `reproduce --waveforms` job for selected and reference on S1 and S4, then plot V(out) vs time from `read_raw`.

README sections: Design choices (copy the rationale of the design doc, plus: the SYNC idealisation and its cost; inductor loss model; why prompts are stateless; why held-out conditions are evaluated only after stopping; cache and overlap); How to run (upload `piezo_synth.ipynb` to a folder of your own under `/work`, run cells 1–4, smoke job, full job); Interpreting results (what each criterion means physically, how to read `report.md`, `summary.json`, the CSVs, `scalar`, reasons the run stops; that sums of model and simulation time can exceed wall time); Reproducing (re-run `reproduce` on `selected/circuit.json`; `seed`); Adjusting the spec (edit `spec.py` tables; re-run the smoke job to recalibrate); Known limitations (ideal synchronisation, idealised device models, no layout/parasitics).

- [ ] **Step 1: Write failing test**

```python
def test_notebook_embeds_sources_exactly():
    build(tmp_path / "nb.ipynb"); nb = json.load(open(tmp_path / "nb.ipynb", encoding="utf-8"))
    cells = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    for f in Path("piezo_synth").glob("*.py"):
        assert f"%%writefile piezo_synth/{f.name}\n" + f.read_text(encoding="utf-8") in cells
    assert any("--smoke" in c for c in cells) and any("progress.json" in c for c in cells)
```

- [ ] **Step 2: Run** `python -m pytest tests/test_notebook.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `tools/build_notebook.py`, run `python tools/build_notebook.py`, write `README.md`.**
- [ ] **Step 4: Run** `python -m pytest -v` — Expected: PASS (full suite).
- [ ] **Step 5: Commit** `feat: notebook deliverable and README`

---

### Task 12: Validation on Panda (run by the researcher; implementer prepares the checklist)

Not automatable here. README "First run" lists these checks; the implementer adds them verbatim.

- [ ] **Step 1: Smoke job** (notebook cell 5). Expected: 20 simulations finish; each takes < 15 s; console shows `[sim]` lines; `runs/smoke/report.md` exists.
- [ ] **Step 2: Sanity checks on the smoke report.** Reference `pext` on S1 is positive (if negative, flip the sign in the `pext` `.meas` in `netlist.py`). The reference fails at least S2, S3 and S4 (this is what makes the spec challenging). The witness should pass more conditions than the reference; if it passes none, inspect `runs/smoke/sims/*/*.log` for convergence errors before running the full job. If the reference passes everything, tighten `rl` for S2 / lower `ip` for S4 in `spec.py` and repeat.
- [ ] **Step 3: Full job** (cell 6). Expected: `[model] waiting …` heartbeats, `[refine]` and `[sim]` lines, a `stop reason` line, and `report.md`/`summary.json`/`figures/` in `runs/<RUN_ID>/`.
- [ ] **Step 4: Record observed timings** (Wine start-up, per-sim seconds, model seconds per call) in the README "Observed performance" section.
