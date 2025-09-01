# Roadmap: Blender Anime-Style Pipeline

Goal: Build a production-ready pipeline that turns Blender 3D scenes into anime-style output (cel shading + stylized line art) while staying compatible with Blender-native nodes and .blend assets.

---

## Phase 0 — Vision and Product Definition (1–2 weeks)

Outcomes
- Success criteria defined: visual targets, performance targets, and usability.
- Reference lookbook built from anime productions and stylized 3D references.
- Constraints documented: Blender-only shaders, no external renderers required, works with .blend files.

Actions
- Collect references (screenshots, clips). Annotate with: base color, lighting style, line weight, halftone/gradients, speed lines, vfx motifs.
- Define acceptance tests: a small set of shots with target looks.
- Decide on minimal Blender version and platforms (Windows/macOS/Linux, GPU requirements).

Artifacts
- `docs/lookbook/` images + notes
- `docs/specs/success_criteria.md`
- `docs/specs/targets.md`

---

## Phase 1 — Technical Research & Prototyping (2–4 weeks)

Focus
- Evaluate Blender render engines: Eevee (realtime), Eevee Next, Cycles (stylized).
- Evaluate freestyle vs geometry-based line art vs shader-based outlines.
- Prototype NPR shaders: cel steps, rim light, shadow bands, specular streaks, anisotropic brush feel.

Actions
- Build a small sandbox .blend with: 3–5 primitive assets, one animated character, a few lights, camera.
- Create shader node groups for: Cel Ramp, Shadow Bands, Specular Streak, Rim, Hatching (optional), Emission Accents.
- Try silhouette/outline options:
  - Freestyle line art (with modifiers for thickness by depth/angle)
  - Inverted hull geometry (solidify/extrude + flipped normals)
  - Screen-space edge detect (Eevee only; post fx)
- Test texture workflows: baked gradients vs procedural ramps vs LUT-driven ramps.

Artifacts
- `blender/prototypes/sandbox.blend`
- `blender/shaders/` node group library (.blend or .json for Asset Browser)
- `docs/notes/prototyping.md`

Milestones
- Choose primary render engine (start Eevee for speed; keep Cycles fallback).
- Choose primary line art technique (Freestyle for control + inverted hull for stability).
- Define shader stack (node groups) and name them.

---

## Phase 2 — Shader Library & Asset Browser Integration (3–6 weeks)

Focus
- Package NPR shaders as reusable Node Groups and mark as Assets for drag-and-drop.
- Establish PBR-to-NPR bridge: interpret Principled BSDF inputs into stylized albedo, shadow mask, specular accents.

Actions
- Build node groups with I/O sockets:
  - Toon_Shade_Core(BaseColor, Normal, LightDir, ShadowSteps, SpecularSize, SpecularIntensity, RimPower, RimColor)
  - Toon_Shadow_Ramp(RampTex, ShadowThresholds)
  - Toon_Specular(StreakWidth, Orientation, Intensity)
  - Toon_Rim(Width, Color, FresnelBias)
  - Outline_InvertedHull(Thickness, Color, CullMode)
- Author Asset Browser metadata, thumbnails, and categories.
- Create test materials: Skin, Hair, Cloth, Metal, Plastic, Eye.

Artifacts
- `blender/shaders/shader_library.blend`
- `docs/shaders/catalog.md` (parameters + screenshots)

Milestones
- Drop-in materials produce target look on sandbox assets.

---

## Phase 3 — Line Art System (2–5 weeks)

Focus
- Reliable outlines and feature lines with consistent thickness and stylization.

Actions
- Configure Freestyle (or Line Art modifier on Grease Pencil) for:
  - Silhouette, Crease, Contour, Intersection
  - Thickness by distance and by view angle
  - Per-material line color overrides
- Add inverted hull outlines for fallback and animation stability.
- Bake line art to Grease Pencil for comp flexibility when needed.

Artifacts
- `blender/lineart/lineart_presets.blend`
- `docs/lineart/presets.md`

Milestones
- 360° turntable of character with stable lines through motion.

---

## Phase 4 — Lighting, Cameras, and Scene Templates (2–4 weeks)

Focus
- Reusable lighting rigs and camera setups that suit anime style.

Actions
- Create studio lighting rigs: 1-key stylized, 3-point toon, dramatic rim setups.
- Camera templates: 12/24/30 fps project settings; motion blur off or stylized; shutter cheats.
- Depth grading: fog bands, distance-based color tint for atmospheric perspective.

Artifacts
- `blender/templates/scene_templates.blend`
- `docs/scenes/templates.md`

