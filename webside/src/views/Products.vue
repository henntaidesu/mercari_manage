<template>
  <div>
    <div class="page-header">
      <span class="page-title">商品管理</span>
      <el-button type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新增商品
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="12" :md="8">
          <el-input v-model="keyword" placeholder="搜索商品名称或SKU" clearable @change="load" prefix-icon="Search" />
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-select v-model="filterCat" placeholder="所有分类" clearable @change="load" style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <!-- 商品列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="图片" width="70" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.image"
              :src="row.image"
              :preview-src-list="[row.image]"
              style="width:40px;height:40px;border-radius:4px;object-fit:cover"
              fit="cover"
            />
            <el-icon v-else size="30" color="#ddd"><Picture /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="商品名称" prop="name" min-width="130" />
        <el-table-column label="SKU" prop="sku" width="120" />
        <el-table-column label="分类" prop="category_name" width="100" />
        <el-table-column label="单位" prop="unit" width="70" align="center" />
        <el-table-column label="单价" prop="price" width="90" align="right">
          <template #default="{ row }">¥{{ row.price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="总库存" prop="total_stock" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.total_stock > 0 ? 'success' : 'info'" size="small">{{ row.total_stock }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该商品？" @confirm="remove(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑商品' : '新增商品'" width="560px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-row :gutter="16">
          <el-col :span="14">
            <el-form-item label="商品名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入商品名称" />
            </el-form-item>
            <el-form-item label="SKU编码">
              <el-input v-model="form.sku" placeholder="可选，如：P-001" />
            </el-form-item>
            <el-form-item label="分类">
              <el-select v-model="form.category_id" placeholder="选择分类" clearable style="width:100%">
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="单位">
                  <el-input v-model="form.unit" placeholder="件" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="单价">
                  <el-input-number v-model="form.price" :min="0" :precision="2" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-col>
          <el-col :span="10">
            <el-form-item label="商品图片">
              <div class="image-upload-area" @click="triggerUpload">
                <img v-if="form.image" :src="form.image" class="preview-img" />
                <div v-else class="upload-placeholder">
                  <el-icon size="28" color="#ccc"><Camera /></el-icon>
                  <div class="upload-tip">点击上传图片</div>
                </div>
              </div>
              <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="handleImageUpload" />
              <el-button v-if="form.image" size="small" type="danger" text @click="form.image = null">移除图片</el-button>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选商品描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { productApi, categoryApi } from '@/api/index.js'

const list = ref([])
const loading = ref(false)
const categories = ref([])
const keyword = ref('')
const filterCat = ref(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const fileInput = ref()
const form = ref({ id: null, name: '', sku: '', category_id: null, unit: '件', price: 0, description: '', image: null })
const rules = { name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }] }

async function load() {
  loading.value = true
  const params = {}
  if (keyword.value) params.keyword = keyword.value
  if (filterCat.value) params.category_id = filterCat.value
  list.value = await productApi.list(params).finally(() => (loading.value = false))
}

function openDialog(row = null) {
  form.value = row ? { ...row } : { id: null, name: '', sku: '', category_id: null, unit: '件', price: 0, description: '', image: null }
  dialogVisible.value = true
}

function triggerUpload() {
  fileInput.value.click()
}

function handleImageUpload(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片不能超过5MB')
    return
  }
  const reader = new FileReader()
  reader.onload = (ev) => { form.value.image = ev.target.result }
  reader.readAsDataURL(file)
  e.target.value = ''
}

async function submit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (form.value.id) await productApi.update(form.value.id, form.value)
    else await productApi.create(form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await productApi.remove(id)
  ElMessage.success('删除成功')
  load()
}

onMounted(async () => {
  categories.value = await categoryApi.list()
  load()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 600; }
.search-card { margin-bottom: 16px; border-radius: 8px; }
.table-card { border-radius: 8px; }

.image-upload-area {
  width: 120px;
  height: 120px;
  border: 2px dashed #3b4961;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transition: border-color 0.2s;
}
.image-upload-area:hover { border-color: #409EFF; }
.preview-img { width: 100%; height: 100%; object-fit: cover; }
.upload-placeholder { text-align: center; }
.upload-tip { font-size: 12px; color: #8e9bb3; margin-top: 6px; }
</style>
