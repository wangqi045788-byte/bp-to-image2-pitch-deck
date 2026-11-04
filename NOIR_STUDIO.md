# Noir PPT Studio · 一键生成可编辑 PPT 的 Skill

把简报、公司资料和参考图片，变成有摄影表现力、可编辑文字和图形的演示文稿。保留这套工作流的关键审美：真实黑白摄影、清晰的视觉焦点、细衬线标题、克制的正文、艺术图录式留白，以及整套页面的节奏。

这是一套 **Codex Skill + 一键入口 + 原生转换工具**。创意、研究和生图由你的 Codex 会话及可用工具执行；Python 脚本负责安装、任务组织、SVG 转 PPT 和检查。它不是离线生图模型，也不附带 API 额度。

## 安装和使用

需要 Python 3.10+、可正常使用的 Codex。首次安装转换依赖：

```bash
python -m pip install -r requirements-noir.txt
python tools/noir.py install
```

Windows 也可双击 `install-noir.cmd` 安装 Skill。安装器只复制本包；不修改账号、模型、权限设置或全局字体。已有同名 Skill 时停止；明确使用 `--replace` 才先备份再更新。

在 Codex 中输入：

```text
使用 $noir-ppt-studio，根据我提供的公司资料和参考图，制作 12 页黑白摄影风格的高端汇报。
请先核验资料，再完成设计、生图或配图、原生可编辑 PPT、逐页 SVG、中文演讲备注和逐页检查。
图片要符合公司特点，避免重复；不要做成全是字的模板。
```

或者编辑 `NOIR_REQUEST.md`，把简报文件拖到 `start-noir.cmd` 上。命令行等价用法：

```bash
python tools/noir.py generate --brief my-brief.md --job ../my-deck --assets my-source-folder
```

`--assets` 可省略。任务目录必须是仓库外的全新目录，私人资料和生成结果不会进入 Git 仓库。生成调用本机 Codex，沿用现有账号与可用工具，保持 `workspace-write` 隔离，不使用跳过权限的参数。

用 `--dry-run` 只准备任务和请求，不调用模型；这不会产出 PPT。用 `python tools/noir.py doctor` 检查基础环境。

## 包含的能力

| 环节 | 实际能力 |
| --- | --- |
| 视觉设计 | 提取参考构图、光线、字体比例、层级和留白；已选方向贯穿全套 |
| 图片 | 公司真实图与原创概念图分开记录；按主体检查重复，而非只比较文件名 |
| 内容 | 日期、单位、口径、事实与目标分清；完整解释和来源保留在备注 |
| 转换 | 文字、线、矩形、多边形为原生对象；摄影为独立图片；输出逐页 SVG |
| 字体 | 可选 Bodoni Moda Editorial 附 OFL 许可；不自动安装到系统 |
| 检查 | PPTX 完整性、页数、对象、备注；Windows 可调用 PowerPoint 渲染和编辑回存 |

自带转换器覆盖本 Skill 的页面 JSON。复杂滤镜、外部多段 `<tspan>`、公式和原生图表应采用相应的专门路径。

## 输出与验收

任务主文件是 `output/deck.pptx`。Skill 按请求补齐 SVG、备注、来源/图片清单、PDF和总览图；PDF与渲染依赖环境的可用工具。

原生对象检查通过，说明文字和图形可编辑，**不代表每页排版和审美已经检阅通过**。最终需要检查实际导出的页面，包括字体替换、溢出、裁切和重复。没有 PowerPoint 或渲染能力时，会标注限制。

Codex CLI 与桌面应用可能拥有不同的生图工具。CLI 缺少生图能力时，可在具备图像工具的桌面会话调用此 Skill，或提供可用图片。仓库不伪称调用 Image2.5：只有工具返回型号时才记录具体型号，否则记为未知。

## 无需模型的演示

```bash
python tools/noir.py demo --out ../noir-demo
```

此命令实际生成两页原生 PPTX、SVG 并检查结构。样例是合成文字与几何图形，用于验证安装和转换，**不是摄影审美的成品展示**。

```bash
python -m unittest discover -s tests -v
python scripts/public_release_check.py . --skip-history
```

PowerPoint 编辑回存集成测试默认不运行。在可用且适合测试的 Windows 环境，可设置 `RUN_POWERPOINT_QA_INTEGRATION=1`。未执行的检查不计为通过。

## 文件与素材边界

- `skills/noir-ppt-studio/`：可单独复制安装的完整 Skill。
- `tools/noir.py`：安装、生成、演示、环境检查。
- `examples/noir-demo/`：没有真实公司数据的转换样例。
- `requirements-noir.txt`：固定版本的转换依赖。

原有 Skill 和使用包保留。这一新增流程承接可编辑摄影式 PPT，不强制所有公司采用黑白。

通用代码沿用 MIT 许可；转换器保留 FigEdit/PPT Master 的 MIT 声明；字体遵循 OFL。开云成品、品牌照片、用户附件、演讲稿和研究底稿没有上传。你的输入和生成成品不会自动成为 MIT 开源素材。
