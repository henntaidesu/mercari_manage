<template>
  <div>
    <el-card shadow="never" class="warehouse-list-card">
      <template #header>
        <div class="list-card-header">
          <div class="list-card-header-start">
            <span class="list-card-title">仓库列表</span>
            <div class="header-overview-grid">
              <div class="header-overview-item">
                <div class="header-overview-value">{{ mergedWarehouse.shelf_count }}</div>
                <div class="header-overview-label">货架数量</div>
              </div>
              <div class="header-overview-item">
                <div class="header-overview-value">{{ mergedWarehouse.product_types }}</div>
                <div class="header-overview-label">商品种类</div>
              </div>
              <div class="header-overview-item">
                <div class="header-overview-value">{{ mergedWarehouse.total_quantity }}</div>
                <div class="header-overview-label">总库存量</div>
              </div>
            </div>
          </div>
          <el-tooltip content="新建仓库" placement="top">
            <el-button type="primary" class="add-warehouse-btn" @click="openWarehouseDialog">
              <el-icon><Plus /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </template>
      <el-collapse v-if="groupedByWarehouse.length" v-model="activeCollapse" class="warehouse-collapse">
        <el-collapse-item
          v-for="grp in groupedByWarehouse"
          :key="grp.warehouse"
          :name="grp.warehouse"
        >
          <template #title>
            <div class="collapse-title">
              <div class="collapse-title-start">
                <span class="collapse-wh-name" :title="grp.warehouse">{{ grp.warehouse }}</span>
              </div>
              <div class="collapse-title-stats">
                <div class="collapse-stat-grid collapse-stat-grid--primary">
                  <div class="collapse-stat-item">
                    <div class="collapse-stat-value">{{ grp.shelfNameGroups.length }}</div>
                    <div class="collapse-stat-label">名称分组</div>
                  </div>
                  <div class="collapse-stat-item">
                    <div class="collapse-stat-value">{{ grp.shelfCount }}</div>
                    <div class="collapse-stat-label">货架号</div>
                  </div>
                  <div class="collapse-stat-item">
                    <div class="collapse-stat-value">{{ grp.productTypes }}</div>
                    <div class="collapse-stat-label">商品种类</div>
                  </div>
                  <div class="collapse-stat-item">
                    <div class="collapse-stat-value">{{ grp.totalQuantity }}</div>
                    <div class="collapse-stat-label">总库存</div>
                  </div>
                </div>
              </div>
              <div class="collapse-title-end">
                <el-button
                  type="primary"
                  size="small"
                  class="collapse-add-btn"
                  @click.stop="openDialogForWarehouse(grp.warehouse)"
                >
                  <el-icon><Plus /></el-icon>
                  添加货架
                </el-button>
              </div>
            </div>
          </template>
          <el-collapse
            v-model="activeShelfNameByWh[grp.warehouse]"
            class="shelf-name-collapse"
          >
            <el-collapse-item
              v-for="sub in grp.shelfNameGroups"
              :key="`${grp.warehouse}::${sub.key}`"
              :name="sub.key"
            >
              <template #title>
                <div class="shelf-name-title-row">
                  <div class="shelf-name-title-start">
                    <span class="shelf-name-title-text" :title="sub.label">{{ sub.label }}</span>
                  </div>
                  <div class="shelf-name-title-stats">
                    <div class="collapse-stat-grid collapse-stat-grid--secondary">
                      <div class="collapse-stat-item collapse-stat-item--compact">
                        <div class="collapse-stat-value">{{ sub.shelfCount }}</div>
                        <div class="collapse-stat-label">货架号</div>
                      </div>
                      <div class="collapse-stat-item collapse-stat-item--compact">
                        <div class="collapse-stat-value">{{ sub.productTypes }}</div>
                        <div class="collapse-stat-label">商品种类</div>
                      </div>
                      <div class="collapse-stat-item collapse-stat-item--compact">
                        <div class="collapse-stat-value">{{ sub.totalQuantity }}</div>
                        <div class="collapse-stat-label">总库存</div>
                      </div>
                    </div>
                  </div>
                  <div class="shelf-name-title-end">
                    <el-button
                      type="primary"
                      size="small"
                      class="collapse-add-btn"
                      @click.stop="openDialogForShelfGroup(grp.warehouse, sub.rawShelfName)"
                    >
                      <el-icon><Plus /></el-icon>
                      添加货架号
                    </el-button>
                  </div>
                </div>
              </template>
              <el-table :data="sub.shelves" border stripe size="small" class="shelf-subtable shelf-no-table">
                <el-table-column label="货架号" prop="name" min-width="120" />
                <el-table-column label="位置" prop="location" min-width="130" />
                <el-table-column label="描述" prop="description" min-width="160" show-overflow-tooltip />
                <el-table-column label="商品种类" prop="product_types" width="100" align="center" />
                <el-table-column label="总库存量" prop="total_quantity" width="100" align="center" />
                <el-table-column label="操作" width="170" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" @click="openDialog(row)">编辑</el-button>
                    <el-popconfirm title="确认删除该货架？" @confirm="remove(row.id)">
                      <template #reference>
                        <el-button size="small" type="danger">删除</el-button>
                      </template>
                    </el-popconfirm>
                  </template>
                </el-table-column>
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </el-collapse-item>
      </el-collapse>
      <el-empty v-else description="暂无货架数据" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑货架' : addDialogTitle" width="440px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="仓库" prop="warehouse">
          <el-input v-model="form.warehouse" placeholder="请输入仓库名称（如 1号仓）" />
        </el-form-item>
        <el-form-item label="货架名称">
          <el-input v-model="form.shelf_name" placeholder="可选，如：一层左、展示名" clearable />
        </el-form-item>
        <el-form-item v-if="form.id" label="货架号" prop="name">
          <el-input v-model="form.name" placeholder="请输入货架号" clearable />
        </el-form-item>
        <el-form-item v-else label="货架号" prop="name">
          <el-input v-model="form.name" placeholder="请输入货架号" clearable />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="form.location" placeholder="如：1号仓库1排左侧" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="warehouseDialogVisible" title="新建仓库" width="420px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="仓库名称" required>
          <el-input v-model="newWarehouseName" placeholder="请输入仓库名称（如 2号仓）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="warehouseDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCreateWarehouse">下一步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { warehouseApi } from '@/api/index.js'

