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
- `graders/color.py`: hex parsing, sRGB->Lab, CIEDE2000 (verified against Sharma reference pair), region median, scoring.
- `graders/continuity.py`: G0 gap, G1 angle, curvature jump, polyline curvature, tiered join grading.
- `graders/render.py`: key-light direction, contrast ratio, clipping, contact-shadow, colour-temperature bias.
- `graders/optics.py`: Sellmeier IOR, prism deviation, Fresnel, white-furnace, prism-render grader.
- 11 seed tasks across all disciplines; `pytest` covers graders and task loading.

## Not yet built (next steps)
1. Tool adapters + VM images (Blender first: headless Python gives cheap scene-state export; then VRED/Unreal, then NX/CATIA, which need licences).
2. Assets (`assets/*`): none exist yet; tasks reference placeholders.
3. VLM-rubric judge with fixed rubric, reference images and multi-sample agreement.
4. Harness loop (screenshot -> action), step/time budgets, trajectory logging.
5. More render-engine tasks: spectral upsampling, thin-film, volumetric, MIS correctness, three.js headless harness.
6. Calibration: human expert baseline per task, difficulty tuning, and held-out variants (randomised hex/dimensions) to resist memorisation.

## Open items
- Paste the BlenderBench concepts you like so they can be mapped onto the above (task structure, scoring, harness).
- Which licensed tools are actually available for the harness?
