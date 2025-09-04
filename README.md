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
------------

   <img width="1918" height="1033" alt="Screenshot 2025-09-03 184953" src="https://github.com/user-attachments/assets/9f03076d-6680-4859-90c3-8a273f3b3470" />
   
------------
## Installation
1a. In Blender: Edit > Preferences 

   <img width="1919" height="1027" alt="Screenshot 2025-09-03 191333" src="https://github.com/user-attachments/assets/d010fd61-7693-48ae-9da2-e0cc3fb7f22d" />

   ------------
   1b. Add-ons > Install…
   
   <img width="1919" height="1033" alt="Screenshot 2025-09-03 190831" src="https://github.com/user-attachments/assets/bcf4662e-bf6d-4f18-b503-10ecbed10995" />
   
3. Pick the ZIP and enable the add-on.
   
   ------------

## Where to find it in Blender
**Shader Editor**
<img width="1919" height="1032" alt="Screenshot 2025-09-03 192809" src="https://github.com/user-attachments/assets/cad0badd-398a-42db-b190-3677fa67bec0" />
**Sidebar (N) > “Anime & Manga” tab"**
<img width="1919" height="1032" alt="Screenshot 2025-09-03 193035" src="https://github.com/user-attachments/assets/10c78d1e-dec0-4b19-8da5-0650fef83643" />

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
- User presets are removeable. Built-in defaults are protected from deletion.
- Texture overlay properties exist per material; controls appear when a material is active.
- The panel is available when the Shader Editor is active.

## Support & Contributions
- Issues and feature requests: https://github.com/AtomaHuro/Anime-Tools/issues

## License
- MIT License (see `LICENSE`).
