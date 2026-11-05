# まちかどマート · 雨夜街角微缩模型

GitHub: https://github.com/YH-Chen444/machikado-mart-rainy-diorama

基于参考图，在 **Blender 5.2.2 LTS** 中全程序化搭建的日式雨夜便利店街角微缩场景。
风格为三渲二／日式动画夜景：Toon 分级着色 + 暖色灯箱 + 冷色夜色 + Freestyle 描边 + EEVEE 体积雾和泛光。

## 交付文件

| 文件 | 说明 |
| --- | --- |
| `machikado_mart.blend` | 当前动画版本：动态雨、循环涟漪、轻微环绕镜头；854×480 / 24 fps / 150 帧。静态图可用 `machikado_mart_static.blend`。 |
| `machikado_mart_animated.blend` | 动态雨 / 涟漪 / 环绕镜头版本的工作副本。 |
| `machikado_mart_static.blend` | 加动画前的静态备份（1920×1080 / 96 samples 主视觉场景）。 |
| `renders/machikado_mart_rain_480p.mp4` | 150 帧、480p、H.264 雨夜微缩动画。 |
| `renders/machikado_mart_rain_preview.png` | 动态版第 80 帧静帧预览（854×480）。 |
| `renders/machikado_mart_hero.png` | 主视觉，1920×1080，96 samples。 |
| `renders/machikado_mart_detail.png` | 街角细节特写，1920×1080，96 samples。 |
| `scripts/build_scene.py` | 全程序化生成脚本，可在 Blender 5.2 中重新生成整个场景。 |
| `scripts/add_animation.py` | 给静态场景添加动态雨、涟漪和镜头运动。 |
| `scripts/render_animation.py` | 渲染 150 帧 480p MP4。 |
| `refs/` | 原参考图。 |

## 场景内容

- 正方形收藏级底座，深色包边 + 细黄铜装饰线。
- 两层日式便利店：奶油色外墙、发光招牌、玻璃橱窗、自动门、门垫、雨棚、遮阳伞、A 字咖啡牌、雨伞架。
- 室内：彩色商品墙、冷藏柜、杂志架、收银台、吊牌、天花板日光灯、暖色溢光。
- 街角元素：两台自动贩卖机、自行车、垃圾桶、回收筐、路灯、4 根电线杆和悬垂电线、凸面镜、限速 30 标志、绿色路牌、P 停车标志、护栏、锥桶、停车位、小货车。
- 街面：湿沥青、积水、雨滴涟漪、反光斑马线、井盖、排水沟、黄色盲道、路缘石。
- 左侧：小料理店、红色灯笼、暖帘、路地入口、树、花坛、报纸箱。
- 背面：后门、后窗、壁灯、空调外机、电表箱、送货箱、后巷栏杆。
- 氛围：雨线、体积雾、远处街灯冷光、粉色霓虹、Composite Bloom、暗角、低饱和夜景调色。

## 动态版：雨、涟漪、镜头

动态版在静态场景基础上增加：

- **Geometry Nodes 雨场**：1200 条实例化雨线，按 `Scene Time` 连续下落，使用 12 m 高的 wrap 循环；雨线长度随机，带有轻微斜度。
- **循环涟漪**：28 圈积水涟漪与 24 个溅射水花各自独立脉动；扩散时透明度渐隐，回到小尺寸时完全透明，因此循环无跳变。
- **轻微镜头运动**：`IsoCamera` 在 150 帧内沿极小的弧线移动并回到原位，`Track To` 始终对准店铺；视频可无缝循环播放。
- **输出规格**：854×480（16:9 480p）、24 fps、150 帧（6.25 秒）、EEVEE、20 samples、Freestyle、H.264 MP4。
- 已用 Blender 读取验证视频：150 帧 / 854×480 / 24 fps。

## 相机

`.blend` 中提供 4 台正交相机：

- `IsoCamera`：默认主视觉；动态版带有轻微环绕动画。
- `Camera_Detail`：街角近景。
- `Camera_Reverse`：背面视角，检查后巷细节。
- `Camera_FrontLeft`：左前方视角。

打开文件后可自由旋转、缩放、拖拽观看；在 Outliner 中可展开 `MACHIKADO_MART` 下的分层集合。

## 渲染设置

静态图：

- Engine：EEVEE
- Resolution：1920 × 1080
- Render samples：96
- Freestyle：开启，1.25 px 墨线
- View Transform：Standard
- Compositor：Bloom + Hue/Saturation + Lift/Gamma/Gain + 柔边暗角

动态版：

- Resolution：854 × 480
- FPS / Frames：24 fps / 1–150
- Render samples：20
- Format：FFmpeg / MPEG-4 / H.264
- 输出：`renders/machikado_mart_rain_480p.mp4`

## 重新生成 / 渲染

```powershell
# 最终版：构建并渲染 1920×1080
& 'D:\blender\blender.exe' -b --factory-startup `
  --python 'D:\Master\dps harness\deepseek_project3\scripts\build_scene.py' -- --final

# 预览版：构建并渲染 1280×720, 28 samples
& 'D:\blender\blender.exe' -b --factory-startup `
  --python 'D:\Master\dps harness\deepseek_project3\scripts\build_scene.py' -- --preview

# 只构建并保存，不渲染
& 'D:\blender\blender.exe' -b --factory-startup `
  --python 'D:\Master\dps harness\deepseek_project3\scripts\build_scene.py' -- --no-render
```

细节图：

```powershell
& 'D:\blender\blender.exe' -b '.\machikado_mart_static.blend' `
  --python '.\scripts\render_detail.py'
```

生成动画场景与视频：

```powershell
# 从静态备份生成带动态雨 / 涟漪 / 镜头的 animated .blend
& 'D:\blender\blender.exe' -b --factory-startup `
  --python '.\scripts\add_animation.py'

# 渲染 150 帧、854×480 的 MP4
& 'D:\blender\blender.exe' -b --factory-startup `
  --python '.\scripts\render_animation.py'
```

所有几何、材质、文字招牌、雨线和灯光都由 Python 生成；未使用外部模型或贴图。
