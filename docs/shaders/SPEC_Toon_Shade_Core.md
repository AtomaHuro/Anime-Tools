# Shader Spec: Toon_Shade_Core

Purpose
- Provide a clean cel shading base with controllable shadow bands, specular/rim accents, and stable color output.

Node Group: `Toon_Shade_Core`

Inputs
- BaseColor (Color): Albedo base.
- ShadowSteps (Float): 1–5 steps; 2–3 typical.
- RimPower (Float): 0.5–3 fresnel curve power.
- RimColor (Color): Tint for rim.
- RampStrength (Float): 0–1 blend between banded color and ColorRamp stylization (0=bands only, 1=ramp only).
- SpecularSize (Float): 0–1 roughness driving highlight width (lower=sharper; typical 0.05–0.2).
- SpecularIntensity (Float): 0–3 specular strength.
- SpecularColor (Color): Tint for the highlight.

Outputs
- BSDF (Shader): Emission-based surface for Eevee toon output.
- ShadowMask (Float): 0–1 mask of shadow band for compositing.
- RimMask (Float): 0–1 rim region.
- SpecularMask (Float): 0–1 specular region.

Implementation Notes
- Eevee-friendly: use ShaderToRGB for lighting to color conversion; avoid screen-space effects.
- Cel banding: Diffuse -> ShaderToRGB -> RGB to BW -> quantize with ShadowSteps via floor(f*steps)/max(steps-1,1).
- Stylization: optional ColorRamp path blended by RampStrength to art direct thresholds.
- Rim: Layer Weight Facing -> (1 - Facing) -> pow by RimPower; use as factor to scale RimColor and add to base.
- Specular: Glossy -> ShaderToRGB -> BW -> pow -> multiply by SpecularIntensity and tint with SpecularColor; add to base. Roughness is driven by SpecularSize.
- Output: Use Emission as final BSDF for flat toon look; expose ShadowMask (1 - band factor), RimMask (rim pow), SpecularMask (spec intensity signal) for compositing.

Naming & Asset Browser
- Name: `Toon_Shade_Core`
- Category: Shaders/Toon
- Provide preview thumbnail with a simple sphere under key+rim lighting.

Testing
- Spheres and a character bust under 3-point toon rig.
- Check for banding, flicker across frames, and color clipping.