const DEFAULT_WAREHOUSE = '默认仓库'

function normalizeWarehouseName(w) {
  if (w == null || (typeof w === 'string' && !w.trim())) return DEFAULT_WAREHOUSE
  return String(w).trim()
}

const EMPTY_SHELF_NAME_KEY = '__shelf_name_empty__'

/** 三级结构：在同一仓库下按 shelf_name 分组成二级，每组内为货架号（行） */
function buildShelfNameGroups(shelves) {
  const m = new Map()
  for (const row of shelves) {
    const raw = row.shelf_name && String(row.shelf_name).trim() ? String(row.shelf_name).trim() : ''
    const key = raw || EMPTY_SHELF_NAME_KEY
    if (!m.has(key)) {
      m.set(key, {
        key,
        rawShelfName: raw,
        label: raw || '（未设置货架名称）',
        shelves: []
      })
    }
    m.get(key).shelves.push(row)
  }
  const list = [...m.values()].map((g) => {
    const productTypes = g.shelves.reduce((s, i) => s + Number(i.product_types || 0), 0)
    const totalQuantity = g.shelves.reduce((s, i) => s + Number(i.total_quantity || 0), 0)
    return {
      ...g,
      shelfCount: g.shelves.length,
      productTypes,
      totalQuantity
    }
  })
  list.sort((a, b) => {
    if (a.key === EMPTY_SHELF_NAME_KEY) return 1
    if (b.key === EMPTY_SHELF_NAME_KEY) return -1
    return (a.rawShelfName || '').localeCompare(b.rawShelfName || '', 'zh-CN')
  })
  return list
}

const list = ref([])
const activeCollapse = ref([])
/** 二级折叠（货架名称）每组展开的 name，按仓库分 key */
const activeShelfNameByWh = ref({})
const dialogVisible = ref(false)
const warehouseDialogVisible = ref(false)
const newWarehouseName = ref('')
const submitting = ref(false)
const formRef = ref()
const form = ref({
  id: null,
  warehouse: '默认仓库',
  shelf_name: '',
  name: '',
  location: '',
  description: ''
})
/** 新建弹窗标题：仓库表头 → 添加货架；三级（货架名称行）→ 添加货架号 */
const createDialogKind = ref('shelf')
const addDialogTitle = computed(() =>
  createDialogKind.value === 'shelfNo' ? '添加货架号' : '添加货架'
)

const rules = {
  warehouse: [{ required: true, message: '请输入仓库名称', trigger: 'blur' }],
  name: [{ required: true, message: '请输入货架号', trigger: 'blur' }],
}

