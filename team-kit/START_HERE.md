# PPT Studio 全套 Skills 使用包

本入口兼容原来的 `bp-to-image2-pitch-deck` 使用包，现已包含研究、分析、叙事、设计、原生制作与质量检查。完整新版从 `$ppt-studio` 开始，Noir 是可选风格，原生可编辑 PPTX 是默认输出。

## 使用

1. 将完整包交给 Codex，并同时提供自己的简报和来源材料。
2. 发送 `CODEX_INSTALL_AND_RUN.txt` 中的任务入口。它会从兼容入口读取完整协调 Skill，再按需要使用分析、设计、制作等模块。
3. 若要安装成独立的八个 Skills，在解压包目录运行：

```text
python -m pip install -r skill/bp-to-image2-pitch-deck/requirements-ppt.txt
python skill/bp-to-image2-pitch-deck/tools/ppt.py install
```

已有同名 Skill 时先检查；明确用 `--replace` 才备份更新。无法安装时可直接读取包内 Skill 执行任务。旧的 `install_skill.py` 仍可安装完整仓库的兼容入口，保留原使用方式。

私人任务应在包外的新目录完成。保持原始材料，核验事实和数据，不将公司图片或研究底稿公开到仓库。

研究、生图和渲染使用实际可用的 Codex 工具；缺少某项能力时说明限制并继续独立工作。检查通过只表示对应检查已执行，不代表所有图像模型或 PowerPoint 环境都可用。
