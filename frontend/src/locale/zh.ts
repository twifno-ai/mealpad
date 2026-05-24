export const zh = {
  loading: "加载中…",
  save: "保存",
  cancel: "取消",
  close: "关闭",
  delete: "删除",
  back: "返回",
  error: {
    loadFailed: "加载失败",
    saveFailed: "保存失败",
    deleteFailed: "删除失败",
    generic: "操作失败，请重试",
  },
  recipes: {
    title: "食谱",
    new: "+ 新建食谱",
    allTypes: "全部类型",
    mealPlan: "膳食计划",
    empty: "还没有食谱，来添加第一个吧。",
    ingredientsCount: (n: number) => `${n} 项食材`,
    deleteConfirm: (name: string) => `确定删除「${name}」？`,
    filterByType: "按类型筛选",
  },
  recipeForm: {
    newTitle: "新建食谱",
    editTitle: "编辑食谱",
    name: "名称",
    type: "类型",
    description: "描述",
    ingredients: "食材（每行一项）",
  },
  mealPlan: {
    title: "膳食计划",
    recipes: "食谱",
    generateList: "生成购物清单",
    viewList: "查看购物清单",
    autoFill: "AI 自动填充空槽",
    filling: "填充中…",
    addSlot: "+ 添加",
    loadFailed: "加载膳食计划失败",
    aiFillFailed: "AI 填充失败",
    generateListFailed: "生成购物清单失败",
  },
  picker: {
    title: "选择食谱",
    search: "搜索食谱…",
    clearSlot: "清空此餐",
  },
  shopping: {
    title: "购物清单",
    backToPlan: "返回膳食计划",
    empty: "还没有购物清单",
    regenerateConfirm: "重新生成清单？所有勾选状态将重置。",
    regenerateFailed: "重新生成失败",
    regenerating: "重新生成中…",
    regenerate: "重新生成清单",
  },
} as const;

const RECIPE_TYPE_LABELS: Record<string, string> = {
  soup: "汤",
  meat: "荤菜",
  veg: "素菜",
  noodle: "面食",
  rice: "米饭",
  salad: "沙拉",
  other: "其他",
};

const SLOT_LABELS: Record<string, string> = {
  lunch: "午餐",
  dinner: "晚餐",
};

const CATEGORY_LABELS: Record<string, string> = {
  produce: "蔬果",
  meat: "肉类",
  dairy: "乳制品",
  bakery: "烘焙",
  frozen: "冷冻",
  pantry: "干货调料",
  other: "其他",
};

export function recipeTypeLabel(type: string): string {
  return RECIPE_TYPE_LABELS[type] ?? type;
}

export function slotLabel(slot: string): string {
  return SLOT_LABELS[slot] ?? slot;
}

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}
