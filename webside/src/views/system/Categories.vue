<template>
  <div>
    <el-card shadow="never" class="search-card">
      <el-row justify="end">
        <el-button type="primary" @click="openDialog()">
          <el-icon><Plus /></el-icon> {{ t('system.addCategory') }}
        </el-button>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="ID" prop="id" width="70" />
        <el-table-column :label="t('system.categoryName')" prop="name" />
        <el-table-column :label="t('common.description')" prop="description" show-overflow-tooltip />
        <el-table-column :label="t('system.inventoryCount')" prop="inventory_count" width="100" align="center" />
        <el-table-column :label="t('common.actions')" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">{{ t('common.edit') }}</el-button>
            <el-popconfirm :title="t('system.deleteCategoryConfirm')" @confirm="remove(row.id)">
              <template #reference>
                <el-button size="small" type="danger">{{ t('common.delete') }}</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? t('system.editCategory') : t('system.addCategory')" width="400px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item :label="t('common.name')" prop="name">
          <el-input v-model="form.name" :placeholder="t('system.categoryNameRequired')" />
        </el-form-item>
        <el-form-item :label="t('common.description')">
          <el-input v-model="form.description" type="textarea" :rows="3" :placeholder="t('system.optionalDescription')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { categoryApi } from '@/api/index.js'

const { t } = useI18n()

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const form = ref({ id: null, name: '', description: '' })
const rules = { name: [{ required: true, message: t('system.categoryNameRequired'), trigger: 'blur' }] }

async function load() {
  loading.value = true
  list.value = await categoryApi.list().finally(() => (loading.value = false))
}

function openDialog(row = null) {
  form.value = row ? { ...row } : { id: null, name: '', description: '' }
  dialogVisible.value = true
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (form.value.id) await categoryApi.update(form.value.id, form.value)
    else await categoryApi.create(form.value)
    ElMessage.success(t('common.success'))
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await categoryApi.remove(id)
  ElMessage.success(t('common.success'))
  load()
}

onMounted(load)
</script>

<style scoped>
.search-card { margin-bottom: 16px; border-radius: 8px; }
.table-card { border-radius: 8px; }
</style>
