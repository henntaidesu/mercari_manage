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
