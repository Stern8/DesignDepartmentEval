# DesignDepartmentEval (DesignBench): automotive design-discipline eval

> Status: scaffold. Written without access to the BlenderBench post (refresh.dev was blocked in the
> authoring sandbox), so alignment with its concepts is by assumption. See "Open items".

## Principles
1. **Check the artefact, not the transcript.** Grade the exported file, render or scene state, not what the model says it did.
2. **Deterministic first, VLM second.** Every task has programmatic checks (hex, dE2000, G0/G1/G2, dimensions, ray-angle error). A VLM rubric covers only subjective items and carries <=40% of a task's weight.
3. **Specific, department-shaped tasks** with a single measurable pass condition and at least one trap (e.g. colour looks right but the view transform is wrong; a surface looks smooth but is only G1).
4. **Tool-agnostic grading.** The model exports a small contract file (edge samples JSON, scene-state JSON, PNG) so the same grader works whichever of VRED / Unreal / Blender / NX / CATIA / A360 produced it.
5. **No partial credit for skipped work**: missing checks score 0 (`scoring.aggregate`).

## Disciplines and what is measured
| Discipline | Example skills | Core graders |
|---|---|---|
| Advanced design | Brief -> proportion/package blockout | dimensions within 1%, VLM proportion |
| Design realisation | Feasibility (min radius, draft), silhouette preservation | scene-state geometry checks |
| Digital modelling | Surface alignment, G0/G1/G2, curvature-comb diagnosis | `continuity.grade_join` |
| CMF | Exact hex, flake/gloss, view-transform awareness | `color.score_hex` (exact, then CIEDE2000 falloff) |
| Visualisation | Studio setup, light/shadow intent, rigging/animation | `render.*` + scene-state + VLM |
| Studio engineering | Data handoff, versioning in A360/PDM, no-overwrite | sandbox state diff |
| Render engine | Write own renderer: dispersion, caustics, spectral, furnace | `optics.*` physics references |

## Modes
- `computer_use`: model drives a real app (VRED, Unreal, Blender, NX, CATIA, Autodesk 360) in a VM. Observation = screenshots (+ optional accessibility tree); the harness snapshots scene state / exports after the episode.
- `code_gen`: model writes a renderer (Python/numpy, GLSL, three.js headless via Playwright) in a sandbox with a time limit; outputs are graded against analytic physics (Sellmeier prism, Fresnel, white-furnace).
- `hybrid`: Blender via Python API plus GUI.

## Task format (`tasks/*.yaml`)
`id, discipline, mode, tools, difficulty (1-5), prompt, inputs, checks[{name, grader, weight, params}]`; weights sum to 1.
Grader kinds: python functions in `designbench/graders`, `scene_state` (assertions on exported JSON, to be implemented per tool adapter), `vlm_rubric`, `sandbox` (exit status / runtime / determinism).

## Implemented now
- **Graders** (`designbench/graders/`): `color` (hex, CIEDE2000, linear->sRGB), `continuity` (G0/G1/G2), `render` (light/shadow stats), `optics` (Sellmeier prism, Fresnel), `scene_state` (Blender scene-JSON checks: exact hex from material, view transform, lights untouched, package dimensions, rotation limits, hinge axis, animation duration, per-frame intersections), `render_engine` (furnace, prism deviation, caustic focus, sandbox run status).
- **Blender track** (`designbench/blender/`): `make_assets.py` builds start files procedurally; `export_state.py` dumps `scene_state_v1` JSON. **Both scripts have not been run in Blender yet** (none in the authoring sandbox); only their syntax was checked. The graders are tested on hand-built JSON.
- **Render-engine track** (`designbench/render_engine/`): subprocess harness with timeout (`main.py <task> <outdir>` contract), plus reference prism (vector ray trace) and furnace (two-sphere path tracer) solutions in `examples/reference_submission/`, validated end to end. No reference caustic renderer yet; the caustic grader is tested on synthetic images only.
- `python -m designbench.run <task_id> --state ... --baseline ... --outdir ...` grades one task; checks without an implemented grader (e.g. `vlm_rubric`) are reported as `unimplemented` and score 0.
- 11 seed tasks; 19 tests (`pytest`).

## Known limits
- The harness uses a plain subprocess, not a sandbox: run untrusted model code in a container/VM.
- `package_dims` assumes `Body`, `Wheel_FL`, `Wheel_RL` naming, +Y forward, Z up.
- The caustic grader checks focus, position and shadow ring from the image only; it can't verify the physics.

## Next steps
1. Run `make_assets.py` / `export_state.py` in real Blender 4.x and fix whatever breaks; add a Blender GUI computer-use harness (screenshot -> action) on top.
2. Reference caustic renderer (photon mapping) to validate the caustic grader; more render-engine tasks (spectral upsampling, thin film, volumetrics, MIS).
3. VLM-rubric judge with fixed rubric and multi-sample agreement.
4. Calibration: human expert baselines, randomised variants (hex, dimensions) to resist memorisation.
5. Other tool adapters (VRED, Unreal, NX, CATIA, A360).

## Open items
- Paste the BlenderBench concepts you like so they can be mapped onto the above (task structure, scoring, harness).
- Which licensed tools are actually available for the harness?
- BlenderBench concepts still not incorporated (post was unreachable).
