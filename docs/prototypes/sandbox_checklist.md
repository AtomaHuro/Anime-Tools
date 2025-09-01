# Sandbox Scene Checklist

Goal: A compact .blend to test shaders, lines, lighting, and animation stability.

Assets
- 3–5 props with simple materials: matte, metal, plastic, cloth, hair.
- 1 character proxy (rigged): head + torso with eyes/mouth, or simple full-body rig.
- Shader test spheres: basecolor grid, smooth gradient, checker.

Layout
- Collections: `CHAR`, `PROPS`, `LIGHTS`, `CAM`, `RENDER`, `LINEART`.
- Camera: 24fps project; 1080p; no motion blur initially.

Lighting
- Preset 1: Single key with high contrast.
- Preset 2: 3-point toon rig (key, fill, rim).
- Preset 3: Dramatic rim-only variant.

Line Art
- Try inverted hull outlines (add-on).
- Try Freestyle/Line Art presets later (Phase 3).

Shots
- Turntable (360°) for character.
- Quick walk/idle loop (on-twos test).
- Close-up face with eye/mouth shapes.

Validation
- No flicker across frames; line thickness stable.
- Cel bands clean (minimal banding); speculars controlled.
- Passes export as expected (Z, material ID).
