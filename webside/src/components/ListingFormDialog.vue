<template>
  <el-dialog
    :model-value="modelValue"
    title="组合出品"
    :width="isMobile ? '94vw' : '640px'"
    class="listing-dialog"
    destroy-on-close
    @update:model-value="onVisibleChange"
  >
    <el-form :model="form" label-width="110px">
      <el-form-item label="商品图片">
        <div class="listing-image-box">
          <el-image
            v-if="form.image"
            :src="form.image"
            fit="cover"
            class="listing-image-preview"
            :preview-src-list="[form.image]"
            :hide-on-click-modal="true"
            :preview-teleported="true"
          />
          <div v-else class="listing-image-empty">暂无图片</div>
          <div class="listing-image-actions">
            <input
              ref="fileInputRef"
              type="file"
              accept="image/*"
              style="display:none"
              @change="handleImageUpload"
            />
            <el-button type="primary" plain @click="fileInputRef?.click()">上传图片</el-button>
            <el-button @click="form.image = ''">清空</el-button>
          </div>
        </div>
      </el-form-item>
      <el-form-item label="商品名">
        <el-input v-model="form.name" placeholder="请输入商品名" clearable />
      </el-form-item>
      <el-form-item label="商品类别">
        <el-select v-model="form.category_id" clearable placeholder="请选择商品类别" style="width: 100%">
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="商品状态">
        <el-select v-model="form.status" placeholder="请选择商品状态" style="width: 100%">
          <el-option v-for="s in listingStatusOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="商品说明">
        <el-input v-model="form.description" type="textarea" :rows="4" maxlength="1000" show-word-limit placeholder="请输入商品说明" />
      </el-form-item>
      <el-form-item label="快递费负担">
        <el-select v-model="form.shipping_payer" placeholder="请选择快递费负担" style="width: 100%">
          <el-option v-for="s in shippingPayerOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="配送方法">
        <el-select v-model="form.shipping_method" placeholder="请选择配送方法" style="width: 100%">
          <el-option v-for="s in shippingMethodOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="发货地址">
        <el-input v-model="form.shipping_from" placeholder="例如：东京都" clearable />
      </el-form-item>
      <el-form-item label="最大发货天数">
        <el-select v-model="form.shipping_days" placeholder="请选择最大发货天数" style="width: 100%">
          <el-option v-for="s in shippingDaysOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="出售类型">
        <el-select v-model="form.sale_type" placeholder="请选择出售类型" style="width: 100%">
          <el-option v-for="s in saleTypeOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="onVisibleChange(false)">取消</el-button>
        <el-button type="primary" @click="submitStub">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  categories: { type: Array, default: () => [] },
  initialData: { type: Object, default: null },
  isMobile: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const fileInputRef = ref()
const form = ref(getDefaultForm())

const listingStatusOptions = [
  { label: '新品、未使用', value: 'new_unused' },
  { label: '未使用に近い', value: 'almost_unused' },
  { label: '目立った傷や汚れなし', value: 'good' },
  { label: 'やや傷や汚れあり', value: 'fair' },
  { label: '傷や汚れあり', value: 'used' }
]
const shippingPayerOptions = [
  { label: '送料込み(出品者负担)', value: 'seller' },
  { label: '着払い(购买者负担)', value: 'buyer' }
]
const shippingMethodOptions = [
  { label: '未定', value: 'undecided' },
  { label: 'らくらくメルカリ便', value: 'rakuraku' },
  { label: 'ゆうゆうメルカリ便', value: 'yuuyu' },
  { label: '普通邮便(定形、定形外)', value: 'regular_mail' }
]
const shippingDaysOptions = [
  { label: '1~2天', value: '1_2_days' },
  { label: '2~3天', value: '2_3_days' },
  { label: '4~7天', value: '4_7_days' }
]
const saleTypeOptions = [
  { label: '即购', value: 'instant_buy' },
  { label: '价格可谈', value: 'negotiable' }
]

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    const seed = props.initialData || {}
    form.value = {
      ...getDefaultForm(),
      image: seed.image || '',
      name: seed.name || '',
      category_id: seed.category_id ?? null,
      description: seed.description || ''
    }
  }
)

function getDefaultForm() {
  return {
    image: '',
    name: '',
    category_id: null,
    status: 'new_unused',
    description: '',
    shipping_payer: 'seller',
    shipping_method: 'undecided',
    shipping_from: '',
    shipping_days: '2_3_days',
    sale_type: 'instant_buy'
  }
}

function onVisibleChange(v) {
  emit('update:modelValue', v)
}

function handleImageUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片不能超过5MB')
    return
  }
  const reader = new FileReader()
  reader.onload = (ev) => {
    form.value.image = ev.target?.result || ''
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

function submitStub() {
  emit('saved', { ...form.value })
  ElMessage.success('出品表单已保存（暂未对接接口）')
  onVisibleChange(false)
}
</script>

<style scoped>
.listing-image-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
}
.listing-image-preview {
  width: 96px;
  height: 96px;
  border-radius: 6px;
}
.listing-image-empty {
  width: 96px;
  height: 96px;
  border: 1px dashed #5a6b88;
  border-radius: 6px;
  color: #8ea0bf;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.listing-image-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
