<template>
  <teleport to="body">
    <div
      v-show="state.visible"
      class="sync-overlay sync-overlay--dark"
      :class="{ 'sync-overlay--failed': state.failed }"
      role="status"
      aria-live="polite"
    >
      <div class="sync-overlay__box">
        <el-icon class="is-loading sync-overlay__icon" :size="40"><Loading /></el-icon>
        <div class="sync-overlay__title">{{ state.title }}</div>
        <div class="sync-overlay__step">{{ state.label || t('sync.pleaseWait') }}</div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { Loading } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  state: { type: Object, required: true },
})
</script>

<style>
.sync-overlay.sync-overlay--dark {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
}
.sync-overlay--dark .sync-overlay__box {
  min-width: 280px;
  max-width: min(440px, 92vw);
  padding: 28px 32px;
  background: linear-gradient(165deg, #1c1c1f 0%, #121214 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  text-align: center;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.04) inset,
    0 20px 50px rgba(0, 0, 0, 0.65);
}
.sync-overlay--dark .sync-overlay__icon {
  color: #94a3b8;
}
.sync-overlay--dark .sync-overlay__title {
  margin-top: 14px;
  font-size: 17px;
  font-weight: 600;
  color: #f1f5f9;
  letter-spacing: 0.02em;
}
.sync-overlay--dark.sync-overlay--failed .sync-overlay__title {
  color: #f87171;
}
.sync-overlay--dark.sync-overlay--failed .sync-overlay__step {
  color: #cbd5e1;
}
.sync-overlay--dark .sync-overlay__step {
  margin-top: 10px;
  font-size: 14px;
  color: #94a3b8;
  line-height: 1.55;
  word-break: break-word;
}
</style>
