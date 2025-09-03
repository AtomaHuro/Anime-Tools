# Anime & Manga Shader Add-on (Blender 4.5 LTS)

<p align="center">
	<img src="assets/preview.gif" alt="Anime & Manga Shader Add-on preview" width="720" />
</p>

Modern NPR toolkit for anime/manga workflows in Blender 4.5.x LTS: cel shaders, outlines, GP line art, overlays (noise/halftone/hatching/texture), scene & lighting helpers, and animation cadence.

## Compatibility
- Blender 4.5.x LTS (uses Eevee Next and 4.x API)

## Capabilities
- Cel Shaders
	- Create Anime Toon and Manga Tone materials (Shader to RGB + Constant ColorRamp)
	- Apply to selected objects; batch convert
- Presets
	- Built-in defaults: `anime_default`, `manga_default` (non-deletable)
	- Apply, Save, Rename, Delete; user presets stored in `data/presets.json`
	- Safeguard against duplicate names with defaults
- Overlays (material-level, luminance-masked)
	- Noise detail; Halftone dots; Hatching (with angle/scale; cross-like look)
	- Texture overlay: blend external images (UV/Generated, blend mode, factor, color space)
	- Live controls per active material (scale/factor/angle/coords/mask/blend)
	- Reset/Reseed overlays; Line Boil (enable/disable drivers) for organic jitter
- Outlines & Grease Pencil
	- Mesh outline via inverted hull (Solidify/backface strategy)
	- Freestyle toggle; Occluder (Holdout) helper; Shade Flat
	- Grease Pencil Line Art object; GP detail canvas
- Scene & Lighting
	- Switch to Eevee Next; Bloom + AO helpers
	- Color Management: Standard view transform
	- Add Sun light; Add Rim light; Auto Smooth by angle; Add Subsurf
- Animation cadence
	- Step Keys (hold on 2s/3s/4s) with optional constant interpolation and key reduction
	- Unstep Keys (restore Bezier)
- Updates
	- Quick link to project GitHub from the panel

## Installation
1. Create the ZIP (from this workspace): run the VS Code task “Zip Blender add-on (script)”. It outputs:
	 - `c:\Users\unspo\Desktop\Projects\Animation Studio\anime-manga-shader-addon.zip`
2. In Blender: Edit > Preferences > Add-ons > Install…
3. Pick the ZIP and enable the add-on.

## Where to find it in Blender
- Shader Editor > Sidebar (N) > “Anime & Manga” tab

## Quick usage
1. Create a shader
	 - Click “Anime” or “Manga”, then “Apply to Selected” (or use “Batch Convert”).
2. Presets
	 - Pick a preset from the dropdown, “Apply”. Use Save/Rename/Delete for custom looks.
3. Overlays
	 - Add Noise/Halftone/Hatching/Texture Overlay. Adjust in “Overlay Controls (Active Material)”.
	 - Use “Reset/Reseed Overlays” to reconnect base color and randomize patterns.
	 - “Enable/Disable Line Boil” adds/removes subtle animation to overlay drivers.
4. Outlines & GP
	 - “Add Outline”, “Enable Freestyle”, or create GP Line Art / GP Canvas.
5. Scene & Lighting
	 - Switch to Eevee, enable Bloom+AO, set Color Mgmt: Standard, add Sun/Rim lights, Smooth by Angle, Subsurf.
6. Animation cadence
	 - “Step Keys (2s/3s/4s)” to hold poses; “Unstep Keys (Bezier)” to restore smoothing.

## Notes & data
- User presets live in `data/presets.json`. Built-in defaults are protected from deletion.
- Texture overlay properties exist per material; controls appear when a material is active.
- The panel is available when the Shader Editor is active.

## Packaging from VS Code
- Run the task: “Zip Blender add-on (script)”. The ZIP is regenerated in the workspace root.

## Optional: create the README GIF
- Requirements: ffmpeg installed and on PATH
- Use the helper script to convert a short MP4/MOV into `assets/preview.gif`:

```powershell
# Example: 6-second 720p, 15 fps segment from 00:00:02
powershell -ExecutionPolicy Bypass -File scripts/make_gif.ps1 -Input "C:\path\to\clip.mp4" -Start 2 -Duration 6 -Width 720 -Fps 15
```

## Support & Contributions
- Issues and feature requests: https://github.com/AtomaHuro/Anime-Tools/issues

## License
- MIT License (see `LICENSE`).