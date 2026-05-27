import { defineComponent, ref, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { mercariAccountApi, mercariApi, webDriveApi } from '@/api/index.js'

export default defineComponent({
  setup() {
    const { t } = useI18n()

    const MERCARI_HOME = 'https://jp.mercari.com/'

    /** 新增账号前共用的 WebDrive 会话键，与后端抓包/出品等约定一致 */
    const MERCARI_PREPARE_KEY = 'mercari_prepare'

    function browserKeyFor(accountId) {
      return `mercari_${accountId}`
    }

    const loading = ref(false)
    const submitting = ref(false)
    const list = ref([])
    const total = ref(0)
    const page = ref(1)
    const pageSize = ref(20)
    const dialogVisible = ref(false)
    const formRef = ref()

    const statusOptions = [
      { label: t('mercariAccounts.enabled'), value: 'active' },
      { label: t('mercariAccounts.disabled'), value: 'disabled' },
    ]

    const autoFetchSwitchOptions = [
      { label: t('mercariAccounts.autoFetchOff'), value: 0 },
      { label: t('mercariAccounts.autoFetchOn'), value: 1 },
    ]

    const fetchIntervalOptions = [
      { label: t('mercariAccounts.interval15min'), value: '15' },
      { label: t('mercariAccounts.interval30min'), value: '30' },
      { label: t('mercariAccounts.interval1h'), value: '60' },
      { label: t('mercariAccounts.interval3h'), value: '3h' },
      { label: t('mercariAccounts.interval6h'), value: '6h' },
    ]

    const legacyFetchIntervalLabels = {
      '10': t('mercariAccounts.interval10min'),
      '12h': t('mercariAccounts.interval12h'),
      '24h': t('mercariAccounts.interval24h'),
    }

    function fetchIntervalLabel(v) {
      if (v == null || v === '') return '-'
      const key = String(v)
      const cur = fetchIntervalOptions.find((o) => o.value === key)
      if (cur) return cur.label
      return legacyFetchIntervalLabels[key] || key
    }

    function pauseWindowLabel(row) {
      if (!row || row.is_open !== 1) return ''
      const s = String(row.pause_start_time || '').trim()
      const e = String(row.pause_end_time || '').trim()
      if (!s || !e || s === e) return ''
      return `${s} - ${e}`
    }

    function autoFetchTasksLabel(row) {
      if (!row || row.is_open !== 1) return ''
      const parts = []
      if (row.auto_fetch_order_list === 1) parts.push(t('mercariAccounts.taskShortOrderList'))
      if (row.auto_fetch_on_sale === 1) parts.push(t('mercariAccounts.taskShortOnSale'))
      if (row.auto_fetch_todos === 1) parts.push(t('mercariAccounts.taskShortTodos'))
      if (row.auto_fetch_notifications === 1) parts.push(t('mercariAccounts.taskShortNotifications'))
      return parts.join(t('mercariAccounts.taskJoiner'))
    }

    function onAutoFetchToggle() {
      if (form.value.is_open !== 1) {
        form.value.fetch_interval = ''
        form.value.auto_fetch_order_list = 0
        form.value.auto_fetch_on_sale = 0
        form.value.auto_fetch_todos = 0
        form.value.auto_fetch_notifications = 0
        form.value.auto_fetch_relist = 0
        form.value.pause_start_time = null
        form.value.pause_end_time = null
      }
      nextTick(() => formRef.value?.clearValidate(['fetch_interval', 'pause_window']))
    }

    function onAutoFetchTaskChange() {
      nextTick(() => formRef.value?.validateField('fetch_interval').catch(() => {}))
    }

    const createDefaultForm = () => ({
      id: null,
      account_name: '',
      seller_id: '',
      status: 'disabled',
      remark: '',
      is_open: 0,
      fetch_interval: '',
      auto_fetch_order_list: 0,
      auto_fetch_on_sale: 0,
      auto_fetch_todos: 0,
      auto_fetch_notifications: 0,
      auto_fetch_relist: 0,
      pause_start_time: null,
      pause_end_time: null,
    })

    const form = ref(createDefaultForm())

    const sellerIdRules = [
      {
        validator(_rule, val, cb) {
          const text = String(val || '').trim()
          if (!text) return cb()
          if (!/^\d+$/.test(text)) return cb(new Error(t('mercariAccounts.errSellerIdDigits')))
          cb()
        },
        trigger: 'blur',
      },
    ]

    const formRules = {
      account_name: [{ required: true, message: t('mercariAccounts.errAccountNameRequired'), trigger: 'blur' }],
      seller_id: sellerIdRules,
      status: [{ required: true, message: t('mercariAccounts.errStatusRequired'), trigger: 'change' }],
      is_open: [{ required: true, message: t('common.selectPlaceholder'), trigger: 'change' }],
      fetch_interval: [
        {
          validator(_rule, val, cb) {
            if (form.value.is_open === 1) {
              if (!val || !String(val).trim()) {
                cb(new Error(t('mercariAccounts.errIntervalRequired')))
                return
              }
              const anyTask =
                form.value.auto_fetch_order_list === 1 ||
                form.value.auto_fetch_on_sale === 1 ||
                form.value.auto_fetch_todos === 1 ||
                form.value.auto_fetch_notifications === 1
              if (!anyTask) {
                cb(new Error(t('mercariAccounts.errPickOneTask')))
                return
              }
            }
            cb()
          },
          trigger: 'change',
        },
      ],
      pause_window: [
        {
          validator(_rule, _val, cb) {
            if (form.value.is_open !== 1) return cb()
            const s = String(form.value.pause_start_time || '').trim()
            const e = String(form.value.pause_end_time || '').trim()
            if (!s && !e) return cb()
            if (!s || !e) {
              cb(new Error(t('mercariAccounts.errPauseBothRequired')))
              return
            }
            if (s === e) {
              cb(new Error(t('mercariAccounts.errPauseSameTime')))
              return
            }
            cb()
          },
          trigger: 'change',
        },
      ],
    }

    async function load() {
      loading.value = true
      const params = { page: page.value, page_size: pageSize.value }
      const res = await mercariAccountApi.list(params).finally(() => {
        loading.value = false
      })
      list.value = res.items || []
      total.value = res.total || 0
    }

    function openPrepareLoginBrowser() {
      openBrowserByKey(MERCARI_PREPARE_KEY, t('mercariAccounts.prepareLoginBrowserLabel'))
    }

    function openCreate() {
      form.value = createDefaultForm()
      dialogVisible.value = true
      nextTick(() => {
        openPrepareLoginBrowser()
      })
    }

    function onFetchUserInfoPlaceholder() {
      fetchSellerIdViaMitm()
    }

    function sellerIdCaptureAccountKey() {
      return form.value.id ? browserKeyFor(form.value.id) : MERCARI_PREPARE_KEY
    }

    async function fetchSellerIdViaMitm() {
      if (fetchSellerIdLoading.value) return
      const accountKey = sellerIdCaptureAccountKey()
      const label = form.value.id
        ? (form.value.account_name || t('mercariAccounts.accountFallbackLabel', { id: form.value.id }))
        : t('mercariAccounts.preLoginLabel')
      fetchSellerIdLoading.value = true
      try {
        ElMessage.info(t('mercariAccounts.tipOpeningEdge', { label }))
        const res = await mercariAccountApi.fetchSellerIdViaMitm({
          account_key: accountKey,
          headless: false,
          close_browser_after: false,
        })
        const sid = String(res?.data?.seller_id || '').trim()
        if (!sid) {
          ElMessage.warning(t('mercariAccounts.warnNoSellerIdParsed'))
          return
        }
        form.value.seller_id = sid
        await nextTick()
        formRef.value?.validateField('seller_id').catch(() => {})
        ElMessage.success(t('mercariAccounts.msgSellerIdFilled', { sid }))
      } catch {
        /* 错误由 axios 拦截器提示 */
      } finally {
        fetchSellerIdLoading.value = false
      }
    }

    function openEdit(row) {
      const open = row.is_open === 1 || row.is_open === true ? 1 : 0
      form.value = {
        ...createDefaultForm(),
        id: row.id,
        account_name: row.account_name || '',
        seller_id: row.seller_id != null ? String(row.seller_id) : '',
        status: row.status || 'active',
        remark: row.remark || '',
        is_open: open,
        fetch_interval: open === 1 ? String(row.fetch_interval != null ? row.fetch_interval : '') : '',
        auto_fetch_order_list: row.auto_fetch_order_list === 1 ? 1 : 0,
        auto_fetch_on_sale: row.auto_fetch_on_sale === 1 ? 1 : 0,
        auto_fetch_todos: row.auto_fetch_todos === 1 ? 1 : 0,
        auto_fetch_notifications: row.auto_fetch_notifications === 1 ? 1 : 0,
        auto_fetch_relist: row.auto_fetch_relist === 1 ? 1 : 0,
        pause_start_time: open === 1 ? (row.pause_start_time || null) : null,
        pause_end_time: open === 1 ? (row.pause_end_time || null) : null,
      }
      dialogVisible.value = true
    }

    function buildPayload() {
      const name = String(form.value.account_name || '').trim()
      const open = form.value.is_open === 1 ? 1 : 0
      const base = {
        account_name: name,
        login_id: name,
        seller_id: String(form.value.seller_id || '').trim() || null,
        status: form.value.status,
        remark: form.value.remark || null,
        is_open: open,
        fetch_interval: open === 1 ? String(form.value.fetch_interval || '').trim() || null : null,
        auto_fetch_order_list: open === 1 && form.value.auto_fetch_order_list === 1 ? 1 : 0,
        auto_fetch_on_sale: open === 1 && form.value.auto_fetch_on_sale === 1 ? 1 : 0,
        auto_fetch_todos: open === 1 && form.value.auto_fetch_todos === 1 ? 1 : 0,
        auto_fetch_notifications: open === 1 && form.value.auto_fetch_notifications === 1 ? 1 : 0,
        auto_fetch_relist: open === 1 && form.value.auto_fetch_relist === 1 ? 1 : 0,
        pause_start_time: open === 1 ? (String(form.value.pause_start_time || '').trim() || null) : null,
        pause_end_time: open === 1 ? (String(form.value.pause_end_time || '').trim() || null) : null,
      }
      if (form.value.id) {
        return base
      }
      return { ...base }
    }

    async function submit() {
      await formRef.value?.validate()
      submitting.value = true
      const payload = buildPayload()
      try {
        if (form.value.id) {
          await mercariAccountApi.update(form.value.id, payload)
          ElMessage.success(t('mercariAccounts.msgUpdateSuccess'))
          dialogVisible.value = false
          load()
        } else {
          await mercariAccountApi.create(payload)
          ElMessage.success(t('mercariAccounts.msgCreateSuccess'))
          dialogVisible.value = false
          await load()
        }
      } finally {
        submitting.value = false
      }
    }

    async function remove(id) {
      await mercariAccountApi.remove(id)
      ElMessage.success(t('mercariAccounts.msgDeleteSuccess'))
      if (list.value.length === 1 && page.value > 1) page.value -= 1
      load()
    }

    async function removeFromDialog() {
      if (!form.value.id) return
      const id = form.value.id
      await remove(id)
      dialogVisible.value = false
    }

    const syncingIds = ref(new Set())
    const browserLoadingKeys = ref(new Set())
    const fetchSellerIdLoading = ref(false)

    async function openBrowserByKey(accountKey, label) {
      if (browserLoadingKeys.value.has(accountKey)) return
      const next = new Set(browserLoadingKeys.value)
      next.add(accountKey)
      browserLoadingKeys.value = next
      try {
        const res = await webDriveApi.openSession({
          account_key: accountKey,
          headless: false,
          restore_tabs: true
        })
        const d = res.data || {}
        const tr = d.tab_restore || {}
        const tabHint =
          tr.restored && tr.tab_count
            ? t('mercariAccounts.tabRestoredHint', { count: tr.tab_count })
            : tr.tab_count
              ? t('mercariAccounts.tabOpenedHint', { count: tr.tab_count })
              : ''
        const tip = d.already_running
          ? t('mercariAccounts.browserAlreadyRunning', { tabHint })
          : t('mercariAccounts.browserStarted', { tabHint })
        ElMessage.success(`${label || accountKey}${t('mercariAccounts.colon')}${tip}`)
      } catch {
        /* 错误由 axios 拦截器提示 */
      } finally {
        const s = new Set(browserLoadingKeys.value)
        s.delete(accountKey)
        browserLoadingKeys.value = s
      }
    }

    function openBrowserForSavedAccount(row) {
      openBrowserByKey(browserKeyFor(row.id), row.account_name || t('mercariAccounts.accountFallbackLabel', { id: row.id }))
    }

    async function fetchHistory(row) {
      if (syncingIds.value.has(row.id)) return
      const sid = String(row.seller_id || '').trim()
      if (!sid) {
        ElMessage.warning(t('mercariAccounts.warnConfigureSellerIdFirst'))
        return
      }

      let preRes
      try {
        preRes = await mercariApi.historySyncPrecheck({ account_id: row.id })
      } catch {
        return
      }
      const pre = preRes?.data || {}
      if (!pre.allowed) {
        ElMessage.warning(pre.message || t('mercariAccounts.warnHistoryAlreadyExists'))
        return
      }

      try {
        await ElMessageBox.confirm(
          t('mercariAccounts.confirmFetchHistoryBody'),
          t('mercariAccounts.fetchHistory'),
          {
            type: 'warning',
            confirmButtonText: t('mercariAccounts.confirmFetchBtn'),
            cancelButtonText: t('common.cancel'),
            distinguishCancelAndClose: true,
          }
        )
      } catch {
        return
      }

      syncingIds.value = new Set([...syncingIds.value, row.id])
      try {
        const res = await mercariApi.syncOrders({ account_id: row.id })
        const d = res.data || {}
        ElMessage.success(
          t('mercariAccounts.msgSyncResult', {
            name: row.account_name,
            inserted: d.inserted ?? 0,
            updated: d.updated ?? 0,
            total: d.total_item_count ?? d.total ?? 0,
          })
        )
      } finally {
        const next = new Set(syncingIds.value)
        next.delete(row.id)
        syncingIds.value = next
      }
    }

    onMounted(() => {
      load()
    })

    return {
      ref,
      onMounted,
      nextTick,
      useI18n,
      Plus,
      ElMessage,
      ElMessageBox,
      mercariAccountApi,
      mercariApi,
      webDriveApi,
      t,
      MERCARI_HOME,
      MERCARI_PREPARE_KEY,
      browserKeyFor,
      loading,
      submitting,
      list,
      total,
      page,
      pageSize,
      dialogVisible,
      formRef,
      statusOptions,
      autoFetchSwitchOptions,
      fetchIntervalOptions,
      legacyFetchIntervalLabels,
      fetchIntervalLabel,
      pauseWindowLabel,
      autoFetchTasksLabel,
      onAutoFetchToggle,
      onAutoFetchTaskChange,
      createDefaultForm,
      form,
      sellerIdRules,
      formRules,
      load,
      openPrepareLoginBrowser,
      openCreate,
      onFetchUserInfoPlaceholder,
      sellerIdCaptureAccountKey,
      fetchSellerIdViaMitm,
      openEdit,
      buildPayload,
      submit,
      remove,
      removeFromDialog,
      syncingIds,
      browserLoadingKeys,
      fetchSellerIdLoading,
      openBrowserByKey,
      openBrowserForSavedAccount,
      fetchHistory,
    }
  },
})
