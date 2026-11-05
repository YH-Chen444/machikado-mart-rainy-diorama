import bpy, os, time
ANIM = r"D:\Master\dps harness\deepseek_project3\machikado_mart_animated.blend"
OUT = r"D:\Master\dps harness\deepseek_project3\renders\machikado_mart_rain_480p.mp4"
bpy.ops.wm.open_mainfile(filepath=ANIM)
scn = bpy.context.scene
scn.render.image_settings.media_type = "VIDEO"
scn.render.image_settings.file_format = "FFMPEG"
scn.render.image_settings.color_mode = "RGB"
scn.render.ffmpeg.format = "MPEG4"
scn.render.ffmpeg.codec = "H264"
scn.render.ffmpeg.constant_rate_factor = "HIGH"
scn.render.ffmpeg.ffmpeg_preset = "GOOD"
scn.render.ffmpeg.audio_codec = "NONE"
scn.render.resolution_x = 854
scn.render.resolution_y = 480
scn.render.resolution_percentage = 100
scn.render.fps = 24
scn.render.use_file_extension = False
scn.frame_start = 1
scn.frame_end = 150
scn.eevee.taa_render_samples = 20
if os.path.exists(OUT):
    os.remove(OUT)
scn.render.filepath = OUT
print("RENDER ANIMATION", OUT, scn.render.resolution_x, scn.render.resolution_y,
      "samples", scn.eevee.taa_render_samples, "frames", scn.frame_start, scn.frame_end)
t0 = time.time()
bpy.ops.render.render(animation=True)
print("ANIMATION DONE in", round(time.time() - t0, 1), "sec")
print("EXISTS", os.path.exists(OUT), "SIZE", os.path.getsize(OUT) if os.path.exists(OUT) else None)
