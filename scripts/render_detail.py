import bpy, os
scn = bpy.context.scene
scn.render.resolution_x = 1920
scn.render.resolution_y = 1080
scn.render.resolution_percentage = 100
scn.eevee.taa_render_samples = 96
cam = bpy.data.objects.get('Camera_Detail')
if cam is None:
    raise RuntimeError('Camera_Detail missing')
scn.camera = cam
scn.render.filepath = r'D:\Master\dps harness\deepseek_project3\renders\machikado_mart_detail.png'
bpy.ops.render.render(write_still=True)
print('DETAIL DONE', scn.render.filepath)
