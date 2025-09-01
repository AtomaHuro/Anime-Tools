# Anime Pipeline Add-on — User Guide (Prototype)

Install
1. In Blender, Edit > Preferences > Add-ons > Install...
2. Select the folder `addons/anime_pipeline` (zip this folder first or select the `.py`).
3. Enable "Anime Pipeline".

Panel
- Location: 3D Viewport > N panel > "Anime" tab.

Buttons
- Setup Anime Scene: Sets Eevee base settings, fps, color management, and common passes.
- Apply Toon Material: Assigns `Anime_Toon` material (backed by `Toon_Shade_Core` group) to selected meshes.
- Add Outline (Inverted Hull): Adds a flipped-normals solidify hull with outline color/thickness.
- Enable Freestyle Lines: Turns on Freestyle for the view layer and creates a default lineset/linestyle (thickness, color; silhouette/crease toggles).
 - Setup Compositor Template: Creates a comp node tree that darkens shadows, and adds rim/specular tints using the AOV masks.
 - Create Toon Lighting Rig: Adds a ground plane, a camera, and a 3-point lighting rig tuned for toon looks.
 - Batch Render Cameras: Renders the current frame from all cameras to files named by camera.

Tips
- Use on a duplicate file while experimenting.
- Animate first with neutral materials; apply toon and outlines once timing is locked.
- For thicker lines on distant shots, increase Outline Thickness or add Freestyle/GP Line Art.
- The toon material writes ShadowMask, RimMask, and SpecularMask to AOVs; ensure the view layer has these AOVs (the Scene Setup button creates them) and use the Compositor Template for a quick start.

Limits (Prototype)
- Shader group focuses on Eevee; Cycles may differ.
- Freestyle presets are basic; Grease Pencil Line Art is not yet wired.
