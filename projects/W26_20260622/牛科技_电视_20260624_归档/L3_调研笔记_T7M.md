# L3 · 调研笔记 · TCL T7M Ultra vs Pro

> 调研日期：2026-06-24
> 调研人：intel-teardown
> 选题方向：TCL T7M Ultra 卖第一 Pro 反第三，拆开配置才懂销量王不等于参数王

---

## 一、核实的参数（来源 URL 必附）

### TCL 85T7M Ultra（京东独家型号）

| 参数 | 数值 | 来源 |
|------|------|------|
| **背光分区** | 最高2176个万象分区 | [京东电视LED排行榜](https://www.jd.com/phb/key_73725d529056c6f39ff.html) |
| **峰值亮度** | 绚彩XDR 3000尼特 | [京东电视85排行榜](https://www.jd.com/phb/key_737d502e36fe22ac065.html) |
| **刷新率** | 4K 150Hz | [京东电视85排行榜](https://www.jd.com/phb/key_737d502e36fe22ac065.html) |
| **色域** | 100% BT.2020全局高色域 | [京东价格行情](https://www.jd.com/jiage/737e5dec3e542ee268e.html) |
| **技术** | SQD-Mini LED | [京东价格行情](https://www.jd.com/jiage/737e5dec3e542ee268e.html) |
| **屏幕** | 超级蝶翼星曜屏 | [京东电视LED排行榜](https://www.jd.com/phb/key_73725d529056c6f39ff.html) |
| **芯片** | TSR AI光色同控芯片 | [知乎专栏 - T7M Pro评测](https://zhuanlan.zhihu.com/p/493254477) |
| **内存** | 4GB + 64GB | [京东价格行情](https://www.jd.com/jiage/737e5dec3e542ee268e.html) |
| **京东独家** | 是 | [京东电视LED排行榜](https://www.jd.com/phb/key_73725d529056c6f39ff.html) |
| **京东价格** | 活动价¥9,999，国补后低至¥7,510.6元 | [京东价格行情](https://www.jd.com/jiage/737e5dec3e542ee268e.html) |
| **销量排行** | 85寸LED排行榜TOP1、全球平板电视排行榜TOP1 | [京东电视85排行榜](https://www.jd.com/phb/key_737d502e36fe22ac065.html) |

### TCL 85T7M Pro

| 参数 | 数值 | 来源 |
|------|------|------|
| **背光分区** | 1056万象分区 | [电视LED排行榜](https://www.jd.com/phb/key_73725d529056c6f39ff.html) |
| **峰值亮度** | 2500尼特 | [电视LED排行榜](https://www.jd.com/phb/key_73725d529056c6f39ff.html) |
| **刷新率** | 4K 150Hz | [IT之家实拍](https://www.ithome.com/0/950/493.htm) |
| **色域** | 100% BT.2020全局高色域 | [京东价格行情](https://www.jd.com/jiage/985519eb94d2eaed5248.html) |
| **技术** | SQD-Mini LED | [京东价格行情](https://www.jd.com/jiage/985519eb94d2eaed5248.html) |
| **芯片** | TSR AI光色同控芯片 | [知乎专栏 - T7M Pro评测](https://zhuanlan.zhihu.com/p/493254477) |
| **内存** | 4GB + 64GB | [京东价格行情](https://www.jd.com/jiage/985519eb94d2eaed5248.html) |
| **京东价格** | 官方活动价¥9,999，最低可至¥6,289.91元 | [京东价格行情](https://www.jd.com/jiage/985519eb94d2eaed5248.html) |
| **销量排行** | UNSURE（传闻TOP3，需进一步核实） | UNSURE |

---

## 二、核心技术差异

### SQD-Mini LED vs QD-Mini LED

| 技术维度 | SQD-Mini LED | QD-Mini LED | 来源 |
|---------|--------------|-------------|------|
| **色域覆盖** | 100% BT.2020全局色域 | 80%-85% BT.2020 | [知乎专栏 - RGB/SQD对比](https://zhuanlan.zhihu.com/p/1950963337761382951) |
| **发光架构** | 摒弃RGB三色灯珠混光，由背光激发"超级量子点层" | 传统蓝光激发量子点 | [TCL官方博客](https://www.tcl.com/au/en/blog/sqd-mini-led-vs-rgb-mini-led-vs-qd-mini-led-vs-oled-2026) |
| **技术定位** | TCL旗舰显示技术，QD-Mini LED的升级命名 | 主流性价比路线 | [智度科技](https://m.zhidx.com/p/506912.html) |

**一句话总结**：SQD-Mini LED是TCL对QD-Mini LED的技术升级，色域从80%-85% BT.2020提升到100% BT.2020，同时保留了QD的稳定控光优势。

---

## 三、CEO战报核实

### CEO 战报内容
- T7M Ultra：京东85寸榜TOP1
- T7M Pro：京东85寸榜TOP3

### 核实结果
- ✅ **T7M Ultra TOP1**：已核实（[京东85寸LED排行榜](https://www.jd.com/phb/key_737d502e36fe22ac065.html)、[全球平板电视排行榜](https://www.jd.com/phb/key_73725d529056c6f39ff.html)）
- ⚠️ **T7M Pro TOP3**：UNSURE，搜索结果未直接显示Pro的具体排名，需进一步核实京东85寸排行榜TOP3位置

### TCL整体618表现
- ✅ 已核实：在京东平台5月13日至6月21日平板电视竞速累计榜中，TCL位居累计榜第一名（[搜狐报道](https://www.jd.com/phb/key_7379edc8266694a0b05.html)）

---

## 四、关键发现（信息增益方向）

### 1. 销量王 ≠ 参数王
- **Ultra（销量王）**：2176分区 + 3000nits + 京东独家
- **Pro（参数更强？）**：1056分区 + 2500nits
- **价格反差**：Ultra国补后¥7,510.6 vs Pro最低¥6,289.91，Ultra参数更强但价格相当

### 2. 京东独家的价值
- Ultra是京东独家版本，有渠道优势
- Pro在多渠道销售，可能存在价格竞争

### 3. SQD-Mini LED的技术护城河
- 色域100% BT.2020是旗舰标准
- 与QD-Mini LED存在真实技术差距（非营销话术）

---

## 五、UNSURE事项（需主笔注意）

1. **T7M Pro具体排名**：传闻TOP3但搜索结果未直接证实，建议正文表述为"榜单前列"或"热销款"而非绝对排名
2. **芯片型号细节**：TSR AI光色同控芯片的具体架构和性能差异，未找到详细技术文档
3. **实时价格波动**：电商价格频繁变动，正文需注明"调研时价格"或"活动期间价格"
4. **用户评价数据**：Ultra"5000+好评"来自搜索结果，Pro评价数未找到

---

## 六、数据来源清单

- 京东排行榜（85寸LED、电视85、全球平板电视）
- 京东价格行情页面
- 知乎专栏（T7M Pro评测、SQD技术对比）
- IT之家（T7M Pro实拍）
- TCL官方博客（SQD技术解析）
- 搜狐报道（TCL 618累计榜）
- 智度科技（SQD技术解析）
- 新华日报（T7M Pro音响配置）

---

**下一步**：产出拆解卡，明确信息增益点和流量机制闸门。
