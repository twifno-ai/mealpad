# 中餐 seed 制作步骤与 upsert 导入

**日期：** 2026-05-24  
**状态：** 已完成  
**实现计划：** [2026-05-24-classic-recipes-steps.md](../plans/2026-05-24-classic-recipes-steps.md)  
**关联：** [2026-05-23-classic-recipes-seed-design.md](./2026-05-23-classic-recipes-seed-design.md)

## 目标

1. 将现有 **240 道** 中餐 seed JSON 的 `description` 升级为 **3–6 步编号制作步骤**（与日餐 S1 格式一致，菜名仍为纯中文）。
2. 扩展 `make seed-recipes`：**默认 upsert** — 同名已存在则更新 `description` + `ingredients`，否则插入。

## 已确认决策

| 项 | 选择 |
|---|---|
| 数据范围 | 4 个 `classic_recipes_*.json`，240 道，配额不变 |
| 步骤格式 | **S1** — 仅编号步骤，`1. ` 起头，`\n` 分隔，3–6 步 |
| Upsert 字段 | **F2** — `description` + `ingredients` |
| 触发 | **T1** — `make seed-recipes` 默认 upsert |
| 不改 | `type`、`name`、封面图、recipe id |
| 日餐 | `make seed-japanese-recipes` **仍 skip**，不 upsert |
| 架构 | **SeedBundle.update_on_match** 配置（方案 1） |

## 导入行为

| 情况 | CLASSIC（中餐） | JAPANESE（日餐） |
|------|-----------------|------------------|
| 无同名 | INSERT → `imported++` | INSERT → `imported++` |
| 有同名 | UPDATE desc+ingredients → `updated++` | SKIP → `skipped++` |

CLI 输出示例：

```text
已导入 0 条，更新 240 条，跳过 0 条
```

## 数据示例

```json
{
  "name": "番茄炒蛋",
  "type": "meat",
  "description": "1. 鸡蛋打散，番茄切块。\n2. 热锅油，先炒蛋至半凝固盛出。\n3. 炒番茄出汁，倒回鸡蛋，加盐、糖炒匀。\n4. 撒葱花出锅。",
  "ingredients": ["鸡蛋 3个", "番茄 2个", "盐 适量", "糖 少许", "葱花 少许", "食用油 适量"]
}
```

## 非目标

- 修改 `Recipe` 表结构
- upsert `type` 或删除/重建记录
- 日餐 seed 行为变更
- 前端改动

## 测试

- upsert 更新 description/ingredients，type 不变
- 新名仍 insert
- 日餐仍 skip（updated=0）
- 240 条生产 JSON 每道 ≥3 编号步骤

## 验收

- [ ] 四个 classic JSON 含步骤描述
- [ ] `make seed-recipes` 对已有 240 道输出 updated=240（或 imported+updated 合计覆盖）
- [ ] pytest 全过
- [ ] README 说明 upsert 行为

## 风险

| 风险 | 缓解 |
|------|------|
| 覆盖用户手改过的 description | README 说明；仅 seed 同名条目受影响 |
| 240 道重写工作量大 | Agent 分批生成 JSON |
