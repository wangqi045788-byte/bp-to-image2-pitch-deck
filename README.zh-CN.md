# BP 到 Image2 高级路演 PPT

这是一个独立的 Codex“画 PPT”Skill：用户只需要提供 Prompt、公司信息和参考资料，即可让 Skill 自动整理证据、判断应该生成哪些页面、提炼品牌视觉语言、生成逐页高复杂度 Prompt，再交给 Image2 生成整套高级 Pitch Deck。

BP 和参考视觉都是可选项。资料不完整时，Skill 会减少页数、记录假设和缺口，不会为了凑模板自行补数字或编造内容。

## 与“转 PPT”项目的区别

- 本项目 `bp-to-image2-pitch-deck`：从 Prompt 和资料出发，重新选择内容、组织叙事并设计新 PPT。
- [`editable-ppt-image2-rebuild`](https://github.com/wangqi045788-byte/editable-ppt-image2-rebuild)：把已有截图、PDF 页面或不可编辑 PPT 重建成可编辑对象。

两者是两个自动化工作流，不混在同一个 Skill 中。

## 支持的输入

- 用户 Prompt：目的、受众、重点、语言、页数或使用场景；
- 公司信息与各种参考资料；
- BP、旧版材料或初步大纲（可选）；
- Logo、品牌手册、产品图、界面截图、报告截图和参考视觉（可选）。

## 核心流程

`Prompt与资料 → 来源盘点 → 证据卡 → 飞书式工作文档 → 叙事与页面选择 → Logo/官网/资料品牌识别 → 配色与版式系统 → 逐页高复杂度Prompt → Image2高级视觉生成 → PPT封装 → 实机渲染与QA`

关键原则：

- 不套固定页数，先判断用户真正需要哪些页面；
- 真实数字、日期、客户、排名、产品能力和引用必须有证据；
- 公司披露、计算结果、用户陈述和分析判断必须分开；
- 真实 Logo、产品图、界面和报告截图不得重绘或篡改；
- 拒绝与公司无关的通用科技蓝、蓝紫霓虹、玻璃拟态和卡片墙；
- 一页只讲一个决策信息，普通内容页最多三个主视觉区；
- 先压缩文案并锁定版式，再生成视觉，不能靠小字体救场；
- 最终每页是一张完整 Image2 视觉，不冒充“对象级可编辑重建”；
- 客户资料、内部 Prompt、生成图和工作目录不得进入公开仓库。

## 使用方式

将仓库安装到 Codex Skills 目录后调用：

```text
$bp-to-image2-pitch-deck
```

示例：

```text
使用 $bp-to-image2-pitch-deck，根据我提供的 Prompt、公司资料和参考文件，
自动选择最有说服力的页面，生成一套高质量投资人路演 PPT。BP 和参考视觉如有则使用，
没有也不要停；所有数字必须可追溯，视觉设计交给 Image2。
```

## 本地辅助脚本

```bash
python scripts/init_job.py /path/to/private-job --title "Company pitch"
python scripts/validate_deck_brief.py /path/to/deck-brief.json
python scripts/prepare_generation.py /path/to/deck-brief.json --out /path/to/prompt-pack.md
```

公开前必须运行：

```bash
python -m unittest discover -s tests -v
python scripts/public_release_check.py . --denylist /path/to/private-denylist.txt
```

自动扫描通过不代表已经完成公司所有权、合规、品牌或第三方素材授权审查。
