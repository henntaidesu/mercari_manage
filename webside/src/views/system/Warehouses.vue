<template>
  <div>
    <el-card shadow="never" class="warehouse-list-card">
      <template #header>
        <div class="list-card-header">
          <div class="list-card-header-start">
            <span class="list-card-title">仓库与货架</span>
            <div class="header-overview-grid">
              <div class="header-overview-item">
                <div class="header-overview-value">{{ mergedWarehouse.shelf_count }}</div>
                <div class="header-overview-label">货架位</div>
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
          <el-button type="primary" class="header-primary-btn" @click="openAddWarehouseNameDialog">
            <el-icon><Plus /></el-icon>
            添加仓库
          </el-button>
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
                    <div class="collapse-stat-label">货架分区</div>
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
              <div class="collapse-title-end collapse-title-actions" @click.stop>
                <el-button type="primary" size="small" @click.stop="openDialogShelfOnly(grp.warehouse, '')">
                  <el-icon><Plus /></el-icon>
                  添加货架
                </el-button>
                <el-button type="primary" size="small" plain @click.stop="openRenameWarehouseDialog(grp)">
                  修改名称
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
                  <div class="shelf-name-title-end shelf-name-title-actions" @click.stop>
                    <el-button
                      type="primary"
                      size="small"
                      class="collapse-add-btn"
                      @click.stop="openDialogForShelfGroup(grp.warehouse, sub.rawShelfName)"
                    >
                      <el-icon><Plus /></el-icon>
                      添加货架号
                    </el-button>
                    <el-button type="primary" size="small" plain @click.stop="openRenameShelfNameDialog(grp, sub)">
                      修改名称
                    </el-button>
                  </div>
                </div>
              </template>
              <el-table :data="sub.shelves" border stripe size="small" class="shelf-subtable shelf-no-table">
                <el-table-column label="货架主键" prop="id" width="88" align="center" />
                <el-table-column label="货架号" prop="name" min-width="120" />
                <el-table-column label="位置" prop="location" min-width="130" />
                <el-table-column label="描述" prop="description" min-width="160" show-overflow-tooltip />
                <el-table-column label="商品种类" prop="product_types" width="100" align="center" />
                <el-table-column label="总库存量" prop="total_quantity" width="100" align="center" />
                <el-table-column label="操作" width="100" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" type="primary" link @click="openDialog(row)">编辑</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </el-collapse-item>
      </el-collapse>
      <el-empty v-else description="还没有货架数据，请先添加仓库">
        <el-button type="primary" @click="openAddWarehouseNameDialog">
          <el-icon><Plus /></el-icon>
          添加仓库
        </el-button>
      </el-empty>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="shelfDialogTitle" width="460px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="92px">
        <el-form-item v-if="form.id" label="货架主键">
          <el-input :model-value="String(form.id)" disabled />
        </el-form-item>
        <el-form-item label="所属仓库" prop="warehouse">
          <el-input v-model="form.warehouse" clearable />
        </el-form-item>
        <el-form-item label="货架名称">
          <el-input v-model="form.shelf_name" clearable />
        </el-form-item>
        <el-form-item v-if="form.id || createDialogKind !== 'shelfOnly'" label="货架号" prop="name">
          <el-input v-model="form.name" clearable />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="form.location" clearable />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" clearable />
        </el-form-item>
        <el-form-item v-if="form.id" label="库存迁移">
          <el-button type="warning" plain @click="openMigrateInventoryDialog">一键迁移物品</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="migrateInventoryDialogVisible" title="一键迁移物品" width="440px" destroy-on-close @closed="onMigrateInventoryDialogClosed">
      <el-form label-width="88px">
        <el-form-item label="目标货架" required>
          <el-cascader
            v-model="migrateTargetWarehousePath"
            :options="migrateTargetCascaderOptions"
            :props="migrateTargetCascaderProps"
            :show-all-levels="false"
            clearable
            filterable
            placeholder=""
            style="width: 100%"
            @change="onMigrateTargetChange"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="migrateInventoryDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="migrateInventorySubmitting" @click="confirmMigrateInventory">确定迁移</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="renameWarehouseDialogVisible"
      title="修改仓库名称"
      width="640px"
      destroy-on-close
      class="rename-warehouse-dialog"
      @closed="onRenameWarehouseDialogClosed"
    >
      <el-form label-width="96px">
        <el-form-item label="当前名称">
          <el-input :model-value="renameWarehouseOld" disabled />
        </el-form-item>
        <el-form-item label="新名称" required>
          <el-input
            v-model="renameWarehouseNew"
            clearable
            @keyup.enter="submitRenameWarehouse"
          />
        </el-form-item>
      </el-form>

      <el-divider content-position="left">货架位与删除</el-divider>
      <el-table :data="renameDialogShelves" border stripe size="small" max-height="280" class="rename-shelf-table">
        <el-table-column label="货架主键" prop="id" width="88" align="center" />
        <el-table-column label="货架号" prop="name" min-width="100" />
        <el-table-column label="货架名称" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ row.shelf_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="位置" prop="location" min-width="100" show-overflow-tooltip />
        <el-table-column label="总库存" prop="total_quantity" width="80" align="center" />
        <el-table-column label="操作" width="88" align="center" fixed="right">
          <template #default="{ row }">
            <el-popconfirm
              title="仅当该货架无库存且无出入库记录时可删除，确定删除？"
              width="260"
              @confirm="removeShelfFromRenameDialog(row.id)"
            >
              <template #reference>
                <el-button type="danger" link size="small" @click.stop>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <div class="rename-dialog-footer">
          <el-popconfirm
            :title="warehouseDeleteConfirmTextForDialog()"
            width="320"
            confirm-button-text="确定删除"
            cancel-button-text="取消"
            @confirm="removeWarehouseGroupForDialog"
          >
            <template #reference>
              <el-button type="danger" plain>删除整个仓库</el-button>
            </template>
          </el-popconfirm>
          <div class="rename-dialog-footer-right">
            <el-button @click="renameWarehouseDialogVisible = false">关闭</el-button>
            <el-button type="primary" :loading="renameWarehouseSubmitting" @click="submitRenameWarehouse">保存名称</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="renameShelfNameDialogVisible"
      title="修改货架名称"
      width="440px"
      destroy-on-close
      @closed="onRenameShelfNameDialogClosed"
    >
      <el-form label-width="100px">
        <el-form-item label="所属仓库">
          <el-input :model-value="renameShelfWarehouse" disabled />
        </el-form-item>
        <el-form-item label="当前名称">
          <el-input :model-value="renameShelfOldDisplay" disabled />
        </el-form-item>
        <el-form-item label="新名称">
          <el-input
            v-model="renameShelfNew"
            clearable
            @keyup.enter="submitRenameShelfName"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameShelfNameDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="renameShelfSubmitting" @click="submitRenameShelfName">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="addWarehouseNameDialogVisible" title="添加仓库" width="420px" destroy-on-close @closed="onAddWarehouseNameDialogClosed">
      <el-form label-width="88px" @submit.prevent="confirmAddWarehouseName">
        <el-form-item label="仓库名称" required>
          <el-input
            v-model="newWarehouseNameInput"
            clearable
            @keyup.enter="confirmAddWarehouseName"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addWarehouseNameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddWarehouseName">下一步：添加货架</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { warehouseApi } from '@/api/index.js'
