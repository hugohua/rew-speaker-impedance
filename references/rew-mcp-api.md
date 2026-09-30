# REW MCP 阻抗数据读取

## 调用顺序

1. `mcp__rew__check_connection({})`：确认 REW API 可达。
2. `mcp__rew__get_rew_environment({})`：需要判断配置是否漂移时读取环境。
3. `mcp__rew__list_measurements({})`：取得 UUID、索引、标题、日期、备注与频率范围。
4. 对目标 UUID 调用 `mcp__rew__get_frequency_response_numeric` 获取阻抗和相位。

不要仅按标题选取曲线；REW 会生成大量同名测量。优先使用 UUID，并把索引、时间与用户对测量顺序的说明一起呈现。

## 关键 API

### 列出测量

工具：`mcp__rew__list_measurements`，参数为 `{}`。

典型返回字段：`uuid`、`index`、`title`、`notes`、`date`、`startFreq`、`endFreq`、`sampleRate`。

### 获取数值曲线

```json
{
  "id": "measurement-uuid",
  "ppo": 96,
  "unit": "ohm"
}
```

工具：`mcp__rew__get_frequency_response_numeric`

关键返回字段：

- `frequencies_hz`
- `magnitude_db`
- `phase_deg`
- `metadata.unit`

REW MCP 当前即使请求 `unit: "ohm"`，数组字段仍可能叫 `magnitude_db`，但当 `metadata.unit` 为 `ohm` 时，数组数值是欧姆，不是 dB。不要根据字段名把 3.2、16.1 等阻抗值误写成 dB。

`mcp__rew__analyze_measurement` 可快速浏览曲线，但其文本标签也可能显示 `dB`；正式阻抗计算应使用数值 API 和 `metadata.unit`。

### 保存测量

工具：`mcp__rew__save_measurements`

仅在用户要求归档时调用，传入绝对 `.mdat` 路径与可选备注。默认不要删除、改名或覆盖现有测量。

## 代码模式示例

```javascript
const listed = await tools.mcp__rew__list_measurements({});
const measurements = listed.structuredContent.result;
const target = measurements.find(x => x.index === 17);
const response = await tools.mcp__rew__get_frequency_response_numeric({
  id: target.uuid,
  ppo: 96,
  unit: "ohm"
});
const data = response.structuredContent;
```

若工具不是直接暴露而是延迟加载，先在可用工具目录中查找 `mcp__rew__`；不要臆造端点或用 UI 自动化替代现成 API。

## 曲线分析方法

1. 在预期谐振区间（通常 20–200Hz）寻找主阻抗峰。
2. 在主峰附近寻找相位从正到负的零交点并线性插值，作为 `Fs`。若相位过零不清晰，再使用峰值频率并注明。
3. `Re` 优先来自扣除表笔电阻后的万用表值；曲线只能取谐振以上、音圈电感上升以前的最低/平坦区作近似。
4. 重复测量至少比较：`Fs`、峰值、基线、高频斜率和相位。相同状态的 `Fs` 差异目标小于 0.5%。
5. 整体比例变化通常是电气链路；只有峰区变化通常是机械支撑或单元状态。

对于附加质量测试，按用户说明将自由空气与配重曲线一一配对。姿态不同的数据分别计算；例如“垂直手持”不能与“水平放桌面”的另一状态配成一组。

