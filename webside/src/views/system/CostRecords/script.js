import { defineComponent, ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { costRecordApi, warehouseApi } from '@/api/index.js'
import { warehouseShelfLabel } from '@/utils/warehouseLabel.js'

export default defineComponent({
  setup() {
    const { t } = useI18n()

    const loading = ref(false)
    const submitting = ref(false)
    const list = ref([])
    const total = ref(0)
    const page = ref(1)
    const pageSize = ref(20)
    const warehouses = ref([])
    const dateRange = ref([])
    const dialogVisible = ref(false)
    const formRef = ref()
    const fileInputRef = ref()
    const uploadingImage = ref(false)

    const filters = ref({
      type: '',
      warehouse_id: null,
    })

    const typeOptions = computed(() => [
      { label: t('system.costRecordTypePurchase'), value: 'purchase' },
      { label: t('system.costRecordTypeShipping'), value: 'shipping' },
      { label: t('system.costRecordTypePackaging'), value: 'packaging' },
      { label: t('system.costRecordTypeOperation'), value: 'operation' },
      { label: t('system.costRecordTypeOther'), value: 'other' },
    ])

    const typeMap = computed(() => ({
      purchase: { label: t('system.costRecordTypePurchase'), tag: 'primary' },
      shipping: { label: t('system.costRecordTypeShipping'), tag: 'warning' },
      packaging: { label: t('system.costRecordTypePackaging'), tag: 'danger' },
      operation: { label: t('system.costRecordTypeOperation'), tag: 'success' },
      other: { label: t('system.costRecordTypeOther'), tag: 'info' },
    }))

    const createDefaultForm = () => ({
      id: null,
      cost_date: Date.now(),
      type: 'purchase',
      item_name: '',
      item_image: '',
      amount: null,
      quantity: 1,
      warehouse_id: null,
      remark: '',
    })

    const form = ref(createDefaultForm())

    function formatTs(ts) {
      if (!ts) return '-'
      return new Date(ts * 1000).toLocaleString()
    }

    const rules = computed(() => ({
      cost_date: [{ required: true, message: t('system.costRecordSelectRecordTime'), trigger: 'change' }],
      type: [{ required: true, message: t('system.costRecordSelectType'), trigger: 'change' }],
      item_name: [{ required: true, message: t('system.costRecordInputItemName'), trigger: 'blur' }],
      amount: [{ required: true, message: t('system.costRecordInputAmount'), trigger: 'blur' }],
      quantity: [{ required: true, message: t('system.costRecordInputQuantity'), trigger: 'blur' }],
    }))

    async function load() {
      loading.value = true
      const params = {
        page: page.value,
        page_size: pageSize.value,
      }
      if (filters.value.type) params.type = filters.value.type
      if (filters.value.warehouse_id) params.warehouse_id = filters.value.warehouse_id
      if (dateRange.value?.length === 2) {
        params.start_date = dateRange.value[0]
        params.end_date = dateRange.value[1]
      }
      const res = await costRecordApi.list(params).finally(() => {
        loading.value = false
      })
      list.value = res.items || []
      total.value = res.total || 0
    }

    function onFilterChange() {
      page.value = 1
      load()
    }

    function resetFilters() {
      filters.value = { type: '', warehouse_id: null }
      dateRange.value = []
      page.value = 1
      load()
    }

    function openCreate() {
      form.value = createDefaultForm()
      dialogVisible.value = true
    }

    function openEdit(row) {
      form.value = {
        id: row.id,
        cost_date: (row.cost_date || 0) * 1000,
        type: row.type,
        item_name: row.item_name || '',
        item_image: row.item_image || '',
        amount: Number(row.amount || 0),
        quantity: Number(row.quantity ?? 0),
        warehouse_id: row.warehouse_id || null,
        remark: row.remark || '',
      }
      dialogVisible.value = true
    }

    async function submit() {
      await formRef.value?.validate()
      submitting.value = true
      const payload = {
        cost_date: Math.floor((form.value.cost_date || Date.now()) / 1000),
        type: form.value.type,
        item_name: String(form.value.item_name || '').trim(),
        item_image: form.value.item_image || null,
        amount: Number(form.value.amount || 0),
        quantity: Number(form.value.quantity || 0),
        warehouse_id: form.value.warehouse_id,
        remark: form.value.remark || null,
      }
      try {
        if (form.value.id) {
          await costRecordApi.update(form.value.id, payload)
          ElMessage.success(t('system.costRecordUpdateSuccess'))
        } else {
          await costRecordApi.create(payload)
          ElMessage.success(t('system.costRecordCreateSuccess'))
        }
        dialogVisible.value = false
        load()
      } finally {
        submitting.value = false
      }
    }

    async function handleImageUpload(e) {
      const file = e.target.files?.[0]
      e.target.value = ''
      if (!file) return
      if (file.size > 25 * 1024 * 1024) {
        ElMessage.warning(t('system.costRecordImageSizeLimit'))
        return
      }
      uploadingImage.value = true
      try {
        const res = await costRecordApi.uploadImage(file)
        form.value.item_image = res.path || ''
        ElMessage.success(t('system.costRecordImageUploadSuccess'))
      } finally {
        uploadingImage.value = false
      }
    }

    function clearImage() {
      form.value.item_image = ''
    }

    async function remove(id) {
      await costRecordApi.remove(id)
      ElMessage.success(t('system.costRecordDeleteSuccess'))
      if (list.value.length === 1 && page.value > 1) page.value -= 1
      load()
    }

    onMounted(async () => {
      warehouses.value = await warehouseApi.list()
      load()
    })

    return {
      ref,
      computed,
      onMounted,
      ElMessage,
      useI18n,
      costRecordApi,
      warehouseApi,
      warehouseShelfLabel,
      t,
      loading,
      submitting,
      list,
      total,
      page,
      pageSize,
      warehouses,
      dateRange,
      dialogVisible,
      formRef,
      fileInputRef,
      uploadingImage,
      filters,
      typeOptions,
      typeMap,
      createDefaultForm,
      form,
      formatTs,
      rules,
      load,
      onFilterChange,
      resetFilters,
      openCreate,
      openEdit,
      submit,
      handleImageUpload,
      clearImage,
      remove,
    }
  },
})