/** 一级：仓库 → 二级：货架名称分组 → 三级：货架号表格 */
const groupedByWarehouse = computed(() => {
  const rows = list.value
  const map = new Map()
  for (const row of rows) {
    const key = normalizeWarehouseName(row.warehouse)
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(row)
  }
  const names = [...map.keys()].sort((a, b) => {
    if (a === DEFAULT_WAREHOUSE) return -1
    if (b === DEFAULT_WAREHOUSE) return 1
    return a.localeCompare(b, 'zh-CN')
  })
  return names.map((name) => {
    const shelves = map.get(name)
    const shelfNameGroups = buildShelfNameGroups(shelves)
    const productTypes = shelves.reduce((s, i) => s + Number(i.product_types || 0), 0)
    const totalQuantity = shelves.reduce((s, i) => s + Number(i.total_quantity || 0), 0)
    return {
      warehouse: name,
      shelves,
      shelfNameGroups,
      shelfCount: shelves.length,
      productTypes,
      totalQuantity,
    }
  })
})

watch(
  groupedByWarehouse,
  (groups) => {
    activeCollapse.value = groups.map((g) => g.warehouse)
    const o = {}
    for (const g of groups) {
      o[g.warehouse] = g.shelfNameGroups.map((s) => s.key)
    }
    activeShelfNameByWh.value = o
  },
  { immediate: true },
)

const mergedWarehouse = computed(() => {
  const productTypes = list.value.reduce((sum, item) => sum + Number(item.product_types || 0), 0)
  const totalQuantity = list.value.reduce((sum, item) => sum + Number(item.total_quantity || 0), 0)
  return {
    shelf_count: list.value.length,
    product_types: productTypes,
    total_quantity: totalQuantity
  }
})

async function load() {
  const rows = await warehouseApi.list()
  list.value = rows.map((item) => ({ ...item, warehouse: normalizeWarehouseName(item.warehouse) }))
}

function openDialog(row = null) {
  if (row) {
    form.value = { ...row, warehouse: normalizeWarehouseName(row.warehouse), shelf_name: row.shelf_name || '' }
  } else {
    createDialogKind.value = 'shelf'
    form.value = {
      id: null,
      warehouse: DEFAULT_WAREHOUSE,
      shelf_name: '',
      name: '',
      location: '',
      description: ''
    }
  }
  dialogVisible.value = true
}

/** 在仓库表头添加货架（预填仓库） */
function openDialogForWarehouse(warehouseName) {
  createDialogKind.value = 'shelf'
  form.value = {
    id: null,
    warehouse: normalizeWarehouseName(warehouseName),
    shelf_name: '',
    name: '',
    location: '',
    description: '',
  }
  dialogVisible.value = true
}

/** 在三级列表添加货架号（预填仓库 + 货架名称） */
function openDialogForShelfGroup(warehouseName, rawShelfName) {
  createDialogKind.value = 'shelfNo'
  form.value = {
    id: null,
    warehouse: normalizeWarehouseName(warehouseName),
    shelf_name: rawShelfName ? String(rawShelfName).trim() : '',
    name: '',
    location: '',
    description: '',
  }
  dialogVisible.value = true
}

function openWarehouseDialog() {
  newWarehouseName.value = ''
  warehouseDialogVisible.value = true
}

