<template>
  <div>
    <el-card shadow="never" class="search-card">
      <div class="warehouse-head">
        <div>
          <div class="warehouse-title">仓库管理（按仓库区分货架）</div>
          <div class="warehouse-subtitle">支持按仓库筛选，历史空值默认归入“默认仓库”</div>
        </div>
        <div class="warehouse-actions">
          <el-select v-model="selectedWarehouse" placeholder="选择仓库" style="width: 180px">
            <el-option label="全部仓库" value="" />
            <el-option
              v-for="w in warehouseOptions"
              :key="w"
              :label="w"
              :value="w"
            />
          </el-select>
          <el-button @click="openWarehouseDialog">新建仓库</el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="hover" class="overview-card">
      <div class="overview-grid">
        <div class="overview-item">
          <div class="overview-value">{{ mergedWarehouse.shelf_count }}</div>
          <div class="overview-label">货架数量</div>
        </div>
        <div class="overview-item">
          <div class="overview-value">{{ mergedWarehouse.product_types }}</div>
          <div class="overview-label">商品种类</div>
        </div>
        <div class="overview-item">
          <div class="overview-value">{{ mergedWarehouse.total_quantity }}</div>
          <div class="overview-label">总库存量</div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="warehouse-list-card">
      <template #header>
        <span class="list-card-title">仓库列表</span>
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
              <div class="collapse-title-center">
                <span class="collapse-wh-meta">
                  货架名称 {{ grp.shelfNameGroups.length }} 组 · 货架号 {{ grp.shelfCount }} · 商品种类 {{ grp.productTypes }} · 总库存 {{ grp.totalQuantity }}
                </span>
              </div>
              <div class="collapse-title-end">
                <el-button
                  type="primary"
                  size="small"
                  class="collapse-add-btn"
                  @click.stop="openDialogForWarehouse(grp.warehouse)"
                >
                  <el-icon><Plus /></el-icon>
                  新增货架
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
                  <div class="shelf-name-title-center">
                    <span class="shelf-name-title-meta">
                      货架号 {{ sub.shelfCount }} · 商品种类 {{ sub.productTypes }} · 总库存 {{ sub.totalQuantity }}
                    </span>
                  </div>
                  <div class="shelf-name-title-end">
                    <el-button
                      type="primary"
                      size="small"
                      class="collapse-add-btn"
                      @click.stop="openDialogForShelfGroup(grp.warehouse, sub.rawShelfName)"
                    >
                      <el-icon><Plus /></el-icon>
                      新增货架
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑货架' : '新增货架'" width="440px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="仓库" prop="warehouse">
          <el-input v-model="form.warehouse" placeholder="请输入仓库名称（如 1号仓）" />
        </el-form-item>
        <el-form-item label="货架名称">
          <el-input v-model="form.shelf_name" placeholder="可选，如：一层左、展示名" clearable />
        </el-form-item>
        <el-form-item v-if="form.id" label="货架号" prop="name">
          <el-select v-model="form.name" filterable allow-create default-first-option placeholder="请选择或输入货架号">
            <el-option
              v-for="code in shelfNoOptionsForEdit"
              :key="code"
              :label="code"
              :value="code"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="货架号" prop="names">
          <el-select
            v-model="form.names"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请选择或输入货架号（可多选）"
          >
            <el-option
              v-for="code in shelfNoOptionsForCreate"
              :key="code"
              :label="code"
              :value="code"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!form.id && (form.names || []).length > 1" class="form-hint-item">
          <span class="form-hint">批量新增多个货架号时，下方「货架名称」仅保存后可在各行单独编辑生效。</span>
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
const selectedWarehouse = ref('')
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
  names: [],
  location: '',
  description: ''
})
const rules = {
  warehouse: [{ required: true, message: '请输入仓库名称', trigger: 'blur' }],
  name: [{ required: true, message: '请输入货架号', trigger: 'blur' }],
  names: [{
    validator: (_, value, callback) => {
      if (!Array.isArray(value) || value.length === 0) {
        callback(new Error('请选择至少一个货架号'))
        return
      }
      callback()
    },
    trigger: 'change'
  }]
}

const warehouseOptions = computed(() => {
  const all = list.value.map((item) => normalizeWarehouseName(item.warehouse))
  return [...new Set(all)]
})

const filteredList = computed(() => {
  if (!selectedWarehouse.value) {
    return list.value
  }
  return list.value.filter((item) => normalizeWarehouseName(item.warehouse) === selectedWarehouse.value)
})

