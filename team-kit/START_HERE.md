# Image2 投行 PPT Codex 使用包

这个包用于把 `bp-to-image2-pitch-deck` 交给另一位同事的 Codex。它不是“截图转可编辑 PPT”的 rebuild 工作流，而是从 Prompt、公司资料和参考材料出发，重新组织内容并用 Image2 生成高级版 Pitch Deck。

## 最快用法

1. 把整个 ZIP 上传给 Codex，不必先手动解压。
2. 同时上传本次项目资料：公司信息、参考资料、可选 BP、可选 Logo/品牌/视觉参考。
3. 把 `CODEX_INSTALL_AND_RUN.txt` 的内容原样发送给 Codex。
4. Codex 会优先尝试安装 Skill；若当前环境不能持久安装，则自动采用包内 Skill 执行本次任务。

## 两种模式

### A. 便携执行（零安装）

适合只做一次或没有本机目录权限。Codex 读取：

```text
skill/bp-to-image2-pitch-deck/SKILL.md
```

然后按文件中的渐进式路由，只加载当前阶段需要的 reference。该方式不影响交付质量。

### B. 永久安装（推荐给经常使用者）

让 Codex 运行：

```bash
python install_skill.py
```

默认安装到 `$CODEX_HOME/skills/bp-to-image2-pitch-deck`；未设置 `CODEX_HOME` 时使用用户目录下的 `.codex/skills`。已有不同版本时，安装器不会直接覆盖；明确更新时运行：

```bash
python install_skill.py --update
```

安装器会先创建时间戳备份，再写入新版本。

## 标准调用

```text
使用 $bp-to-image2-pitch-deck，根据我上传的 Prompt、公司资料和参考文件，
自动选择最有说服力的页面，生成一套高质量投资人路演 PPT。
BP 和视觉参考如有则使用，没有也不要停；所有数字必须可追溯，视觉由 Image2 完成。
```

需要更精准时，填写 `REQUEST_TEMPLATE.md`。不要把同一份长资料在聊天中重复粘贴；上传一次并引用文件名即可。

## 推荐模型与思考强度

| 场景 | 建议 | 原因 |
| --- | --- | --- |
| 常规 8-15 页 Pitch Deck | `gpt-5.6-sol` + `high` | 质量与 Token 消耗的最佳默认平衡 |
| 资料杂乱、财务口径复杂、关键对外材料 | `gpt-5.6-sol` + `xhigh` | 增强证据梳理、叙事选择与交叉核验 |
| 安装、文件盘点、脚本验证、简单改单页 | `medium` | 这些步骤可由确定性脚本承担，不需要持续高推理 |
| `ultra` | 只在高风险、来源冲突严重且 `xhigh` 仍不足时使用 | 不应作为默认，Token 成本通常高于边际收益 |

如环境支持，使用 `priority` 服务等级提高执行速度；不要为省 Token 降低 Image2 出图质量或跳过 PPT 渲染 QA。

## 省 Token 但不降质量

- 只让 Codex 首先读取 `SKILL.md`，随后按阶段读取对应 reference，避免一次加载全部说明。
- 来源盘点、Brief 校验、Prompt Pack 生成和发布扫描优先运行包内脚本。
- 先一次性上传所有已知资料；让 Codex 先输出“证据缺口清单”，只补真正影响结论的材料。
- 先确认页面计划与关键事实，再批量生成 Image2，减少无效重画。
- 同一视觉方向只保留一套主方案；确需探索时，先对 1-2 张代表页做 A/B 测试。
- 修改时指出页码、元素和目标，不要重复整份项目背景。

## 交付边界

- 输出是每页一张完整 Image2 视觉组成的 PPTX，不是对象级可编辑重建。
- 不允许编造数字、客户、合同、市场份额、估值、功能或引用。
- Logo、产品图、界面和报告截图等事实性资产必须保持真实，不交给 Image2 重绘。
- 所有客户资料默认私密；工作目录必须位于 Skill 仓库之外。
- 最终交付前必须渲染导出的 PPTX 并逐页检查。

## 包内文件

- `CODEX_INSTALL_AND_RUN.txt`：直接发给 Codex 的最短机器指令。
- `REQUEST_TEMPLATE.md`：项目请求模板。
- `install_skill.py`：跨平台安全安装/更新。
- `verify_package.py`：文件哈希、Skill 结构和测试校验。
- `PACKAGE_MANIFEST.json`：版本、来源与 SHA-256 文件清单。
- `skill/bp-to-image2-pitch-deck/`：完整 Skill。

项目主页：<https://github.com/wangqi045788-byte/bp-to-image2-pitch-deck>