function confirmCreateWarehouse() {
  const name = (newWarehouseName.value || '').trim()
  if (!name) {
    ElMessage.warning('请输入仓库名称')
    return
  }
  warehouseDialogVisible.value = false
  openDialogForWarehouse(name)
  ElMessage.success('已创建仓库名，请继续新增该仓库下的货架')
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (form.value.id) {
      await warehouseApi.update(form.value.id, {
        warehouse: form.value.warehouse,
        name: form.value.name,
        shelf_name: form.value.shelf_name || null,
        location: form.value.location,
        description: form.value.description
      })
    } else {
      const code = (form.value.name || '').trim()
      await warehouseApi.create({
        warehouse: form.value.warehouse,
        name: code,
        shelf_name: (form.value.shelf_name || '').trim() || null,
        location: form.value.location,
        description: form.value.description
      })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await warehouseApi.remove(id)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.list-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.list-card-header-start {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  min-width: 0;
  flex: 1;
}
.header-overview-grid {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 8px;
  justify-content: flex-start;
}
.header-overview-item {
  background: #161f33;
  border-radius: 8px;
  text-align: center;
  padding: 8px 14px;
  min-width: 88px;
  border: 1px solid #2a3446;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.header-overview-value {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
  line-height: 1.2;
}
.header-overview-label {
  font-size: 11px;
  color: #9ba8bf;
  margin-top: 2px;
}
.add-warehouse-btn {
  padding: 8px 14px;
  border-radius: 6px;
  flex-shrink: 0;
}
.list-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #e6edf7;
  flex-shrink: 0;
}
.warehouse-list-card :deep(.el-card__header) {
  background: #131c2f;
  border-bottom: 1px solid #28354a;
}
.warehouse-list-card :deep(.el-card__body) {
  padding-top: 12px;
}
.warehouse-collapse {
  border: none;
  --el-collapse-header-bg-color: #161f33;
  --el-collapse-header-text-color: #e6edf7;
  --el-collapse-border-color: #28354a;
}
.warehouse-collapse :deep(.el-collapse-item) {
  margin-bottom: 10px;
  border: 1px solid #28354a;
  border-radius: 8px;
  overflow: hidden;
  background: #131c2f;
}
.warehouse-collapse :deep(.el-collapse-item__header) {
  padding: 12px 14px;
  font-weight: 600;
  border-bottom: 1px solid #28354a;
  flex-wrap: nowrap;
  align-items: center;
  height: auto;
  line-height: 1.35;
}
/* 插槽根节点占满箭头左侧区域，避免内部 grid 仅随内容宽度被摆在视觉中间 */
.warehouse-collapse :deep(.el-collapse-item__header > :first-child) {
  flex: 1;
  min-width: 0;
  text-align: left;
}
.warehouse-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
  background: #0f1628;
}
.warehouse-collapse :deep(.el-collapse-item__content) {
  padding: 12px;
}
/* 标题列随内容宽度，统计紧跟标题，避免 1fr 把标题撑开导致卡片视觉上居中 */
.collapse-title {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  column-gap: 12px;
  width: 100%;
  min-width: 0;
  padding-right: 4px;
}
.collapse-title-start {
  justify-self: start;
  min-width: 0;
  max-width: min(320px, 42vw);
  overflow: hidden;
}
.collapse-title-stats {
  justify-self: start;
  min-width: 0;
  max-width: 100%;
}
.collapse-title-end {
  justify-self: end;
}
.collapse-wh-name {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: #e6edf7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.collapse-stat-grid {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  justify-content: flex-start;
  gap: 8px;
}
.collapse-stat-grid--primary .collapse-stat-item {
  min-width: 76px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.collapse-stat-grid--secondary {
  gap: 6px;
}
.collapse-stat-item {
  background: #161f33;
  border-radius: 8px;
  text-align: center;
  padding: 10px 12px;
  border: 1px solid #2a3446;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.22);
}
.collapse-stat-item--compact {
  padding: 7px 10px;
  min-width: 68px;
  border-radius: 6px;
}
.collapse-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
  line-height: 1.15;
}
.collapse-stat-item--compact .collapse-stat-value {
  font-size: 16px;
}
.collapse-stat-label {
  font-size: 11px;
  color: #9ba8bf;
  margin-top: 3px;
  line-height: 1.2;
}
.shelf-name-collapse .collapse-stat-item {
  background: #121a2b;
  border-color: #2a3446;
}
.collapse-add-btn {
  flex-shrink: 0;
}
/* 二级：按货架名称折叠 */
.shelf-name-collapse {
  border: none;
  --el-collapse-header-bg-color: #141d30;
}
.shelf-name-collapse :deep(.el-collapse-item) {
  margin-bottom: 8px;
  border: 1px solid #253149;
  border-radius: 6px;
  overflow: hidden;
  background: #0c1322;
}
.shelf-name-collapse :deep(.el-collapse-item:last-child) {
  margin-bottom: 0;
}
.shelf-name-collapse :deep(.el-collapse-item__header) {
  padding: 10px 12px;
  font-weight: 600;
  flex-wrap: nowrap;
  align-items: center;
  border-bottom: 1px solid #28354a;
  height: auto;
  line-height: 1.35;
}
.shelf-name-collapse :deep(.el-collapse-item__header > :first-child) {
  flex: 1;
  min-width: 0;
  text-align: left;
}
.shelf-name-collapse :deep(.el-collapse-item__wrap) {
  background: #0a0f1a;
}
.shelf-name-collapse :deep(.el-collapse-item__content) {
  padding: 10px 12px;
}
.shelf-name-title-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  column-gap: 10px;
  width: 100%;
  min-width: 0;
  padding-right: 4px;
}
.shelf-name-title-start {
  justify-self: start;
  min-width: 0;
  max-width: min(280px, 38vw);
  overflow: hidden;
}
.shelf-name-title-stats {
  justify-self: start;
  min-width: 0;
  max-width: 100%;
}
.shelf-name-title-end {
  justify-self: end;
}
.shelf-name-title-text {
  font-size: 14px;
  color: #cbd5e8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.shelf-subtable {
  width: 100%;
}
.shelf-no-table {
  margin-top: 0;
}
</style>
