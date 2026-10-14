# REW 扬声器阻抗与 T/S 测试技能

这是一个用于 Codex 的个人技能，帮助使用 REW、UMC202HD 和 DIY 阻抗测量盒完成：

- 开路、短路、参考电阻三步校准；
- 无源扬声器阻抗曲线读取与重复性分析；
- `Re`、`Fs`、`Qms`、`Qes`、`Qts`、`Le` 等参数整理；
- 附加质量法计算 `Mms`、`Cms`、`Vas` 和可选的 `Bl`；
- 单元一致性、维修前后差异及异常曲线判断；
- 密闭箱净容积、`Qtc`、`Fc`、`F3` 和响应峰值初步估算。

本技能针对当前已验证的 UMC202HD + 47Ω DIY 阻抗盒进行了配置，同时保留了其他声卡或测量夹具所需的参数核对步骤。

## 安装

在尚未安装该技能的设备上，可以直接克隆到 Codex 技能目录：

```bash
git clone git@github.com:hugohua/rew-speaker-impedance.git \
  ~/.codex/skills/rew-speaker-impedance
```

已有本地仓库时更新：

```bash
cd ~/.codex/skills/rew-speaker-impedance
git pull --ff-only
```

## 使用方法

在 Codex 中显式调用：

```text
使用 $rew-speaker-impedance 分析当前 REW 中的扬声器阻抗测量。
```

也可以直接描述任务，例如：

```text
读取 REW 当前最后四条阻抗曲线，前两条是自由空气，后两条加了 10.67g，计算 T/S 参数并判断重复性。
```

技能默认允许自动触发，但涉及删除测量、改变 REW 配置、应用 EQ 或覆盖文件时，仍需用户明确要求。

## 当前阻抗盒基线

| 项目 | 设置 |
|---|---|
| 声卡 | Behringer UMC202HD |
| 测试输出 | PHONES 左声道 |
| 参考输入 | Input 1 / L |
| 测量输入 | Input 2 / R |
| `R_SENSE` | 47.00Ω 标称，优先填写万用表实测值 |
| `R_REF` | 10.00Ω |
| `R_INPUT` | 20,000Ω |
| 采样率 | 44.1kHz |
| 阻抗扫频 | 20Hz–20kHz、512k、重复2次 |
| 起始电平 | -30dBFS，检查电平后再谨慎提高 |

UMC202HD 两路输入应使用 `LINE`，PAD 和 +48V 关闭。完成校准后不要改变输入增益、PHONES 音量、声道、采样率或线材。

推荐流程：

```text
检查硬件与声道路由
→ 开路校准
→ 短路校准
→ 10Ω参考校准
→ 用另一只已知电阻独立验证
→ 自由空气测量2–3次
→ 附加质量测量2–3次
→ 计算T/S并评估重复性
→ 估算箱体
→ 完成箱体后进行麦克风声学测量
```

## REW MCP 数据读取

技能主要使用以下只读工具：

- `mcp__rew__check_connection`
- `mcp__rew__get_rew_environment`
- `mcp__rew__list_measurements`
- `mcp__rew__get_frequency_response_numeric`

正式计算时以测量 UUID 为准，不依赖可能重复的标题。请求阻抗数据的典型参数为：

```json
{
  "id": "measurement-uuid",
  "ppo": 96,
  "unit": "ohm"
}
```

当前 REW MCP 返回的阻抗数组字段可能仍命名为 `magnitude_db`。当 `metadata.unit` 为 `ohm` 时，其中的数据是欧姆值，不能按 dB 解读。详细说明见 [REW MCP API 参考](references/rew-mcp-api.md)。

## 附加质量计算脚本

脚本 [ts_added_mass.py](scripts/ts_added_mass.py) 可对多组自由空气/配重谐振频率逐对计算，并模拟多个密闭箱净容积：

```bash
python3 scripts/ts_added_mass.py \
  --pair 58.772,44.993 \
  --pair 58.772,45.319 \
  --mass-g 10.6667 \
  --sd-cm2 147.4 \
  --qts 0.745 \
  --volumes 10,12,15,18,20
```

也可以用 `--dd-mm` 代替 `--sd-cm2`。如果同时提供可靠的 `--re` 和 `--qes`，脚本会计算 `Bl`。

本地临时螺丝称重记录：

| 数量 | 估算质量 |
|---:|---:|
| 4颗 | 约2.67g |
| 12颗 | 约8.00g |
| 16颗 | 约10.67g |
| 30颗 | 约20g |

该重量来自低分辨率厨房秤，只适合近似分析。正式 T/S 测量应使用 0.1g 或更高精度电子秤称量总配重。

## 项目结构

```text
rew-speaker-impedance/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── hardware-workflow.md
│   ├── rew-mcp-api.md
│   └── ts-and-enclosure.md
└── scripts/
    └── ts_added_mass.py
```

## 使用边界

- 只把阻抗盒连接到无源扬声器或无源元件；不要把功率放大器输出直接接入声卡输入。
- 阻抗和 T/S 参数不能代替麦克风频响、相位、指向性、失真和最大声压测量。
- 箱体计算使用净容积；需要扣除单元、加强筋、分频器和其他内部结构。
- 无配重和配重测试必须保持同一单元、姿态、支撑、线材与电平，不同姿态应分别计算。

更完整的测量流程见 [硬件工作流](references/hardware-workflow.md)，计算原则见 [附加质量法与箱体估算](references/ts-and-enclosure.md)。
