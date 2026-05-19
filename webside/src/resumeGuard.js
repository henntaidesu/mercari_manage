/**
 * 手机端从其他 App / 网页切回时，避免开发环境 HMR 重连等触发的整页刷新。
 * 须在 Vite client 之前加载（见 vite.config.js 的 index 注入）；main.js 也会再次 import（幂等）。
 */

const RESUME_GUARD_MS = 90_000
const GUARD_KEY = '__mercariResumeGuardInstalled'

function isMobileLike() {
  if (typeof window === 'undefined') return false
  try {
    if (window.matchMedia('(max-width: 768px)').matches) return true
  } catch {
    /* ignore */
  }
  return Number(navigator.maxTouchPoints || 0) > 0
}

function createState() {
  return {
    hiddenAt: 0,
    guardUntil: 0,
    mobile: isMobileLike()
  }
}

const state = typeof window !== 'undefined' ? createState() : null

function armGuard() {
  if (!state?.mobile) return
  state.hiddenAt = Date.now()
  state.guardUntil = state.hiddenAt + RESUME_GUARD_MS
}

function shouldSuppressReload() {
  if (!state?.mobile) return false
  return state.guardUntil > 0 && Date.now() < state.guardUntil
}

/** 业务层若在 visibilitychange 里拉数，可先判断此函数 */
export function shouldSkipAutoRefreshOnResume() {
  return shouldSuppressReload()
}

function patchLocationReload() {
  if (!state || state.mobile === false) return
  const proto = window.Location?.prototype
  const orig =
    (proto && typeof proto.reload === 'function' && proto.reload) ||
    (typeof window.location.reload === 'function' && window.location.reload.bind(window.location))
  if (!orig) return

  const wrapped = function mercariGuardedReload(...args) {
    if (shouldSuppressReload()) {
      console.info('[mercari] 已阻止切回前台后的自动整页刷新')
      return
    }
    return orig.apply(this, args)
  }

  if (proto) proto.reload = wrapped
  try {
    window.location.reload = wrapped
  } catch {
    /* 部分环境 location.reload 不可写 */
  }
}

function bindLifecycle() {
  if (!state) return

  document.addEventListener(
    'visibilitychange',
    () => {
      if (document.visibilityState === 'hidden') armGuard()
    },
    { capture: true }
  )

  window.addEventListener(
    'pagehide',
    () => {
      armGuard()
    },
    { capture: true }
  )

  window.addEventListener('pageshow', (ev) => {
    if (ev.persisted) armGuard()
  })
}

function bindViteHmr() {
  if (!import.meta.hot) return
  import.meta.hot.on('vite:beforeFullReload', () => {
    if (shouldSuppressReload()) {
      console.info('[mercari] 已忽略切回前台后的 Vite 整页热更新')
    }
  })
}

export function installResumeGuard() {
  if (typeof window === 'undefined' || window[GUARD_KEY]) return
  window[GUARD_KEY] = true
  patchLocationReload()
  bindLifecycle()
  bindViteHmr()
}

installResumeGuard()