import { warehouseShelfLabel, warehouseShelfLeafLabel } from '@/utils/warehouseLabel.js'

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
const addWarehouseNameDialogVisible = ref(false)
const newWarehouseNameInput = ref('')
const renameWarehouseDialogVisible = ref(false)
/** 弹窗内列表筛选键（改名成功后会更新为新名称） */
const renameWarehouseGroupKey = ref('')
const renameWarehouseOld = ref('')
const renameWarehouseNew = ref('')
const renameWarehouseSubmitting = ref(false)
const renameShelfNameDialogVisible = ref(false)
const renameShelfWarehouse = ref('')
const renameShelfOldRaw = ref('')
const renameShelfOldDisplay = ref('')
const renameShelfNew = ref('')
const renameShelfSubmitting = ref(false)
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
/** 新建来源：shelfOnly = 添加货架（货架号可空）；shelfNo = 添加货架号；shelf = 编辑等 */
const createDialogKind = ref('shelf')

const migrateInventoryDialogVisible = ref(false)
const migrateSourceWarehouseId = ref(null)
const migrateTargetWarehouseId = ref(null)
const migrateTargetWarehousePath = ref([])
const migrateInventorySubmitting = ref(false)

const shelfDialogTitle = computed(() => {
  if (form.value?.id) return '编辑货架'
  const wh = normalizeWarehouseName(form.value?.warehouse)
  if (createDialogKind.value === 'shelfNo') {
    const sn = (form.value?.shelf_name || '').trim()
    if (sn) return `添加货架号 · ${wh} / ${sn}`
    return `添加货架号 · ${wh}`
  }
  if (createDialogKind.value === 'shelfOnly') {
    if (wh && wh !== DEFAULT_WAREHOUSE) return `添加货架 · ${wh}`
    return '添加货架'
  }
  if (wh && wh !== DEFAULT_WAREHOUSE) return `新增货架 · ${wh}`
  return '新增货架'
})

