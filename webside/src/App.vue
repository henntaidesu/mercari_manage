<template>
  <router-view />
</template>

<script setup>
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root.dark {
  color-scheme: dark;
}

/* 与暗色主题对齐：避免统计卡片、表格卡片出现浅色底 / 白屏 loading */
html.dark {
  --el-bg-color: #0b1220;
  --el-bg-color-page: #0b1220;
  --el-fill-color-blank: #131c2f;
  --el-fill-color-light: #18233a;
  --el-mask-color: rgba(11, 18, 32, 0.78);
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: #0b1220;
  color: #e5e7eb;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-thumb {
  background: #3a4456;
  border-radius: 3px;
}
::-webkit-scrollbar-track {
  background: transparent;
}

.page-title {
  color: #e6edf7 !important;
}

.el-card,
.el-dialog,
.el-table,
.el-input__wrapper,
.el-select__wrapper,
.el-textarea__inner {
  border-color: #2a3446 !important;
}

.el-card {
  background: #131c2f !important;
  color: #e6edf7;
}

.el-card__header {
  background: #161f33 !important;
  border-bottom: 1px solid #28354a !important;
  color: #e6edf7 !important;
}

.el-card__body {
  background: transparent !important;
  color: #e6edf7;
}

.el-loading-mask {
  background-color: var(--el-mask-color) !important;
}

.el-loading-mask .el-loading-spinner .path {
  stroke: #8fb8ff;
}

.el-table {
  --el-table-header-bg-color: #18233a;
  --el-table-tr-bg-color: #131c2f;
  --el-table-row-hover-bg-color: #1b2942;
  --el-table-border-color: #28354a;
  color: #d6deea;
}

.el-dialog {
  --el-dialog-bg-color: #131c2f;
}

.el-input,
.el-select,
.el-date-editor.el-input__wrapper,
.el-date-editor.el-input {
  width: 180px !important;
}

.el-range-editor.el-input__wrapper,
.el-date-editor--daterange {
  width: 180px !important;
  min-width: 180px !important;
}
</style>
