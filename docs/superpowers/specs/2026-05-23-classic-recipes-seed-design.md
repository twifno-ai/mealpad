# 经典中餐食谱种子数据

**日期：** 2026-05-23  
**状态：** 已完成  
**实现计划：** [2026-05-23-classic-recipes-seed.md](../plans/2026-05-23-classic-recipes-seed.md)

## 目标

为 Mealpad 食谱库一次性扩充 **240 道** 全国家常经典中餐，使 AI 填充每餐、手动选菜时有足够候选（尤其 `meat`、`veg`、`soup` 三类）。

内容在实现阶段由 **Cursor Agent 编写**（非运行时 Claude/OpenAI API），经 **一次性手动脚本** 写入现有 SQLite 数据库，**在已有食谱基础上追加**。

## 已确认决策

| 项 | 选择 |
|---|---|
| 内容来源 | Cursor Agent 生成 JSON 数据 |
| 写入方式 | 一次性 Python 导入脚本，手动执行 |
| 触发时机 | **不**绑定 server 启动 / lifespan |
| 去重 | **按 `name` 去重** — 与 DB 已有或本批已导入同名则跳过，不覆盖 |
| 与现有库 | **追加**（非「库为空才导入」） |
| 总量 | **240 道**（≥200 要求） |
| 类型配额 | **meat 100 / veg 60 / soup 40 / other 40** |
| 风格 | **R1 全国家常** — 南北混合、家庭日常（番茄炒蛋、红烧肉、冬瓜排骨汤等） |
| 数据形态 | 4 个 JSON 按类型拆分 + 统一导入脚本 |
| 封面图 | 无（v1 种子不含图片） |

## 非目标

- 启动时自动 seed、`init_db()` 钩子
- 同名 merge / 更新已有食谱字段
- 重复执行保护（锁文件等）
- 运行时 AI 批量生成
- 烹饪步骤、营养信息、URL 导入
- 前端「导入食谱」按钮
- 修改 `Recipe` 表结构

## 数据文件

路径：`backend/data/seeds/`

| 文件 | 类型 | 条数 |
|---|---|---|
| `classic_recipes_meat.json` | `meat` | 100 |
| `classic_recipes_veg.json` | `veg` | 60 |
| `classic_recipes_soup.json` | `soup` | 40 |
| `classic_recipes_other.json` | `other` | 40 |

每条记录对齐 `RecipeCreate` / `Recipe` 模型：

```json
{
  "name": "番茄炒蛋",
  "type": "meat",
  "description": "家常下饭菜，酸甜适口。",
  "ingredients": ["鸡蛋 3 个", "番茄 2 个", "盐 适量", "糖 少许", "葱花 少许"]
}
```

**字段规则：**

- `name`：非空，中文菜名；240 条内互不重复
- `type`：必须与文件名一致（`meat` / `veg` / `soup` / `other`）
- `description`：可选，1 句家常说明；可为空字符串
- `ingredients`：非空数组；每项为 **中文自由文本** 一行（含量词/「适量」），与现有 UI 及购物清单合并逻辑一致

**内容质量（Agent 生成时）：**

- 南北家常混合，避免仅某一地域或仅饭店大菜
- 每道菜 4–10 条常见食材，家庭可采购
- `other` 含主食、小吃、简餐（蛋炒饭、葱油拌面、蒸水蛋等），不含纯饮料

## 导入脚本

**路径：** `backend/scripts/import_classic_recipes.py`

**行为：**

1. 读取 `backend/app/config.py` 中 `settings.db_path`（默认 `backend/data/mealpad.db`）
2. 启动时查询 DB 中全部 `Recipe.name`，放入集合 `seen_names`（精确字符串匹配，不 trim、不大小写转换）
3. 依次加载 `backend/data/seeds/classic_recipes_*.json`（文件名排序：`meat` → `veg` → `soup` → `other`）
4. 校验每条：`type` 合法、字段完整、`ingredients` 非空
5. **去重：** 若 `name` 已在 `seen_names` 中 → **跳过**，计入 `skipped`；否则 `session.add(Recipe(...))` 并将 `name` 加入 `seen_names`
6. 单次 `commit`
7. stdout 打印汇总，例如：`已导入 238 条，跳过 2 条（同名已存在）`

**去重规则：**

- **与 DB 去重：** 库中已有同名食谱则不插入
- **批内去重：** 多个 seed 文件或同一文件内出现同名 → 仅 **先遇到的** 一条入库，其余跳过
- **不覆盖：** 跳过时不更新已有行的 `description`、`ingredients`、`type`

**不做：** HTTP 调 API、事务外逐条 commit、模糊匹配菜名。

**Makefile 目标（可选但推荐）：**

```makefile
seed-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_classic_recipes.py
```

**运行说明（写入 README 一句）：**

> 扩充食谱库时执行 `make seed-recipes`；同名食谱会自动跳过，可安全重复执行。

## 测试

**文件：** `backend/tests/test_import_classic_recipes.py`

1. **JSON 结构：** 四个 seed 文件存在；解析后条数分别为 100/60/40/40；每条 `type` 与文件一致
2. **导入集成：** 对空测试库执行脚本，断言新增 240 行，按 `type` 计数正确
3. **去重 — DB 已有：** 预置同名 `Recipe` 后导入，断言跳过且不覆盖原记录
4. **去重 — 批内重复：** seed 含两条同名时，仅导入一条
5. **幂等：** 同一测试库连续跑两次，第二次 `imported=0`、`skipped=240`
6. **校验失败：** 缺字段或非法 `type` 时脚本非零退出（可用夹具小 JSON 或 monkeypatch）

不测试 UI；手动验证：备份 `backend/data/` 后跑一次，食谱列表页可见新条目。

## 实现顺序（概要）

1. 添加空目录结构与导入脚本骨架 + Makefile 目标
2. Agent 分 4 批编写 JSON（每批完成后校验条数与 `type`）
3. 补充 pytest
4. 文档：本 spec 状态更新 + README 一句

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 误重复执行 | 按名跳过；脚本输出 imported / skipped 计数 |
| 单文件过大难 review | 按类型拆 4 文件 |
| Agent 生成菜名重复 | 实现阶段维护已用名称清单，分批生成时交叉检查 |
| JSON 与模型漂移 | pytest 校验 schema + 与 `RECIPE_TYPES` 一致 |

## 验收标准

- [ ] 四个 JSON 合计 240 条，配额准确
- [ ] `make seed-recipes` 在现有 DB 上追加且同名跳过
- [ ] 重复执行不产生重复菜名
- [ ] `cd backend && pytest` 含新测试且通过
- [ ] 无修改 `main.py` lifespan / 无自动 seed
- [ ] JSON 进 git；`mealpad.db` 仍 gitignore