Milestones
- Template produces consistent look across test shots.

---

## Phase 5 — Animation & Rigging Conventions (3–8 weeks)

Focus
- Kinematic clarity, stepped interpolation, anime timing, squash-and-stretch where suited.

Actions
- Rig requirements: FK/IK switching, bendy bones for limbs, facial rig with shape keys for stylized eyes/mouth.
- Animation conventions: stepped keys for blocking, held frames, smear poses, on-twos export profiles.
- Add pose libraries and animation cycles (idle, run, jump) for testing.

Artifacts
- `blender/rigs/rig_guides.md`
- `blender/actions/` example actions
- `docs/animation/conventions.md`

Milestones
- Short animated clip (3–5s) showing the style in motion.

---

## Phase 6 — Rendering & Compositing (2–5 weeks)

Focus
- Non-destructive render setup with AOVs and passes for comp.

Actions
- Output passes/AOVs: Beauty, Lines, ShadowMask, SpecularMask, RimMask, Z-Depth, ID masks. (Add-on auto-creates AOVs and writes mask AOVs from materials.)
- Eevee settings: shadows resolution, contact shadows, SSR off/on per material, clamp, color management (Filmic vs Standard).
- Compositor node group templates: color banding control, halftone overlays, vignette, posterization. (Add-on provides a starter template blending AOV masks.)

Artifacts
- `blender/compositor/compositing_templates.blend`
- `docs/rendering/passes.md`

Milestones
- Rendered shots match success criteria; comp stack is reusable.

---

## Phase 7 — Add-on: Tools & Automation (4–8 weeks)

Focus
- Blender add-on to automate repetitive setup and ensure consistency.

Features
- Apply Toon Material to selection; toon node group with Shadow/Rim/Specular masks and RampStrength.
- Add Outline (inverted hull) with chosen thickness.
- Configure Freestyle line art for the view layer.
- Scene template creator (fps, color management, passes and AOVs).
- Compositor template setup that uses AOV masks.
- Create toon lighting rig (ground, camera, 3-point lights).
- Batch render from all cameras.

Artifacts
- `addons/anime_pipeline/` Blender add-on (Python)
- `docs/addon/spec.md`, `docs/addon/user_guide.md`

Milestones
- One-click setup for a fresh scene to the studio look.

---

## Phase 8 — Asset Standards & Publishing (2–4 weeks)

Focus
- Keep assets consistent and ready for reuse.

Actions
- Naming conventions for materials, collections, and actions.
- Texture packing/baking guidelines (if using ramps/LUTs).
- Asset Browser packaging (categories, previews, versioning).

Artifacts
- `docs/pipeline/standards.md`
- `docs/pipeline/checklist.md`

Milestones
- New assets drop in and match the look with minimal tweaking.

---

## Phase 9 — Performance & QA (ongoing)

Focus
- Real-time viewport performance and predictable render times.

Actions
- Profiling: scene complexity vs fps, render time by pass.
- LOD rules; shader cost budgets; texture memory caps.
- Visual regression: compare reference stills using automated diff (ImageMagick/CI).

Artifacts
- `tools/bench/` scripts for profiling and diffs
- `docs/qa/visual_regression.md`

Milestones
- Stable performance targets met on test hardware.

---

## Phase 10 — Documentation & Training

Focus
- Make it easy for artists to adopt.

Actions
- Quickstart docs, video walkthroughs, do/don't style sheets.
- Troubleshooting guide (banding, flicker, aliasing, line boil).

Artifacts
- `docs/guides/quickstart.md`
- `docs/guides/troubleshooting.md`

Milestones
- New user can set up and render a shot in under 30 minutes.

---

## Deliverables Overview

- Reusable shader library (node groups, assets)
- Line art presets and inverted hull outline tool
- Scene/lighting templates
- Add-on for automation
- Documentation and standards

## Dependencies & Tools

- Blender 4.x (Eevee Next recommended when stable)
- Optional: Grease Pencil 3.0 features (if on Blender 4.2+)
- Python 3.10+ (bundled with Blender for add-ons)

## Risks & Mitigations

- Temporal artifacts (aliasing, flicker): prefer stable line methods, comp post-fx over screen-space edges.
- Banding in cel steps: dither/noise injection, higher bit-depth or LUT ramps.
- Cross-version Blender changes: pin minimum version, provide compatibility notes.

## Next Steps

- Build the sandbox .blend and first pass shaders.
- Decide on primary line art method based on tests.
- Lock render engine and start naming the node groups.
