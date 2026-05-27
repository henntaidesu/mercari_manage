import { defineComponent, ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, EditPen, Check } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { memosApi } from '@/api/index.js'

export default defineComponent({
  components: { Search, EditPen, Check },
  setup() {
    const { t } = useI18n()

    const tab = ref('inbox')
    const keyword = ref('')
    const onlyUnread = ref(false)

    const list = ref([])
    const loading = ref(false)
    const page = ref(1)
    const pageSize = ref(20)
    const total = ref(0)
    const unread = ref(0)

    const composeVisible = ref(false)
    const submitting = ref(false)
    const composeFormRef = ref()
    const users = ref([])
    const composeForm = ref({ receiver_id: null, title: '', content: '' })
    const composeRules = {
      receiver_id: [{ required: true, message: t('memos.receiverRequired'), trigger: 'change' }],
      content: [{ required: true, message: t('memos.contentRequired'), trigger: 'blur' }],
    }

    const detailVisible = ref(false)
    const detailMemo = ref(null)

    async function refreshUnread() {
      try {
        const r = await memosApi.unreadCount()
        unread.value = r?.unread || 0
      } catch {
        // 静默
      }
    }

    async function reload(toPage) {
      if (toPage) page.value = toPage
      loading.value = true
      try {
        const params = {
          keyword: keyword.value || undefined,
          page: page.value,
          page_size: pageSize.value,
        }
        let r
        if (tab.value === 'inbox') {
          params.only_unread = onlyUnread.value || undefined
          r = await memosApi.inbox(params)
        } else {
          r = await memosApi.sent(params)
        }
        list.value = r?.items || []
        total.value = r?.total || 0
      } finally {
        loading.value = false
      }
      if (tab.value === 'inbox') refreshUnread()
    }

    function onTabChange() {
      page.value = 1
      keyword.value = ''
      onlyUnread.value = false
      reload(1)
    }

    function rowClassName({ row }) {
      if (tab.value === 'inbox' && !row.is_read) return 'memos-row-unread'
      return ''
    }

    async function setRead(row, isRead) {
      try {
        await memosApi.markRead([row.id], isRead)
        row.is_read = isRead
        row.read_at = isRead ? new Date().toISOString().replace('T', ' ').slice(0, 19) : null
        refreshUnread()
      } catch {
        // 错误已被 axios 拦截器提示
      }
    }

    async function onRowClick(row) {
      openDetail(row)
    }

    function openDetail(row) {
      detailMemo.value = row
      detailVisible.value = true
      if (tab.value === 'inbox' && !row.is_read) {
        setRead(row, true)
      }
    }

    async function markAllRead() {
      try {
        await memosApi.markAllRead()
        ElMessage.success(t('common.success'))
        reload()
      } catch {
        // ignore
      }
    }

    async function remove(id) {
      try {
        await memosApi.remove(id)
        ElMessage.success(t('common.success'))
        if (list.value.length === 1 && page.value > 1) page.value -= 1
        reload()
      } catch {
        // ignore
      }
    }

    async function openComposeDialog() {
      if (!users.value.length) {
        try {
          users.value = await memosApi.users()
        } catch {
          users.value = []
        }
      }
      composeForm.value = { receiver_id: null, title: '', content: '' }
      composeVisible.value = true
    }

    async function submitCompose() {
      await composeFormRef.value.validate()
      submitting.value = true
      try {
        await memosApi.create({
          receiver_id: composeForm.value.receiver_id,
          title: composeForm.value.title?.trim() || null,
          content: composeForm.value.content,
        })
        ElMessage.success(t('memos.sentSuccess'))
        composeVisible.value = false
        if (tab.value === 'sent') reload()
      } finally {
        submitting.value = false
      }
    }

    onMounted(() => {
      reload(1)
      refreshUnread()
    })

    return {
      t,
      tab,
      keyword,
      onlyUnread,
      list,
      loading,
      page,
      pageSize,
      total,
      unread,
      composeVisible,
      submitting,
      composeFormRef,
      users,
      composeForm,
      composeRules,
      detailVisible,
      detailMemo,
      reload,
      onTabChange,
      rowClassName,
      onRowClick,
      openDetail,
      setRead,
      markAllRead,
      remove,
      openComposeDialog,
      submitCompose,
    }
  },
})