const rules = {
  warehouse: [{ required: true, message: '请填写所属仓库', trigger: 'blur' }],
  name: [
    {
      validator: (_, val, cb) => {
        if (!form.value.id && createDialogKind.value === 'shelfOnly') return cb()
        if (!String(val ?? '').trim()) return cb(new Error('请填写货架号'))
        cb()
      },
      trigger: 'blur',
    },
  ],
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

const mergedWarehouse = computed(() => {
  const productTypes = list.value.reduce((sum, item) => sum + Number(item.product_types || 0), 0)
  const totalQuantity = list.value.reduce((sum, item) => sum + Number(item.total_quantity || 0), 0)
  return {
    shelf_count: list.value.length,
    product_types: productTypes,
    total_quantity: totalQuantity
  }
})

const migrateInventoryOptions = computed(() => {
  const sid = migrateSourceWarehouseId.value
  return list.value
    .filter((w) => w.id != null && Number(w.id) !== Number(sid))
    .map((w) => ({
      value: Number(w.id),
      label: `${normalizeWarehouseName(w.warehouse)} · ${warehouseShelfLabel(w)}`,
    }))
    .sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
})

const migrateTargetCascaderProps = {
  value: 'value',
  label: 'label',
  children: 'children',
  emitPath: true,
  checkStrictly: false,
}

const migrateTargetCascaderOptions = computed(() => {
  const sid = Number(migrateSourceWarehouseId.value)
  const byWh = new Map()
  for (const row of list.value) {
    const id = Number(row?.id)
    if (!Number.isFinite(id) || id === sid) continue
    const wh = normalizeWarehouseName(row.warehouse)
    if (!byWh.has(wh)) byWh.set(wh, [])
    byWh.get(wh).push(row)
  }
  const whNames = [...byWh.keys()].sort((a, b) => {
    if (a === DEFAULT_WAREHOUSE) return -1
    if (b === DEFAULT_WAREHOUSE) return 1
    return a.localeCompare(b, 'zh-CN')
  })
  return whNames.map((wh) => {
    const rows = byWh.get(wh)
    const shelfMap = new Map()
    for (const r of rows) {
      const sn = r?.shelf_name && String(r.shelf_name).trim()
        ? String(r.shelf_name).trim()
        : '（未设置货架名称）'
      if (!shelfMap.has(sn)) shelfMap.set(sn, [])
      shelfMap.get(sn).push(r)
    }
    const snKeys = [...shelfMap.keys()].sort((a, b) => {
      if (a === '（未设置货架名称）') return 1
      if (b === '（未设置货架名称）') return -1
      return a.localeCompare(b, 'zh-CN')
    })
    return {
      value: `WH:${encodeURIComponent(wh)}`,
      label: wh,
      children: snKeys.map((sn) => ({
        value: `SN:${encodeURIComponent(wh)}::${encodeURIComponent(sn)}`,
        label: sn,
        children: shelfMap.get(sn)
          .slice()
          .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN'))
          .map((r) => ({
            value: `SID:${r.id}`,
            label: warehouseShelfLeafLabel(r),
            children: [],
          })),
      })),
    }
  })
})

function onMigrateTargetChange(path) {
  const picked = Array.isArray(path) ? path[path.length - 1] : null
  if (!picked || !String(picked).startsWith('SID:')) {
    migrateTargetWarehouseId.value = null
    return
  }
  const id = Number(String(picked).slice(4))
  migrateTargetWarehouseId.value = Number.isFinite(id) ? id : null
}

const renameDialogShelves = computed(() => {
  if (!renameWarehouseDialogVisible.value || !renameWarehouseGroupKey.value) return []
  const key = renameWarehouseGroupKey.value
  return list.value.filter((r) => normalizeWarehouseName(r.warehouse) === key)
})

function onMigrateInventoryDialogClosed() {
  migrateSourceWarehouseId.value = null
  migrateTargetWarehouseId.value = null
  migrateTargetWarehousePath.value = []
}

function openMigrateInventoryDialog() {
  if (!form.value?.id) return
  migrateSourceWarehouseId.value = Number(form.value.id)
  migrateTargetWarehouseId.value = null
  migrateTargetWarehousePath.value = []
  migrateInventoryDialogVisible.value = true
}

async function confirmMigrateInventory() {
  const tid = migrateTargetWarehouseId.value
  const sid = migrateSourceWarehouseId.value
  if (tid == null || tid === '') {
    ElMessage.warning('请选择目标货架')
    return
  }
  if (Number(tid) === Number(sid)) {
    ElMessage.warning('目标不能与当前货架相同')
    return
  }
  migrateInventorySubmitting.value = true
  try {
    const res = await warehouseApi.migrateInventory(sid, { target_warehouse_id: Number(tid) })
    const n = res?.moved ?? 0
    try {
      await warehouseApi.remove(Number(sid))
      ElMessage.success(n > 0 ? `已迁移 ${n} 条库存，并已删除原货架` : '已删除原货架')
    } catch (e2) {
      const msg = apiErrorMessage(e2)
      ElMessage.warning(
        n > 0
          ? `已迁移 ${n} 条库存，但删除原货架失败：${msg}`
          : `库存迁移完成，但删除原货架失败：${msg}`
      )
    }
    migrateInventoryDialogVisible.value = false
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(apiErrorMessage(e))
  } finally {
    migrateInventorySubmitting.value = false
  }
}

async function load() {
  const rows = await warehouseApi.list()
  list.value = rows.map((item) => ({ ...item, warehouse: normalizeWarehouseName(item.warehouse) }))
}

function onAddWarehouseNameDialogClosed() {
  newWarehouseNameInput.value = ''
}

function onRenameShelfNameDialogClosed() {
  renameShelfWarehouse.value = ''
  renameShelfOldRaw.value = ''
  renameShelfOldDisplay.value = ''
  renameShelfNew.value = ''
}

function openRenameShelfNameDialog(grp, sub) {
  renameShelfWarehouse.value = String(grp?.warehouse ?? '').trim() || DEFAULT_WAREHOUSE
  renameShelfOldRaw.value = sub?.rawShelfName != null ? String(sub.rawShelfName).trim() : ''
  renameShelfOldDisplay.value = String(sub?.label ?? '').trim() || '（未设置货架名称）'
  renameShelfNew.value = renameShelfOldRaw.value
  renameShelfNameDialogVisible.value = true
}

async function submitRenameShelfName() {
  const oldRaw = String(renameShelfOldRaw.value ?? '').trim()
  const newT = String(renameShelfNew.value ?? '').trim()
  if (oldRaw === newT) {
    ElMessage.warning('名称未变化')
    return
  }
  renameShelfSubmitting.value = true
  try {
    await warehouseApi.renameShelfNameGroup({
      warehouse: renameShelfWarehouse.value,
      old_shelf_name: oldRaw,
      new_shelf_name: newT,
    })
    ElMessage.success('货架名称已更新')
    renameShelfNameDialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(apiErrorMessage(e))
  } finally {
    renameShelfSubmitting.value = false
  }
}

function onRenameWarehouseDialogClosed() {
  renameWarehouseGroupKey.value = ''
  renameWarehouseOld.value = ''
  renameWarehouseNew.value = ''
}

function openRenameWarehouseDialog(grp) {
  const name = String(grp?.warehouse ?? '').trim() || DEFAULT_WAREHOUSE
  renameWarehouseGroupKey.value = name
  renameWarehouseOld.value = name
  renameWarehouseNew.value = name
  renameWarehouseDialogVisible.value = true
}

async function submitRenameWarehouse() {
  const oldW = (renameWarehouseOld.value || '').trim()
  const newW = (renameWarehouseNew.value || '').trim()
  if (!newW) {
    ElMessage.warning('请输入新仓库名称')
    return
  }
  if (normalizeWarehouseName(oldW) === normalizeWarehouseName(newW)) {
    ElMessage.warning('名称未变化')
    return
  }
  renameWarehouseSubmitting.value = true
  try {
    await warehouseApi.renameGroup({ old_warehouse: oldW, new_warehouse: newW })
    ElMessage.success('仓库名称已更新')
    const nextKey = normalizeWarehouseName(newW)
    renameWarehouseGroupKey.value = nextKey
    renameWarehouseOld.value = nextKey
    renameWarehouseNew.value = nextKey
    await load()
  } catch (e) {
    ElMessage.error(apiErrorMessage(e))
  } finally {
    renameWarehouseSubmitting.value = false
  }
}

function openAddWarehouseNameDialog() {
  newWarehouseNameInput.value = ''
  addWarehouseNameDialogVisible.value = true
}

function confirmAddWarehouseName() {
  const raw = (newWarehouseNameInput.value || '').trim()
  if (!raw) {
    ElMessage.warning('请输入仓库名称')
    return
  }
  const name = normalizeWarehouseName(raw)
  addWarehouseNameDialogVisible.value = false
  openDialogShelfOnly(name, '')
}

function warehouseDeleteConfirmTextForDialog() {
  const n = renameDialogShelves.value.length
  const wh = renameWarehouseGroupKey.value || ''
  const base = `将依次删除该仓库下全部 ${n} 个货架位；每个须无库存、无出入库及费用关联记录。确定删除「${wh}」？`
  if (wh === DEFAULT_WAREHOUSE) return `【默认仓库】${base}（删除后若仍有业务数据，部分货架位可能无法删除，请以提示为准。）`
  return base
}

async function removeWarehouseGroupForDialog() {
  const shelves = [...renameDialogShelves.value]
  if (!shelves.length) return
  const grp = {
    warehouse: renameWarehouseGroupKey.value,
    shelves,
    shelfCount: shelves.length,
  }
  await removeWarehouseGroup(grp, { closeRenameDialog: true })
}

async function removeWarehouseGroup(grp, options = {}) {
  const shelves = [...(grp.shelves || [])]
  if (!shelves.length) return
  let removed = 0
  for (const row of shelves) {
    try {
      await warehouseApi.remove(row.id)
      removed++
    } catch {
      await load()
      if (removed > 0) {
        ElMessage.warning(`已删除 ${removed} 个货架位后中止，请处理剩余项后重试`)
      }
      return
    }
  }
  ElMessage.success(`已删除仓库「${grp.warehouse}」共 ${removed} 个货架位`)
  await load()
  if (options.closeRenameDialog) renameWarehouseDialogVisible.value = false
}

async function removeShelfFromRenameDialog(id) {
  try {
    await warehouseApi.remove(id)
    ElMessage.success('删除成功')
    await load()
    if (!renameDialogShelves.value.length) renameWarehouseDialogVisible.value = false
  } catch (e) {
    ElMessage.error(apiErrorMessage(e))
  }
}

function openDialog(row = null) {
  if (row) {
    createDialogKind.value = 'shelf'
    form.value = { ...row, warehouse: normalizeWarehouseName(row.warehouse), shelf_name: row.shelf_name || '' }
  } else {
    openDialogShelfOnly(DEFAULT_WAREHOUSE, '')
    return
  }
  dialogVisible.value = true
}

/**
 * 二级「添加货架」：不必填货架号，预填当前分区的货架名称（rawShelfName 可为空）
 */
function openDialogShelfOnly(warehouseName, rawShelfName = '') {
  createDialogKind.value = 'shelfOnly'
  form.value = {
    id: null,
    warehouse: normalizeWarehouseName(warehouseName),
    shelf_name: rawShelfName != null && String(rawShelfName).trim() ? String(rawShelfName).trim() : '',
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

function apiErrorMessage(err) {
  const d = err?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d[0]?.msg) return d.map((x) => x.msg).join('；')
  return err?.message || '请求失败'
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = {
      warehouse: form.value.warehouse,
      name: (form.value.name || '').trim() || null,
      shelf_name: (form.value.shelf_name || '').trim() || null,
      location: form.value.location,
      description: form.value.description
    }
    if (form.value.id) {
      await warehouseApi.update(form.value.id, payload)
      ElMessage.success('保存成功')
    } else {
      const created = await warehouseApi.create(payload)
      ElMessage.success(`保存成功，货架主键：${created?.id ?? '—'}`)
    }
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(apiErrorMessage(e))
  } finally {
    submitting.value = false
  }
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
.header-primary-btn {
  flex-shrink: 0;
}
.rename-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  width: 100%;
}
.rename-dialog-footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.rename-shelf-table {
  width: 100%;
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
.collapse-title-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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
.shelf-name-title-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
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
