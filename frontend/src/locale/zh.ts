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
    cover: "食谱封面",
    uploadCover: "上传封面",
    replaceCover: "更换封面",
    removeCover: "删除封面",
  },
  cooked: {
    sectionPlanned: "计划",
    sectionActual: "实际",
    markDone: "标记已做",
    markWithPhoto: "拍照标记",
    unmark: "取消标记",
    addExtra: "追加实际做的菜",
    planned: "计划内",
    extra: "额外",
    replacePhoto: "换照片",
    removePhoto: "删照片",
  },
  journal: {
    title: "饮食记录",
    empty: "本周还没有饮食记录",
    backToPlan: "返回膳食计划",
  },
  mealPlan: {
    title: "膳食计划",
    recipes: "食谱",
    generateList: "生成购物清单",
    viewList: "查看购物清单",
    autoFill: "AI 自动填充空餐次",
    filling: "填充中…",
    addSlot: "+ 添加",
    mealDetail: "本餐菜单",
    addDish: "添加菜品",
    replaceDish: "更换",
    removeDish: "删除",
    emptyMeal: "尚未安排菜品",
    loadFailed: "加载膳食计划失败",
    aiFillFailed: "AI 填充失败",
    generateListFailed: "生成购物清单失败",
    regenerate: "重新生成计划",
    regenerating: "重新生成中…",
    regenerateConfirm:
      "重新生成本周膳食计划？所有餐次将被 AI 重新安排，该周购物清单将被删除。",
    regenerateFailed: "重新生成计划失败",
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