/** 一级：仓库 → 二级：货架名称分组 → 三级：货架号表格 */
const groupedByWarehouse = computed(() => {
  const rows = filteredList.value
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

const shelfNoOptionsForEdit = computed(() => {
  const warehouseName = normalizeWarehouseName(form.value.warehouse)
  const codes = list.value
    .filter((item) => normalizeWarehouseName(item.warehouse) === warehouseName)
    .map((item) => item.name)
  return [...new Set(codes)]
})

const shelfNoOptionsForCreate = computed(() => {
  const targetWh = form.value.warehouse || DEFAULT_WAREHOUSE
  const selectedNames = new Set((form.value.names || []).map((v) => String(v).trim()).filter(Boolean))

  const normWh = (w) => w || DEFAULT_WAREHOUSE

  const namesFromDefault = list.value
    .filter((item) => normWh(item.warehouse) === DEFAULT_WAREHOUSE)
    .map((item) => item.name)
    .filter(Boolean)

  const namesInTarget = list.value
    .filter((item) => normWh(item.warehouse) === targetWh)
    .map((item) => item.name)
    .filter(Boolean)

  const pool = new Set([...namesFromDefault, ...namesInTarget])
  let options = [...pool].filter((name) => !selectedNames.has(name))

  if (targetWh !== DEFAULT_WAREHOUSE) {
    const existingInTarget = new Set(namesInTarget)
    options = options.filter((name) => !existingInTarget.has(name))
  }

  return [...new Set(options)]
})

const mergedWarehouse = computed(() => {
  const productTypes = filteredList.value.reduce((sum, item) => sum + Number(item.product_types || 0), 0)
  const totalQuantity = filteredList.value.reduce((sum, item) => sum + Number(item.total_quantity || 0), 0)
  return {
    shelf_count: filteredList.value.length,
    product_types: productTypes,
    total_quantity: totalQuantity
  }
})

async function load() {
  const rows = await warehouseApi.list()
  list.value = rows.map((item) => ({ ...item, warehouse: normalizeWarehouseName(item.warehouse) }))
}

function openDialog(row = null) {
  form.value = row
    ? { ...row, warehouse: normalizeWarehouseName(row.warehouse), names: [], shelf_name: row.shelf_name || '' }
    : {
        id: null,
        warehouse: selectedWarehouse.value || DEFAULT_WAREHOUSE,
        shelf_name: '',
        name: '',
        names: [],
        location: '',
        description: ''
      }
  dialogVisible.value = true
}

/** 在某个仓库分组下新增货架（预填该仓库名称） */
function openDialogForWarehouse(warehouseName) {
  form.value = {
    id: null,
    warehouse: normalizeWarehouseName(warehouseName),
    shelf_name: '',
    name: '',
    names: [],
    location: '',
    description: '',
  }
  dialogVisible.value = true
}

/** 在某货架名称分组下新增（预填仓库 + 货架名称） */
function openDialogForShelfGroup(warehouseName, rawShelfName) {
  form.value = {
    id: null,
    warehouse: normalizeWarehouseName(warehouseName),
    shelf_name: rawShelfName ? String(rawShelfName).trim() : '',
    name: '',
    names: [],
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
  selectedWarehouse.value = name
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
      const codes = [...new Set((form.value.names || []).map((v) => String(v).trim()).filter(Boolean))]
      const batch = codes.length > 1
      const sn = (form.value.shelf_name || '').trim()
      for (const code of codes) {
        await warehouseApi.create({
          warehouse: form.value.warehouse,
          name: code,
          shelf_name: batch ? null : (sn || null),
          location: form.value.location,
          description: form.value.description
        })
      }
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
.search-card { margin-bottom: 16px; border-radius: 8px; }
.warehouse-head { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
.warehouse-actions { display: flex; align-items: center; gap: 10px; }
.warehouse-title { font-size: 18px; font-weight: 600; color: #e6edf7; }
.warehouse-subtitle { font-size: 12px; color: #9ba8bf; margin-top: 4px; }
.overview-card {
  border-radius: 10px;
  margin-bottom: 16px;
  background: #131c2f !important;
  border: 1px solid #28354a !important;
}
.overview-card :deep(.el-card__body) {
  padding: 16px;
  background: transparent !important;
}
.overview-grid { display: grid; grid-template-columns: repeat(3, minmax(100px, 1fr)); gap: 12px; }
.overview-item {
  background: #161f33;
  border-radius: 8px;
  text-align: center;
  padding: 14px 10px;
  border: 1px solid #2a3446;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.overview-value { font-size: 24px; font-weight: 700; color: #409eff; line-height: 1.2; }
.overview-label { font-size: 12px; color: #9ba8bf; margin-top: 4px; }

.list-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #e6edf7;
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
}
.warehouse-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
  background: #0f1628;
}
.warehouse-collapse :deep(.el-collapse-item__content) {
  padding: 12px;
}
/* 一行：左仓库名 | 中统计（红框区域/视觉中心）| 右按钮 */
.collapse-title {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  column-gap: 10px;
  width: 100%;
  min-width: 0;
  padding-right: 4px;
}
.collapse-title-start {
  justify-self: start;
  min-width: 0;
  overflow: hidden;
}
.collapse-title-center {
  justify-self: center;
  text-align: center;
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
.collapse-wh-meta {
  display: inline-block;
  font-size: 12px;
  font-weight: 500;
  color: #9ba8bf;
  white-space: nowrap;
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
}
.shelf-name-collapse :deep(.el-collapse-item__wrap) {
  background: #0a0f1a;
}
.shelf-name-collapse :deep(.el-collapse-item__content) {
  padding: 10px 12px;
}
.shelf-name-title-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  column-gap: 8px;
  width: 100%;
  min-width: 0;
  padding-right: 4px;
}
.shelf-name-title-start {
  justify-self: start;
  min-width: 0;
  overflow: hidden;
}
.shelf-name-title-center {
  justify-self: center;
  text-align: center;
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
.shelf-name-title-meta {
  font-size: 12px;
  font-weight: 500;
  color: #8b9ab5;
  white-space: nowrap;
}
.shelf-subtable {
  width: 100%;
}
.shelf-no-table {
  margin-top: 0;
}
.form-hint-item {
  margin-bottom: 0 !important;
}
.form-hint {
  font-size: 12px;
  color: #8b9ab5;
  line-height: 1.45;
}
</style>
