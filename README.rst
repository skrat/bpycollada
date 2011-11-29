Blender COLLADA import/export
=============================
This export addon is based on `pycollada <http://pycollada.github.com/>`_ library.
It was created as a replacement for current `Blender <http://www.blender.org/>`_ 2.5,
OpenCOLLADA/C++ export/import, which is buggy and suffers from external dependencies.

COLLADA 1.4.1 supported features (import)
-----------------------------------------
* Geometry
   * Triangle mesh
   * Polylist (quads)
* Rendering
   * Constant, Lambert, Phong and Blinn shaders
   * Textures with alpha channel
   * Reflectivity
   * Transparency
* Camera
   * Perspective
   * Orthographic

Blender features (export)
-------------------------
* Triangle/Quad meshes
* Smoothing groups

