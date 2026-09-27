# RainGaugeNet — 2008 汶川地震后泥石流多时相数据集复现

> 想先看复现过程而不是结果? 全程记录在这里:
> [`docs/repro_log.md`](docs/repro_log.md) (Blog 风格, 中文, 直白)

对数据论文 **Wang, L., Chang, M., Le, J., Xiang, L. & Ni, Z. (2022).**
*Two multi-temporal datasets to track debris flow after the 2008 Wenchuan earthquake.*
**Scientific Data 9:525**，[doi:10.1038/s41597-022-01658-y](https://doi.org/10.1038/s41597-022-01658-y)
的**流程复现**：从 Zenodo 原始数据出发，跑通「读取 → 清洗 → 特征工程 → 传统机器学习分类 → 与经验 I-D 阈值比较 → 出图出表」的完整链路。

数据 DOI：[10.5281/zenodo.6891244](https://doi.org/10.5281/zenodo.6891244)

> **论文本身是 Data Descriptor（数据论文），不含降雨阈值或易发性建模。**
> 本仓库做的是"用论文发布的数据完成它建议的应用"（原文 Abstract：
> *"can aid different applications, including the early warning and engineering prevention
> of post-earthquake debris flow"*），因此下面所有模型结果都是**本仓库的实验结论**，
> 不是对原文数值的复刻。原文提供的可核验对象只有两套数据本身（事件、降雨、坝体）。

---

## 1. 快速开始（一键复现）

```powershell
# 1. 建环境（CPU 即可，无需 GPU / 深度学习）
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. 一键复现：raw -> interim -> processed -> models -> figures -> 校验
.\.venv\Scripts\python.exe run_all.py
```

`run_all.py` 依次执行 5 个阶段并最后做**逐字节复现校验**：

| 阶段 | 脚本 | 输入 → 输出 |
|---|---|---|
| 1 | `scripts/build_interim.py` | `data/raw/` → `data/interim/*.csv`、`data/processed/rain_events_raw.csv` |
| 2 | `scripts/build_catchment_features.py` | interim → `data/processed/catchment_features.csv` |
| 3 | `scripts/run_models.py` | → `results/metrics_summary.csv`、`results/task_a_*.json`、`results/task_b_*.json` |
| 4 | `scripts/make_figures.py` | → `results/figures/*.png` |
| 5 | `scripts/verify_results.py` | 对 `results/repro_manifest.json` 里的 SHA-256 逐个校验 |

常用开关：

```powershell
python run_all.py --no-verify          # 首次跑 / 改过方法学后跳过校验
python run_all.py --update-manifest    # 有意变更后重新记录指纹
python scripts/verify_results.py       # 单独校验
```

**固定随机种子**：`SEED = 20220901`（`scripts/run_models.py`）与 `SPLIT_SEED = 20220901`
（`src/wenchuan/models.py`），所有划分与所有 estimator 的 `random_state` 都由它派生。
同一份原始数据重跑，`data/` 与 `results/` 下的 CSV/JSON **逐字节一致**（阶段 5 强制检查）。

**已实测验证**：连续两次运行 `run_all.py`，第二次带完整校验，16 个产物全部通过 SHA-256 比对，
输出 `OK: every artefact reproduces bit-for-bit.`（日志见 `results/run_all_stdout.txt`、
`results/repro_run2.log`）。单次全流程约 **52–63 秒**（Windows 11，CPU）。

---

## 2. 目录结构

```
RainGaugeNet/
├─ run_all.py                     # 一键复现入口
├─ requirements.txt
├─ README.md
├─ data/
│  ├─ raw/                        # 原始数据（见 §3），只读
│  ├─ interim/                    # 清洗后的三张基础表
│  └─ processed/                  # 建模用的两张宽表
├─ src/wenchuan/                  # 可复用库（无脚本副作用）
│  ├─ io.py                       # 原始 CSV / 降雨 txt / dbf 读取
│  ├─ dbf.py                      # 手写 DBF 读取器（不依赖 geopandas）
│  ├─ geometry.py                 # 手写 SHP 读取器 + 多边形面积/质心
│  ├─ clean.py                    # 清洗 + 事件↔流域名称对齐
│  ├─ features.py                 # 降雨场次切分与 16 个降雨特征
│  ├─ catchment_assign.py         # 事件→流域的空间归属（名称优先，几何兜底）
│  ├─ catchment_geom.py           # 流域形态特征 + UTM→WGS84 反投影
│  ├─ dataset.py                  # 组装 Task A / Task B 两张建模表
│  ├─ models.py                   # 4+1 个传统分类器 + 统一评分
│  └─ threshold.py                # I-D 阈值拟合与评估
├─ scripts/                       # 5 个流程阶段 + explore/ 下的探索脚本
├─ results/                       # 结果 CSV/JSON/PNG + 复现指纹
└─ docs/                          # 论文全文、Read me、报告
```

---

## 3. 数据来源与放置

原始数据**不随仓库分发**，需自行从 Zenodo 下载后放到 `data/raw/`：

```
data/raw/
├─ dataset1/Dataset1 Debris flow and Triggering rain/
│  ├─ Dataset1_Debris flow.csv              # 186 条泥石流事件
│  ├─ Debris_flow_catchment.{shp,dbf,prj}   # 79 个流域多边形
│  └─ ID_RG_DF_DATA/ID_RG_DF_<DF_ID>/*.txt  # 465 个逐小时降雨序列
├─ dataset2/Dataset2 Dam/Dataset2_Dam.csv   # 工程防治（拦砂坝）
├─ Read me.pdf                              # 官方字段说明
└─ References of data sources.pdf           # 逐条数据出处
```

`docs/raw/` 放论文全文（PMC9420130）与从 PDF 提取的字段说明文本，供字段核对使用。

**字段（来自官方 Read me）**

| 文件 | 关键字段 |
|---|---|
| `Dataset1_Debris flow.csv` | `DF_ID`, `Gully name`, `Latitude`, `Longitude`, `Year/Month/Day`, `Time(24 hour)`, `Deposition volume (m3)`, `Reference of Data source` |
| 流域多边形 | `Name`, `CID`, `County`, `Area` |
| `ID_RG_DF_*/**.txt` | 文件名 `<seq>_<rg_id>_<YYYYMMDDHH>`；内容两列：`YYYYMMDDHH` + 降雨量(mm) |
| `Dataset2_Dam.csv` | `Name`, `C_ID`, `Dam number`, `Built Time`, `Successful prevention and control` |

---

## 4. 数据清洗：三个必须记录的坑

这三条是复现过程中实际踩到并处理的，**都会改变结论**，因此写进正文而不是附录。

### 4.1 事件表的两列坐标是反的
`Dataset1_Debris flow.csv` 里名为 `Latitude` 的列装的是 103.x（**经度**），名为 `Longitude`
的列装的是 31.x（**纬度**）—— 龙门山震中区不可能有纬度 103°。
`io.load_events()` 因此把两列重命名为真值 `lon` / `lat`，原始列另存为 `Latitude_raw` /
`Longitude_raw` 保留可追溯性。**若不做这步，所有空间归属都会落到地球另一侧。**

### 4.2 95/186 条事件没有时刻
`Time(24 hour)` 为 `-`。这些事件的 `datetime` 用当天 00:00 兜底，并置 `time_missing=True`；
降雨触发判定因此以**整个日历日**为窗口（`features.label_triggers`），而不是拿 12:00 当精确时刻。

### 4.3 事件名与流域名是两种写法
事件表存单个沟名（如 `Mayangdian`），流域表存 `/` 连接的多沟名
（如 `Douyaping/Mayangdian/Maliuwan/Qingling/Guanshan` → `W16`）。
`clean.build_catchment_lookup()` 把流域名拆成子名建索引，再做最长匹配兜底；
仍有少量事件无法用名称匹配时，`catchment_assign.py` 用**点-多边形空间关系**兜底，
并记录 `catchment_source ∈ {name, geometry, unassigned}` 以便核查。

---

## 5. 特征工程

### 5.1 降雨场次切分（`features.py`）
每个 `ID_RG_DF_<DF_ID>/` 文件夹是「该事件 8 km 内的所有雨量站」在
**事件前 7 天 → 事件后 1 天**窗口内的逐小时序列。窗口内远不止一场雨，因此它也天然提供了
**非触发场次**作为监督学习的负样本 —— 不需要合成负样本。

一场"雨"的定义（可调常量集中在 `features.py` 顶部）：

| 常量 | 值 | 含义 |
|---|---|---|
| `WET_MM` | 0.1 | 小时雨量 ≥ 该值算"湿小时" |
| `DRY_GAP_H` | 6 | 连续干小时 > 6 h 才切成两场 |
| `MIN_TOTAL_MM` | 1.0 | 场次总雨量 < 1 mm 丢弃 |
| `API_K` | 0.9 | 前期降水指数的小时衰减系数 |

### 5.2 16 个降雨特征（`dataset.RAIN_FEATURES`）
`duration_h`, `n_wet_hours`, `total_mm`, `max_1h/3h/6h/12h/24h/48h/72h`,
`mean_intensity`, `peak_intensity`, `antecedent_24h/72h/168h`, `api`

### 5.3 流域特征（`dataset.CATCHMENT_FEATURES`）
形态类：`area_km2`, `poly_perimeter_km`, `compactness = 4πA/P²`, `bbox_width_km`,
`bbox_height_km`, `bbox_aspect`, `centroid_lon`, `centroid_lat`, `n_gullies`
防治类：`dam_number`, `has_dam`, `built_year`, `has_built_year`

> **不造数据**：数据集不含 DEM，因此**不虚构坡度/高程特征**（`catchment_geom.py` 顶部明确写了这一点）。
> 多边形面积同时用鞋带公式独立算了一遍，与 `.dbf` 的 `Area` 属性做交叉校验
> （`area_check_rel_err`，见 `data/processed/catchment_features.csv`）。

---

## 6. 两个分类任务与评测协议

### Task A — 降雨阈值（rainstorm 级二分类）
- **样本**：一行 = 一个（雨量站文件, 雨场）。正样本 = 与泥石流当日重叠的雨场，负样本 = 同一窗口内其它雨场。
- **规模**：**1597 行 / 444 正样本 / 1153 负样本（正例率 27.8%）**，覆盖 146 个事件文件夹、
  39 个雨量站（见 `results/task_a_rainfall_threshold.json`）。
- **关键问题：行与行不独立。** 一次泥石流事件贡献多个雨量站文件，它的触发雨场在多个站上被重复计入。
  随机划分会把同一场雨同时放进训练和测试 → **泄漏**。
- 因此**同时报告三种协议**，用来量化泄漏带来的乐观偏差：

| 协议 | 划分方式 | 作用 |
|---|---|---|
| `random` | 分层随机 7:3 | 有泄漏，**只作为乐观上界**，不作为结论 |
| `group_event` | `GroupKFold`，以 `DF_ID` 分组 | **主协议**，同一次事件不跨折 |
| `temporal` | 训练 ≤2013，测试 ≥2016 | 检验跨期泛化（阈值随震后恢复应下降） |

- **经验 I-D 阈值对照**：`I = a·D^(−b)`。`threshold.py` 里记录了为什么
  **必须用固定时间窗**而不是"湿 spell 长度"来构造 (D, I)：
  湿 spell 中位数 20 h、最长 82 h（6 h 干间隔把连续季风降雨合并了），
  得到的 log-log 散点 Pearson r 只有 **0.274**，OLS 斜率被少数超长历时样本主导，
  **不能刻画物理包络**；改用"任意 D 小时窗口内的最大雨量 / D"后，每个雨场贡献 7 个点
  （窗长 1/3/6/12/24/48/72 h，共 **11179** 个 (D, I) 对），点云才呈现经典幂律形态。
  共拟合 6 条曲线（OLS 全点 / OLS 仅触发点 / OLS 下移 1σ / 触发点 P50 / P90 / 全点 P90），
  全部在**同一批行、同一批标签**上与 ML 模型同口径评分。
  关键发现：**原始点云的 OLS r² 只有 0.35–0.49**，而"先按窗长取分位数再拟合"的 r² 达
  **0.96–0.99**——幂律只在分位数包络上成立，报告里两类结果并列给出。
- **ML 等效阈值曲线：诊断失败，如实记录。** `threshold.fit_ml_equivalent_threshold()`
  试图从随机森林的 0.5 概率等高线反推一条 I-D 曲线，但合成样本只有 1 个特征被赋值、
  其余 15 个填 0，概率曲线不单调，返回空字典 `{}`。报告 §6.4 记录了这一失败，
  没有换参数把它"调出"一条好看的曲线。

### Task B — 流域易发性（catchment 级二分类）
- **样本**：79 个流域，一行一个。
- **标签**：`susceptible = (n_events > median(n_events))`。
- **防泄漏**：显式排除事件派生列（`n_events`, `first_event`, `last_event`,
  `total_volume_m3`, `event_span_years`），只留形态 + 防治特征。
- **评测**：`RepeatedStratifiedKFold(5 折 × 10 次重复)` 报均值/标准差，
  另出 5 折 OOF 混淆矩阵。

### 模型（`models.py`，全部传统方法，无深度网络）
逻辑回归（中位数插补 + 标准化 + `class_weight="balanced"`）、随机森林（500 棵）、
RBF-SVM、梯度提升、XGBoost（可选，未安装则自动跳过，结果表中相应行消失）。

---

## 7. 结果文件

| 文件 | 内容 |
|---|---|
| `results/metrics_summary.csv` | 全部模型的 accuracy / precision / recall / F1 / ROC-AUC / 混淆矩阵 |
| `results/task_a_rainfall_threshold.json` | Task A 完整结果：三协议逐模型指标、6 条 I-D 曲线、ML 等效阈值、特征重要性、逐年触发雨量 |
| `results/task_b_susceptibility.json` | Task B 完整结果：CV 均值/标准差、OOF 指标、特征重要性、79 个流域的逐行明细 |
| `results/figures/fig01..07*.png` | 7 张图 |
| `results/repro_manifest.json` | 16 个产物的 SHA-256 指纹 |
| `results/run_all_stdout.txt` | 一键复现的完整控制台日志 |
| `results/repro_run2.log` | 第二次全流程 + 逐字节复现校验日志 |
| `docs/report.md` / `docs/report.pdf` | 实验报告 |
| `docs/_numbers.md` | 报告引用数字的自动汇总（`scripts/explore/report_numbers.py` 可重算） |

**所有图里的数字都能在 CSV/JSON 里查到**，报告不依赖读图。

---

## 8. 复现环境

实测环境：Windows 11 x64，Python 3.12.10，pandas 3.0.6 / numpy 2.5.3 /
scikit-learn 1.9.1 / matplotlib 3.11.2 / seaborn 0.13.2 / xgboost 3.4.1。CPU 即可。

`src/wenchuan/geometry.py` 与 `dbf.py` 是手写的 SHP/DBF 读取器，
**刻意不依赖 geopandas / GDAL / fiona**，避免复现时卡在二进制依赖上。

生成 `docs/report.pdf` 额外需要 `pandoc` + 一个无头 Chromium/Edge（仅报告环节需要，
不影响数据与模型流程）。

---

## 9. 引用与来源声明

- **数据与论文**：Wang L., Chang M., Le J., Xiang L., Ni Z. (2022).
  *Two multi-temporal datasets to track debris flow after the 2008 Wenchuan earthquake.*
  Scientific Data 9:525. doi:10.1038/s41597-022-01658-y；数据 doi:10.5281/zenodo.6891244
  （CC BY 4.0）。数据集本身基于 Fan et al. (2019) 更新而来。
- **I-D 阈值形式**：`I = a·D^(−b)`，源自 Caine (1980) 的经典幂律形式（经由本领域通行做法沿用）。
- **本仓库代码**：全部为本仓库自行编写，未复制外部开源实现。
  借鉴的是方法学惯例（固定窗口最大雨量构造 I-D 对、`GroupKFold` 防事件级泄漏、
  以中位数切分易发性标签），具体实现与参数均在上文和代码注释中标明。
- **阈值数值的可核验性声明**：仓库中所有阈值系数**均由本次数据自行拟合得到**。
  与文献（如 Guzzetti 2008、Tang 2012、Guo 2016、Jiang 2021 等）的对比，
  仅在报告"讨论"一节作为**定性参照**出现；凡未取得全文核验的文献系数，
  一律不作为定量基线使用。

## 10. 许可

代码：本仓库作者保留。数据：遵循 Zenodo 上原数据集许可（CC BY 4.0），
使用时请引用上述论文与数据 DOI。