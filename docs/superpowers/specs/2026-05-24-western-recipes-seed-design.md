# 西餐食谱种子数据（法/西/意/美）

**日期：** 2026-05-24  
**状态：** 已完成  
**实现计划：** [2026-05-24-western-recipes-seed.md](../plans/2026-05-24-western-recipes-seed.md)

## 目标

扩充食谱库 **240 道** 家庭可做的西餐，覆盖 **法餐、西班牙餐、意餐、美式** 四个独立菜系；扩展 `cuisine` 枚举（移除 `western`）；与现有中/日 seed 并存。

## 已确认决策

| 项 | 选择 |
|---|---|
| 建模 | **E1** — `french` / `spanish` / `italian` / `american` 独立 `cuisine`；**移除 `western`** |
| 总量 | **240 道**（每国 **60**） |
| 每国 type 配额 | **meat 25 / veg 15 / soup 10 / other 10** |
| 导入 | **I2** — 4 条独立命令 |
| 菜名/步骤 | **F1** — L3 `中文（原文）`；`description` 3–6 步编号（中文） |
| Upsert | **U2** — 同名更新 `description` + `ingredients` + `cuisine` |
| AI 配餐 | **不限制**菜系（与现有一致） |
| 架构 | 四国各一 `SeedBundle` + 薄 CLI（方案 1） |

## 非目标

- 德餐、英式、墨西哥餐等（后续可加枚举或归入 `other`）
- `sub_cuisine` 字段
- AI 按菜系偏好
- 封面图、步骤字段独立列
- 单命令一次导入四国（I1/I3）

## 枚举变更

**之前：**

```python
CUISINE_TYPES = {"chinese", "japanese", "korean", "thai", "western", "other"}
```

**之后：**

```python
CUISINE_TYPES = {
    "chinese",
    "japanese",
    "korean",
    "thai",
    "french",
    "spanish",
    "italian",
    "american",
    "other",
}
```

| code | UI 中文 |
|------|---------|
| `french` | 法餐 |
| `spanish` | 西班牙餐 |
| `italian` | 意餐 |
| `american` | 美式 |
| `other` | 其他 |

## Migration

在 `migrate.py` 增加幂等步骤（与现有 `cuisine` 列迁移并列）：

1. `UPDATE recipe SET cuisine = 'other' WHERE cuisine = 'western'`
2. 不尝试将 `western` 自动映射到法/西/意/美（无法可靠推断）

用户手动改过的 `french` 等值若已存在则保留。新 seed 导入由 bundle 写入。

## 数据文件

路径：`backend/data/seeds/`

每国 4 个 JSON，共 **16 个文件**：

| 国家 | 文件前缀 | 条数合计 |
|------|----------|----------|
| 法餐 | `french_recipes_` | 60 |
| 西班牙餐 | `spanish_recipes_` | 60 |
| 意餐 | `italian_recipes_` | 60 |
| 美式 | `american_recipes_` | 60 |

单文件条数：`meat` 25、`veg` 15、`soup` 10、`other` 10。

### 记录示例

```json
{
  "name": "法式洋葱汤（Soupe à l'oignon）",
  "type": "soup",
  "description": "1. 洋葱切细丝，小火炒至深琥珀色。\n2. 倒入牛肉高汤煮开，小火炖 15 分钟。\n3. 面包片烤至酥脆，放入汤碗。\n4. 汤倒入碗中，撒格鲁耶尔芝士，烤箱烤至芝士融化。",
  "ingredients": [
    "洋葱 2个",
    "牛肉高汤 500ml",
    "法棍面包 2片",
    "格鲁耶尔芝士 50g",
    "黄油 20g",
    "盐 适量",
    "黑胡椒 少许"
  ]
}
```

- `type` 与文件名一致；JSON 内可不写 `cuisine`（由 bundle 注入）
- 240 个 `name` **全局唯一**（跨四国不可重名）

## SeedBundle 与导入

在 `recipe_seed.py` 新增四个 bundle（结构同 `CLASSIC_BUNDLE`）：

| 常量 | `default_cuisine` | `update_on_match` |
|------|-------------------|-------------------|
| `FRENCH_BUNDLE` | `french` | `description`, `ingredients`, `cuisine` |
| `SPANISH_BUNDLE` | `spanish` | 同上 |
| `ITALIAN_BUNDLE` | `italian` | 同上 |
| `AMERICAN_BUNDLE` | `american` | 同上 |

薄包装模块：

- `french_recipes_seed.py` → `import_french_recipes`
- `spanish_recipes_seed.py` → `import_spanish_recipes`
- `italian_recipes_seed.py` → `import_italian_recipes`
- `american_recipes_seed.py` → `import_american_recipes`

CLI：

- `backend/scripts/import_french_recipes.py`
- `backend/scripts/import_spanish_recipes.py`
- `backend/scripts/import_italian_recipes.py`
- `backend/scripts/import_american_recipes.py`

Makefile：

```makefile
seed-french-recipes: setup-backend
	cd backend && .venv/bin/python scripts/import_french_recipes.py
# … spanish / italian / american 同理
```

输出格式（与中餐一致）：

```text
已导入 N 条，更新 M 条，跳过 K 条
```

## 前端

- `frontend/src/api.ts`：`CuisineType` 移除 `western`，增加四国
- `locale/zh.ts`：`cuisineLabel` 映射
- `RecipesPage` 筛选下拉更新
- `RecipeFormPage` 菜系下拉更新

## 内容方向（J2 家庭化 + 外食常见简化）

- **法餐：** 洋葱汤、红酒炖牛肉、可丽饼、油封鸭（简化）、尼斯沙拉、法式煎蛋卷…
- **西班牙餐：** 海鲜饭、西班牙土豆蛋饼、蒜香虾、冷汤 Gazpacho、塔帕斯…
- **意餐：** 番茄意面、奶油培根面、千层面、米兰烩饭、玛格丽特披萨（家庭版）…
- **美式：** 汉堡、烤肋排、通心粉奶酪、蛤蜊浓汤、烤鸡、布朗尼…

实现阶段由 Agent 编写具体 240 道菜名与步骤（附录仅列配额，不预列全名）。

## 测试

**新增：**

- `test_import_french_recipes.py` 等（或合并 `test_import_western_recipes.py`）
- 每国 production JSON：60 条、type 计数、L3 格式、≥3 步
- upsert 更新 description/ingredients/cuisine
- `test_recipe_cuisine.py`：`western` 非法；migration `western`→`other`

**回归：**

- 现有中餐/日餐 seed 测试不变
- `pytest` 全量通过

## 验收标准

- [x] `CUISINE_TYPES` 含四国、无 `western`
- [x] 16 个 JSON 合计 240 条，配额正确
- [x] 四条 `make seed-*-recipes` 可导入且 upsert 正常
- [x] 前端可筛选法/西/意/美
- [x] DB 中旧 `western` 已变为 `other`
- [x] README 文档四条命令

## 风险

| 风险 | 缓解 |
|------|------|
| 与中餐/日餐菜名冲突 | 全局唯一检查；L3 原文降低碰撞 |
| 16 文件维护量大 | 分国命令、分国提交 |
| 用户习惯「西餐」筛选 | UI 四国并列；`other` 兜底 |
