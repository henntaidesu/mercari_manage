<template>
  <div :class="{ 'listing-pick-mode-active': listingPickMode }">
    <!-- 库存统计卡片（全库汇总）；手机端不展示 -->
    <el-card v-if="!isMobile" class="section-card inventory-stats-wrap" shadow="never">
      <el-row :gutter="16" class="stat-row inventory-stat-row">
        <el-col :xs="12" :sm="12" :md="8" :lg="4" v-for="card in inventoryStatCards" :key="card.label">
          <div class="inv-stat-card" :style="{ borderTopColor: card.color }">
            <div class="inv-stat-icon" :style="{ background: card.color + '20', color: card.color }">
              <el-icon size="22"><component :is="card.icon" /></el-icon>
            </div>
            <div class="inv-stat-info">
              <div class="inv-stat-value">{{ inventorySummary[card.key] ?? '-' }}</div>
              <div class="inv-stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="search-card">
      <el-row :gutter="0" align="middle" class="search-row">
        <el-col :xs="24" :md="14" class="search-left-group">
          <el-input v-model="keyword" class="search-input-control" placeholder="搜索商品名称" clearable @change="load" prefix-icon="Search" />
          <div class="search-filters-row">
            <el-select v-model="filterCat" class="search-select-control" placeholder="所有游戏分类" clearable @change="load">
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select v-model="filterWarehouse" class="search-select-control" placeholder="所有仓库" clearable @change="load">
              <el-option v-for="w in warehouses" :key="w.id" :label="warehouseShelfLabel(w)" :value="w.id" />
            </el-select>
            <el-cascader
              v-model="filterProductTypePath"
              :options="productTypeCascaderOptions"
              :props="productTypeCascaderProps"
              :show-all-levels="false"
              class="search-select-control"
              placeholder="商品类型"
              popper-class="product-type-cascader-popper"
              clearable
              filterable
              @change="handleFilterProductTypeChange"
            />
            <el-select v-model="filterOwnerUserId" class="search-select-control" placeholder="所有商品归属" clearable @change="load">
              <el-option v-for="u in ownerUsers" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
            </el-select>
          </div>
        </el-col>
        <el-col :xs="24" :md="10" class="search-actions" :class="{ 'search-actions--ios': isIOS }">
          <template v-if="isIOS">
            <template v-if="!listingPickMode">
              <div class="search-actions-ios-row">
                <el-button type="success" @click="openContScan">条码入库</el-button>
              </div>
              <div class="search-actions-ios-row">
                <el-button type="warning" @click="openNoBarcodeEntry">无码入库</el-button>
                <el-button @click="enterListingPickMode()">组合出品</el-button>
              </div>
            </template>
            <template v-else>
              <div class="search-actions-ios-row listing-pick-actions">
                <span class="listing-pick-count">已选 {{ listingPickIds.size }} 条</span>
                <el-button type="primary" :disabled="!listingPickIds.size" @click="confirmListingPick">下一步</el-button>
                <el-button @click="exitListingPickMode">取消选择</el-button>
              </div>
            </template>
          </template>
          <template v-else>
            <template v-if="!listingPickMode">
              <el-button type="success" @click="openContScan">条码入库</el-button>
              <el-button type="warning" @click="openNoBarcodeEntry">无码入库</el-button>
              <el-button @click="enterListingPickMode()">组合出品</el-button>
            </template>
            <template v-else>
              <span class="listing-pick-count">已选 {{ listingPickIds.size }} 条</span>
              <el-button type="primary" :disabled="!listingPickIds.size" @click="confirmListingPick">下一步：填写出品表单</el-button>
              <el-button @click="exitListingPickMode">取消选择</el-button>
            </template>
          </template>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-scroll">
      <el-table
        :data="pagedList"
        v-loading="loading"
        stripe
        row-key="id"
        :size="isMobile ? 'small' : 'default'"
        :row-class-name="rowClassName"
        @sort-change="onInventorySortChange"
        @expand-change="onInventoryExpandChange"
        @row-click="onTableRowClick"
      >
        <el-table-column type="expand" width="44">
          <template #default="{ row }">
            <div class="inventory-expand-wrap" v-loading="getInventoryExpandSlot(row.id)?.loading">
              <el-table
                v-if="mercariItemIds(row).length"
                :data="getInventoryExpandRows(row)"
                size="small"
                border
                class="inventory-expand-inner-table"
                empty-text="暂无在售商品数据"
              >
                <el-table-column label="商品ID" prop="item_id" min-width="130" align="center" />
                <el-table-column label="标题" prop="name" min-width="220" align="left" show-overflow-tooltip />
                <el-table-column label="卖家" prop="seller_name" min-width="120" align="center" show-overflow-tooltip />
                <el-table-column label="价格¥" width="90" align="center">
                  <template #default="{ row: r }">{{ Number(r.price || 0) }}</template>
                </el-table-column>
                <el-table-column label="状态" width="110" align="center">
                  <template #default="{ row: r }">
                    <el-tag :type="onSaleStatusTagType(r.status)" size="small" effect="light">
                      {{ displayOnSaleStatus(r.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="在售数量" width="90" align="center">
                  <template #default="{ row: r }">{{ Number(r.inventory_on_sale_quantity ?? 0) }}</template>
                </el-table-column>
                <el-table-column label="更新" width="150" align="center">
                  <template #default="{ row: r }">{{ formatUnixTs(r.updated) }}</template>
                </el-table-column>
              </el-table>
              <el-empty v-else description="暂无煤炉商品ID" :image-size="48" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="管理番号" prop="id" width="100" align="center" header-align="center" />
        <el-table-column label="正面图" width="76" align="center" header-align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.image_front || row.image"
              class="order-thumb"
              :src="thumbUrl(row.image_front || row.image)"
              :preview-src-list="[row.image_front || row.image]"
              :hide-on-click-modal="true"
              :preview-teleported="true"
              :z-index="4000"
              fit="cover"
              referrerpolicy="no-referrer"
              lazy
            >
              <template #error>
                <span class="thumb-fallback">-</span>
              </template>
            </el-image>
            <span v-else class="thumb-fallback">-</span>
          </template>
        </el-table-column>
        <el-table-column label="背面图" width="76" align="center" header-align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.image_back"
              class="order-thumb"
              :src="thumbUrl(row.image_back)"
              :preview-src-list="[row.image_back]"
              :hide-on-click-modal="true"
              :preview-teleported="true"
              :z-index="4000"
              fit="cover"
              referrerpolicy="no-referrer"
              lazy
            >
              <template #error>
                <span class="thumb-fallback">-</span>
              </template>
            </el-image>
            <span v-else class="thumb-fallback">-</span>
          </template>
        </el-table-column>
        <el-table-column label="条形码" prop="barcode" min-width="150" align="left" header-align="left" />
        <el-table-column label="商品名称" min-width="130" align="left" header-align="left">
          <template #default="{ row }">
            <el-input
              v-if="isEditing(row, 'name')"
              v-model="editingValue"
              size="small"
              class="inline-input"
              @keyup.enter="saveInlineEdit(row, 'name')"
              @blur="saveInlineEdit(row, 'name')"
            />
            <div v-else class="editable-cell" @click="startInlineEdit(row, 'name')">{{ row.name || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="游戏分类" width="120" align="center" header-align="center">
          <template #default="{ row }">
            <el-select
              v-if="editingCategoryRowId === row.id"
              :model-value="row.category_id"
              size="small"
              style="width: 100%"
              placeholder="选择分类"
              @change="saveCategoryInline(row, $event)"
              @visible-change="(v) => { if (!v) editingCategoryRowId = null }"
            >
              <el-option label="未分类" :value="null" />
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <div v-else class="editable-cell" @click="!listingPickMode && (editingCategoryRowId = row.id)">{{ row.category_name || '未分类' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="商品类型" width="120" align="center" header-align="center">
          <template #default="{ row }">
            <el-cascader
              v-if="editingProductTypeRowId === row.id"
              :model-value="getInlineProductTypePath(row)"
              :options="productTypeCascaderOptions"
              :props="productTypeCascaderProps"
              :show-all-levels="false"
              size="small"
              class="inventory-inline-select"
              placeholder="选择类型"
              popper-class="product-type-cascader-popper"
              filterable
              clearable
              @change="saveProductTypeInline(row, $event)"
              @visible-change="(v) => { if (!v) editingProductTypeRowId = null }"
            />
            <div v-else class="editable-cell" @click="openProductTypeInline(row)">{{ displayProductTypeName(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="商品归属" width="120" align="center" header-align="center">
          <template #default="{ row }">
            <el-select
              v-if="editingOwnerRowId === row.id"
              :model-value="row.owner_user_id"
              :ref="(el) => setInlineOwnerSelectRef(row.id, el)"
              size="small"
              class="inventory-inline-select"
              placeholder="选择归属"
              popper-class="inventory-inline-select-popper"
              @change="saveOwnerInline(row, $event)"
              @visible-change="(v) => { if (!v) editingOwnerRowId = null }"
            >
              <el-option label="" :value="null" />
              <el-option v-for="u in ownerUsers" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
            </el-select>
            <div v-else class="editable-cell" @click="openOwnerInline(row)">{{ displayOwnerName(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="所属仓库" min-width="100" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.inv_wh_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="所属货架" min-width="100" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.inv_shelf_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="货架号码" min-width="100" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.inv_shelf_code || '-' }}</template>
        </el-table-column>
        <el-table-column label="单价" prop="price" width="120" align="center" header-align="center" sortable="custom">
          <template #default="{ row }">
            {{ Math.round(Number(row.price || 0)) }}
          </template>
        </el-table-column>
        <el-table-column label="库存" prop="quantity" width="80" align="center" header-align="center" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="quantityTagType(row.quantity)" size="small">
              {{ row.quantity || 0 }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="在售" prop="on_sale_quantity" width="80" align="center" header-align="center" sortable="custom">
          <template #default="{ row }">{{ Number(row.on_sale_quantity ?? 0) }}</template>
        </el-table-column>
        <el-table-column label="待出" prop="pending_outbound_qty" width="80" align="center" header-align="center" sortable="custom">
          <template #default="{ row }">
            <el-tag v-if="Number(row.pending_outbound_qty || 0) > 0" type="warning" size="small">
              {{ Number(row.pending_outbound_qty || 0) }}
            </el-tag>
            <span v-else class="cell-muted">{{ Number(row.pending_outbound_qty || 0) }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="!listingPickMode" label="操作" :width="isMobile ? 140 : 160" align="center" header-align="center" :fixed="isMobile ? false : 'right'">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button
                size="small"
                type="warning"
                :disabled="Number(row.quantity ?? 0) <= 0"
                @click.stop="openListingFormForRow(row)"
              >出品</el-button>
              <el-button size="small" @click.stop="openDialog(row)">编辑</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-else label="选择" width="64" align="center" header-align="center" :fixed="isMobile ? false : 'right'">
          <template #default="{ row }">
            <el-icon v-if="listingPickIds.has(row.id)" color="#67C23A" :size="20"><Check /></el-icon>
            <span v-else class="cell-muted">-</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="list.length"
          :pager-count="5"
        />
      </div>
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑商品' : '新增商品'"
      :width="isMobile ? '94vw' : '580px'"
      class="product-dialog"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef">
        <!-- 条形码行 -->
        <el-form-item prop="barcode">
          <el-input
            v-model="form.barcode"
            placeholder="条形码（必填）"
            size="large"
            clearable
            :disabled="Boolean(form.id)"
          >
            <template #append>
              <el-button @click="openScanDialog">
                <el-icon><Camera /></el-icon> 扫码
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="商品名称">
          <el-input v-model="form.name" class="listing-field-fullwidth" type="text" clearable />
        </el-form-item>
        <el-form-item label="游戏分类" prop="category_id">
          <div class="product-field-inline">
            <template v-if="!categoryCreateMode">
              <el-select
                v-model="form.category_id"
                clearable
                :filterable="!isIOS"
                placeholder="请选择分类"
                class="product-field-inline__main"
              >
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
              <el-button type="primary" plain @click="startCreateCategory">新建分类</el-button>
            </template>
            <template v-else>
              <el-input
                v-model="newCategoryName"
                placeholder="输入新分类名称"
                clearable
                class="product-field-inline__main"
                @keyup.enter="confirmCreateCategory"
              />
              <el-button type="primary" @click="confirmCreateCategory">确认</el-button>
              <el-button @click="cancelCreateCategory">取消</el-button>
            </template>
          </div>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :xs="24" :sm="16">
            <el-form-item label="商品类型" prop="product_type_id">
              <el-cascader
                v-model="productTypeCascaderPath"
                :options="productTypeCascaderOptions"
                :props="productTypeCascaderProps"
                :show-all-levels="false"
                clearable
                filterable
                placeholder="请选择商品类型（按1/2/3级分类）"
                class="product-field-inline__main"
                style="width: 100%"
                popper-class="product-type-cascader-popper"
                @change="handleProductTypeCascaderChange"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="单价" prop="price">
              <el-input
                v-model="priceEdit"
                placeholder="整数"
                class="product-price-input"
                inputmode="numeric"
                @blur="applyPriceEditToForm"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="商品归属" prop="owner_user_id">
          <el-select
            v-model="form.owner_user_id"
            clearable
            :filterable="!isIOS"
            placeholder="请选择归属用户"
            class="product-field-inline__main"
          >
            <el-option v-for="u in ownerUsers" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :xs="24" :sm="16">
            <el-form-item label="所属仓库" prop="warehouse_id">
              <div class="product-field-inline">
                <template v-if="!warehouseCreateMode">
                  <el-select
                    v-model="form.warehouse_id"
                    clearable
                    :filterable="!isIOS"
                    placeholder="请选择仓库"
                    class="product-field-inline__main"
                  >
                    <el-option v-for="w in warehouses" :key="w.id" :label="warehouseShelfLabel(w)" :value="w.id" />
                  </el-select>
                  <el-button type="primary" plain @click="startCreateWarehouse">新建仓库</el-button>
                </template>
                <template v-else>
                  <el-input
                    v-model="newWarehouseName"
                    placeholder="输入新仓库名称"
                    clearable
                    class="product-field-inline__main"
                    @keyup.enter="confirmCreateWarehouse"
                  />
                  <el-button type="primary" @click="confirmCreateWarehouse">确认</el-button>
                  <el-button @click="cancelCreateWarehouse">取消</el-button>
                </template>
              </div>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="库存数量" prop="quantity">
              <el-input
                v-model="quantityEdit"
                placeholder=""
                class="product-qty-input"
                inputmode="numeric"
                @blur="applyQuantityEditToForm"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <!-- 正面图 / 背面图 -->
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item prop="image_front" style="display:block">
              <div class="img-label">正面图</div>
              <div class="image-upload-area large" @click="triggerUpload('front')">
                <img v-if="form.image_front" :src="form.image_front" class="preview-img" />
                <div v-else class="upload-placeholder">
                  <el-icon size="36" color="#4a5a72"><Camera /></el-icon>
                  <div class="upload-tip">点击上传正面图</div>
                </div>
              </div>
              <input ref="fileInputFront" type="file" accept="image/*" capture="environment" style="display:none" @change="handleImageUpload($event, 'front')" />
              <div class="img-actions">
                <el-button v-if="form.image_front" size="small" type="danger" text @click="form.image_front = null">移除</el-button>
                <el-button v-if="form.image_front" size="small" type="primary" text @click="openOcr('front')">OCR识别名称</el-button>
              </div>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item style="display:block">
              <div class="img-label">背面图（选填）</div>
              <div class="image-upload-area large" @click="triggerUpload('back')">
                <img v-if="form.image_back" :src="form.image_back" class="preview-img" />
                <div v-else class="upload-placeholder">
                  <el-icon size="36" color="#4a5a72"><Camera /></el-icon>
                  <div class="upload-tip">点击上传背面图</div>
                </div>
              </div>
              <input ref="fileInputBack" type="file" accept="image/*" capture="environment" style="display:none" @change="handleImageUpload($event, 'back')" />
              <div class="img-actions">
                <el-button v-if="form.image_back" size="small" type="danger" text @click="form.image_back = null">移除</el-button>
                <el-button v-if="form.image_back" size="small" type="primary" text @click="openOcr('back')">OCR识别名称</el-button>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="出品标题">
          <el-input v-model="form.listing_title" class="listing-field-fullwidth" type="text" clearable />
        </el-form-item>
        <el-form-item label="商品说明">
          <el-input
            v-model="form.listing_body"
            class="listing-field-fullwidth"
            type="textarea"
            :rows="5"
            clearable
          />
        </el-form-item>
        <template v-if="form.id">
          <el-form-item label="煤炉商品ID">
            <div class="mercari-id-editor">
              <div v-for="(_, idx) in mercariIdList" :key="idx" class="mercari-id-row">
                <el-input
                  v-model="mercariIdList[idx]"
                  size="small"
                  placeholder="输入商品ID"
                  class="mercari-id-input"
                  clearable
                />
                <el-button size="small" type="danger" text @click="removeMercariId(idx)">删除</el-button>
              </div>
              <el-button size="small" type="primary" plain @click="addMercariId">+ 添加商品ID</el-button>
            </div>
          </el-form-item>
          <el-form-item label="在售数量">
            <el-input-number v-model="form.on_sale_quantity" :min="0" :max="999999" :step="1" controls-position="right" style="width: 160px" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <div class="product-dialog-footer">
          <div class="product-dialog-footer__left">
            <template v-if="form.id">
              <el-button type="success" @click="openOcrForRow(form)">OCR</el-button>
              <el-popconfirm title="确认删除该商品？" @confirm="remove(form.id); dialogVisible = false">
                <template #reference>
                  <el-button type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </div>
          <div class="product-dialog-footer__right">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="submit" :loading="submitting">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <SingleListingFormDialog
      v-model="listingDialogVisible"
      :category-mappings="listingCategoryMappings"
      :initial-data="listingSeedData"
      :is-mobile="isMobile"
      @saved="onListingFormSaved"
    />
    <CombinedListingFormDialog
      v-model="combinedListingDialogVisible"
      :category-mappings="listingCategoryMappings"
      :initial-data="combinedListingSeedData"
      :is-mobile="isMobile"
      @saved="onListingFormSaved"
    />

    <el-dialog
      v-model="scanVisible"
      title="摄像头扫描条形码"
      :width="isMobile ? '94vw' : '640px'"
      class="scan-dialog"
      @closed="stopScan"
    >
      <div class="scan-box">
        <video ref="videoRef" class="scan-video" autoplay playsinline muted />
        <div class="scan-tip">
          <span v-if="scanning" class="scanning-hint">识别中…</span>
          <span v-else>请将条形码置于画面中央，识别后会自动填充</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="scanVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 拍照扫码降级方案（iOS Safari / 非安全上下文）-->
    <input
      ref="cameraInputRef"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handleCameraCapture"
    />

    <!-- ===== 连续扫码对话框 ===== -->
    <el-dialog
      v-model="contScanVisible"
      title="条码入库"
      :width="isMobile ? '94vw' : '580px'"
      class="scan-dialog"
      @closed="stopContScan"
    >
      <!-- 扫码中：显示摄像头（多摄像头时可选设备，选择会记住到本机） -->
      <div v-show="contState === 'scanning'" class="scan-box">
        <div v-if="inventoryCameraDevices.length > 1" class="camera-device-row">
          <span class="camera-device-label">摄像头</span>
          <el-select
            v-model="inventoryCameraSelectId"
            filterable
            placeholder="选择摄像头"
            class="camera-device-select"
            @change="onContCameraDeviceChanged"
          >
            <el-option
              v-for="d in inventoryCameraDevices"
              :key="d.deviceId"
              :label="d.label"
              :value="d.deviceId"
            />
          </el-select>
        </div>
        <video ref="contVideoRef" class="scan-video" autoplay playsinline muted />
        <div class="scan-tip">
          <span v-if="contScanning" class="scanning-hint">识别中…</span>
          <span v-else>将条形码对准摄像头，自动识别</span>
        </div>
      </div>

      <!-- iOS / HTTP 降级：拍照按钮 -->
      <div v-if="contState === 'ios-fallback'" class="ios-fallback-box">
        <el-icon size="50" color="#4a5a72"><Camera /></el-icon>
        <p style="color:#8e9bb3;margin:12px 0">当前环境无法在网页内直接预览摄像头连续扫码。</p>
        <p v-if="contScanNeedsHttpsHint" class="cont-https-hint">
          您正在使用 <strong>HTTP</strong> 访问：Chrome / Edge 不会向页面开放摄像头接口，因此会出现系统「打开文件」对话框。
          请改用 <strong>https://</strong> 打开本站（开发环境运行 <code>npm run dev</code> 已默认开启 HTTPS），首次需在浏览器里信任自签名证书，即可在弹窗内选择摄像头并扫码入库。
        </p>
        <p style="color:#8e9bb3;margin:12px 0">也可点击下方，从相册或相机拍摄条形码图片进行识别。</p>
        <el-button type="primary" @click="triggerContCapture">拍照 / 选图识别</el-button>
      </div>

      <!-- 找到商品（须同时有 contProduct，避免二次入库时 contState 仍为 found 但 product 已清空导致渲染报错、弹窗空白） -->
      <div v-if="contState === 'found' && contProduct" class="cont-result">
        <div class="barcode-tag">
          <el-icon><Tickets /></el-icon>
          <span>{{ contBarcode }}</span>
        </div>
        <div class="product-images-row">
          <div v-if="contProduct.image_front" class="result-img-wrap">
            <span class="img-side-label">正面</span>
            <img :src="contProduct.image_front" class="result-img" />
          </div>
          <div v-if="contProduct.image_back" class="result-img-wrap">
            <span class="img-side-label">背面</span>
            <img :src="contProduct.image_back" class="result-img" />
          </div>
          <div v-if="!contProduct.image_front && !contProduct.image_back" class="no-image-placeholder">
            <el-icon size="40" color="#4a5a72"><Picture /></el-icon>
            <p>暂无图片</p>
          </div>
        </div>
        <div class="product-meta">
          <span class="product-meta-name">{{ contProduct.name || '(未命名)' }}</span>
          <el-tag type="info" size="small">当前库存 {{ contProduct.quantity ?? 0 }} 件</el-tag>
          <el-tag size="small" effect="plain">所属仓库 {{ contProduct.warehouse_name || '未设置' }}</el-tag>
        </div>
        <div class="cont-quantity-row">
          <span class="cont-quantity-label">本次数量</span>
          <el-input-number v-model="contQuantity" :min="1" :max="9999" :step="1" controls-position="right" />
        </div>
        <div class="cont-actions">
          <el-button @click="resumeContScan">继续扫码</el-button>
          <el-button type="primary" size="large" :loading="contConfirming" @click="confirmContAction">
            确认入库 +{{ contQuantity }}
          </el-button>
        </div>
      </div>

      <!-- 未找到商品 -->
      <div v-if="contState === 'notfound'" class="cont-result">
        <div class="barcode-tag">
          <el-icon><Tickets /></el-icon>
          <span>{{ contBarcode }}</span>
        </div>
        <div class="notfound-box">
          <el-icon size="44" color="#e6a23c"><Warning /></el-icon>
          <p>该条形码尚未登记商品</p>
        </div>
        <div class="cont-actions">
          <el-button @click="resumeContScan">继续扫码</el-button>
          <el-button type="primary" @click="openAddFromScan">新增商品</el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="contScanVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 双 input 轮换：iOS 上同一 file 连续拍照/选图时 change 可能不触发，换节点可稳定再次唤起 -->
    <input
      ref="contCameraRefA"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handleContCapture"
    />
    <input
      ref="contCameraRefB"
      type="file"
      accept="image/*"
      capture="environment"
      style="display:none"
      @change="handleContCapture"
    />
    <!-- ===== OCR 框选弹窗 ===== -->
    <el-dialog
      v-model="ocrVisible"
      title="框选文字区域 → OCR识别名称"
      :width="isMobile ? '96vw' : '700px'"
      class="ocr-dialog"
      destroy-on-close
      @opened="initOcrCanvas"
    >
      <div v-if="ocrTargetRow" class="ocr-img-tabs">
        <el-button
          :type="ocrSide === 'front' ? 'primary' : 'default'"
          size="small"
          @click="switchOcrSide('front')"
          :disabled="!getOcrSrc('front')"
        >正面图</el-button>
        <el-button
          :type="ocrSide === 'back' ? 'primary' : 'default'"
          size="small"
          @click="switchOcrSide('back')"
          :disabled="!getOcrSrc('back')"
        >背面图</el-button>
      </div>
      <p class="ocr-hint">在图片上拖动框选要识别的文字区域，松手后自动识别写入商品名称</p>
      <div class="ocr-canvas-wrap" ref="ocrWrapRef">
        <canvas
          ref="ocrCanvasRef"
          class="ocr-canvas"
          @mousedown.prevent="ocrDragStart"
          @mousemove.prevent="ocrDragMove"
          @mouseup.prevent="ocrDragEnd"
          @mouseleave.prevent="ocrDragEnd"
          @touchstart.prevent="ocrDragStart"
          @touchmove.prevent="ocrDragMove"
          @touchend.prevent="ocrDragEnd"
        />
      </div>
      <div v-if="ocrLoading" class="ocr-loading">
        <span class="scanning-hint">识别中，请稍候…</span>
      </div>
      <template #footer>
        <el-button @click="ocrVisible = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { inventoryApi, categoryApi, warehouseApi, authApi, scanApi, ocrApi, transactionApi, productTypeCategoryMappingApi, onSaleItemApi, listingApi } from '@/api/index.js'
import { warehouseShelfLabel } from '@/utils/warehouseLabel.js'
import SingleListingFormDialog from '@/components/SingleListingFormDialog.vue'
import CombinedListingFormDialog from '@/components/CombinedListingFormDialog.vue'

const list = ref([])
const loading = ref(false)
/** 表头排序：custom 模式，在 sortedList 中处理 */
const inventorySortProp = ref('')
const inventorySortOrder = ref('') // 'ascending' | 'descending' | ''

const inventorySummary = ref({})
const inventoryStatCards = [
  { key: 'total_inventory', label: '库存条目', icon: 'Goods', color: '#409EFF' },
  { key: 'total_quantity', label: '总库存量', icon: 'Box', color: '#E6A23C' },
  { key: 'today_in', label: '今日入库', icon: 'Top', color: '#67C23A' },
  { key: 'today_out', label: '今日出库', icon: 'Bottom', color: '#F56C6C' },
]
const onSaleStatusMap = {
  on_sale: { label: '出售中', tag: 'success' },
  stop: { label: '暂停出售', tag: 'warning' },
  trading: { label: '交易中', tag: 'primary' },
  wait_payment: { label: '待支付', tag: 'warning' },
  wait_shipping: { label: '待发货', tag: 'warning' },
  wait_review: { label: '待评价', tag: 'primary' },
  sold_out: { label: '已售完', tag: 'info' },
  done: { label: '已完成', tag: 'success' },
  cancelled: { label: '已取消', tag: 'info' },
  cancel_request: { label: '取消申请中', tag: 'danger' },
  deleted: { label: '已删除', tag: 'danger' },
  private: { label: '非公开', tag: 'info' },
  pending: { label: '待处理', tag: 'info' },
}
const categories = ref([])
const warehouses = ref([])
const productTypes = ref([])
const ownerUsers = ref([])
const keyword = ref('')
const filterCat = ref(null)
const filterWarehouse = ref(null)
const filterProductType = ref(null)
const filterProductTypePath = ref([])
const filterOwnerUserId = ref(null)
const currentPage = ref(1)
const pageSize = 15
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const fileInputFront = ref()
const fileInputBack = ref()
const listingDialogVisible = ref(false)
const listingSeedData = ref(null)
/** 组合出品独立弹窗 */
const combinedListingDialogVisible = ref(false)
const combinedListingSeedData = ref(null)
/** 组合出品「在列表中选择」模式 */
const listingPickMode = ref(false)
/** 已选中的库存 id 集合 */
const listingPickIds = ref(new Set())
const listingCategoryMappings = ref([])
const productTypeCascaderPath = ref([])
const inventoryExpandById = ref({})
const scanVisible = ref(false)
const scanning = ref(false)
const videoRef = ref()
const cameraInputRef = ref()
const isMobile = ref(false)
const isIOS = ref(false)
const editingCell = ref('')
const editingValue = ref('')
const savingInlineCell = ref('')
const editingCategoryRowId = ref(null)
const editingProductTypeRowId = ref(null)
const editingOwnerRowId = ref(null)
const inlineOwnerSelectMap = new Map()
const newCategoryName = ref('')
const newWarehouseName = ref('')
/** 编辑弹窗：新建分类 / 仓库时，下拉与输入框同位切换 */
const categoryCreateMode = ref(false)
const warehouseCreateMode = ref(false)
/** 编辑弹窗库存数量：纯文本输入，blur / 保存时写回 form.quantity */
const quantityEdit = ref('0')
/** 编辑弹窗单价：纯文本整数，blur / 保存时写回 form.price */
const priceEdit = ref('0')

/** 编辑弹窗：煤炉商品ID 列表（一对多） */
const mercariIdList = ref([])

function syncQuantityEditFromForm() {
  quantityEdit.value = String(form.value.quantity ?? 0)
}

function applyQuantityEditToForm() {
  const raw = String(quantityEdit.value ?? '').trim()
  const n = parseInt(raw, 10)
  const v = Number.isNaN(n) ? 0 : Math.max(0, n)
  form.value.quantity = v
  quantityEdit.value = String(v)
}

function syncPriceEditFromForm() {
  priceEdit.value = String(Math.round(Number(form.value.price ?? 0)))
}

function applyPriceEditToForm() {
  const raw = String(priceEdit.value ?? '').trim()
  const n = parseInt(raw, 10)
  const v = Number.isNaN(n) ? 0 : Math.max(0, Math.min(999999999, n))
  form.value.price = v
  priceEdit.value = String(v)
}

function parseMercariIdsRaw(raw) {
  return String(raw || '').trim()
    .split(/[\n,，、\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function syncMercariIdListFromForm() {
  mercariIdList.value = parseMercariIdsRaw(form.value.mercari_item_id)
}

function applyMercariIdListToForm() {
  form.value.mercari_item_id = mercariIdList.value
    .map((s) => String(s || '').trim())
    .filter(Boolean)
    .join(',')
}

function addMercariId() {
  mercariIdList.value.push('')
}

function removeMercariId(idx) {
  mercariIdList.value.splice(idx, 1)
}

// ---- OCR 状态 ----
const ocrVisible = ref(false)
const ocrSide = ref('front')
const ocrTargetRow = ref(null)  // 从列表行直接调用时存储 row
const ocrCanvasRef = ref()
const ocrWrapRef = ref()
const ocrLoading = ref(false)
let _ocrDrawing = false
let _ocrStart = { x: 0, y: 0 }
let _ocrRect = { x: 0, y: 0, w: 0, h: 0 }
let _ocrNativeImg = null
let mediaStream = null
let scanTimer = null

// ---- 连续扫码状态 ----
const contScanVisible = ref(false)
/** 桌面端无 getUserMedia（多为 HTTP）时在降级弹窗内提示改用 HTTPS */
const contScanNeedsHttpsHint = ref(false)
const contState = ref('scanning')   // 'scanning' | 'found' | 'notfound' | 'ios-fallback'
const contBarcode = ref('')
const contProduct = ref(null)
const contQuantity = ref(1)
const contScanning = ref(false)
const contConfirming = ref(false)
const contVideoRef = ref()
const contCameraRefA = ref()
const contCameraRefB = ref()
const contScanMode = ref('stream') // 'stream' | 'fallback'
/** 下次拍照识别点击的 input（与另一路交替，缓解 iOS 重复选择同一 input 不触发 change） */
let contCaptureUseA = true
let contStream = null
let contTimer = null

const SCAN_INTERVAL_MS = 500
const CAMERA_CONSTRAINTS = {
  video: {
    facingMode: { ideal: 'environment' },
    width: { ideal: 1280 },
    height: { ideal: 720 },
    frameRate: { ideal: 30, max: 60 }
  },
  audio: false
}

/** 库存页扫码：用户选择的摄像头 deviceId（Windows 等多摄像头场景） */
const INVENTORY_CAMERA_STORAGE_KEY = 'mercari.inventory.preferredCameraDeviceId'
const inventoryCameraDevices = ref([])
const inventoryCameraSelectId = ref('')

function readSavedInventoryCameraDeviceId() {
  try {
    const s = localStorage.getItem(INVENTORY_CAMERA_STORAGE_KEY)
    const t = s && String(s).trim()
    return t || null
  } catch {
    return null
  }
}

function writeSavedInventoryCameraDeviceId(deviceId) {
  if (!deviceId) return
  try {
    localStorage.setItem(INVENTORY_CAMERA_STORAGE_KEY, String(deviceId))
  } catch {
    /* ignore */
  }
}

function inventoryCameraBaseVideoConstraints() {
  return {
    width: { ideal: 1280 },
    height: { ideal: 720 },
    frameRate: { ideal: 30, max: 60 },
  }
}

/**
 * 按优先级尝试打开摄像头：用户保存的 deviceId → 默认约束（后置等）→ 任意摄像头
 */
async function getInventoryCameraStream(preferredDeviceId = null) {
  const base = inventoryCameraBaseVideoConstraints()
  const attempts = []
  if (preferredDeviceId) {
    attempts.push({ video: { ...base, deviceId: { exact: preferredDeviceId } }, audio: false })
    attempts.push({ video: { ...base, deviceId: { ideal: preferredDeviceId } }, audio: false })
  }
  attempts.push(CAMERA_CONSTRAINTS)
  attempts.push({ video: { ...base }, audio: false })
  attempts.push({ video: true, audio: false })
  let lastErr
  for (const constraints of attempts) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints)
    } catch (e) {
      lastErr = e
    }
  }
  throw lastErr
}

async function refreshInventoryCameraDeviceList() {
  if (!navigator.mediaDevices?.enumerateDevices) {
    inventoryCameraDevices.value = []
    return
  }
  const list = await navigator.mediaDevices.enumerateDevices()
  const inputs = list.filter((d) => d.kind === 'videoinput')
  inventoryCameraDevices.value = inputs.map((d, i) => ({
    deviceId: d.deviceId,
    label: (d.label && String(d.label).trim()) ? d.label : `摄像头 ${i + 1}`,
  }))
}

function syncInventoryCameraSelectFromStream(stream) {
  const id = stream?.getVideoTracks?.()?.[0]?.getSettings?.()?.deviceId
  if (id) inventoryCameraSelectId.value = id
}

async function onContCameraDeviceChanged(deviceId) {
  if (!deviceId || contScanMode.value !== 'stream' || contState.value !== 'scanning') return
  writeSavedInventoryCameraDeviceId(deviceId)
  const videoEl = contVideoRef.value
  if (!videoEl) return
  if (contStream) {
    contStream.getTracks().forEach((t) => t.stop())
    contStream = null
  }
  try {
    contStream = await getInventoryCameraStream(deviceId)
    videoEl.srcObject = contStream
    await new Promise((resolve) => {
      videoEl.onloadedmetadata = resolve
    })
    await refreshInventoryCameraDeviceList()
    syncInventoryCameraSelectFromStream(contStream)
    const okDev = contStream.getVideoTracks()[0]?.getSettings?.()?.deviceId
    if (okDev) writeSavedInventoryCameraDeviceId(okDev)
  } catch {
    ElMessage.error('无法切换到所选摄像头，将尝试默认摄像头')
    try {
      contStream = await getInventoryCameraStream(null)
      videoEl.srcObject = contStream
      await new Promise((resolve) => {
        videoEl.onloadedmetadata = resolve
      })
      await refreshInventoryCameraDeviceList()
      syncInventoryCameraSelectFromStream(contStream)
      const fbDev = contStream.getVideoTracks()[0]?.getSettings?.()?.deviceId
      if (fbDev) writeSavedInventoryCameraDeviceId(fbDev)
    } catch {
      ElMessage.error('无法打开摄像头')
      contScanVisible.value = false
    }
  }
}

const form = ref({
  id: null,
  barcode: '',
  name: '',
  category_id: null,
  product_type_id: null,
  warehouse_id: null,
  price: 0,
  quantity: 1,
  mercari_item_id: '',
  on_sale_quantity: 0,
  description: '',
  listing_title: '',
  listing_body: '',
  image_front: null,
  image_back: null
})

const rules = {
  barcode: [{ required: true, message: '请填写或扫描条形码', trigger: 'blur' }],
  warehouse_id: [
    {
      validator: (_, val, cb) => {
        if (val == null || val === '') cb(new Error('请选择所属仓库'))
        else cb()
      },
      trigger: 'change',
    },
  ],
  image_front: [{ validator: (_, val, cb) => val ? cb() : cb(new Error('请拍摄或上传正面图')), trigger: 'change' }],
  price: [
    {
      validator: (_, val, cb) => {
        const n = Number(val)
        if (Number.isNaN(n) || n < 0) cb(new Error('单价须为大于等于 0 的数字'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

const productTypeCascaderProps = {
  value: 'value',
  label: 'label',
  children: 'children',
  emitPath: true,
  checkStrictly: false,
}

function updateViewportState() {
  isMobile.value = window.matchMedia('(max-width: 768px)').matches
  const ua = navigator.userAgent || ''
  const platform = navigator.platform || ''
  isIOS.value = /iPhone|iPad|iPod/i.test(ua) || (platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

// ============ OCR 框选 ============

function getOcrSrc(side) {
  if (ocrTargetRow.value) {
    return side === 'front'
      ? (ocrTargetRow.value.image_front || ocrTargetRow.value.image)
      : ocrTargetRow.value.image_back
  }
  return side === 'front' ? form.value.image_front : form.value.image_back
}

function openOcr(side) {
  ocrTargetRow.value = null
  ocrSide.value = side
  _ocrReset()
  ocrVisible.value = true
}

function openOcrForRow(row) {
  ocrTargetRow.value = row
  // 优先正面，若无则背面
  ocrSide.value = (row.image_front || row.image) ? 'front' : 'back'
  _ocrReset()
  ocrVisible.value = true
}

function switchOcrSide(side) {
  ocrSide.value = side
  _ocrReset()
  initOcrCanvas()
}

function _ocrReset() {
  _ocrNativeImg = null
  _ocrDrawing = false
  _ocrRect = { x: 0, y: 0, w: 0, h: 0 }
}

async function initOcrCanvas() {
  await nextTick()
  const canvas = ocrCanvasRef.value
  const wrap = ocrWrapRef.value
  if (!canvas || !wrap) return
  const src = getOcrSrc(ocrSide.value)
  if (!src) return
  _ocrNativeImg = null
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  await new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      _ocrNativeImg = img
      canvas.width = wrap.clientWidth
      canvas.height = Math.round((img.naturalHeight / img.naturalWidth) * wrap.clientWidth)
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      resolve()
    }
    img.onerror = reject
    img.src = src
  }).catch(() => {
    ElMessage.error('图片加载失败，无法进行 OCR')
  })
}

function _ocrGetPos(e) {
  const canvas = ocrCanvasRef.value
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  let clientX, clientY
  if (e.touches && e.touches.length > 0) {
    clientX = e.touches[0].clientX
    clientY = e.touches[0].clientY
  } else if (e.changedTouches && e.changedTouches.length > 0) {
    clientX = e.changedTouches[0].clientX
    clientY = e.changedTouches[0].clientY
  } else {
    clientX = e.clientX
    clientY = e.clientY
  }
  return {
    x: Math.max(0, Math.min(canvas.width, Math.round((clientX - rect.left) * scaleX))),
    y: Math.max(0, Math.min(canvas.height, Math.round((clientY - rect.top) * scaleY))),
  }
}

function _ocrRedraw() {
  const canvas = ocrCanvasRef.value
  if (!canvas || !_ocrNativeImg) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(_ocrNativeImg, 0, 0, canvas.width, canvas.height)
  const { x, y, w, h } = _ocrRect
  if (w > 2 && h > 2) {
    ctx.strokeStyle = '#409EFF'
    ctx.lineWidth = 2
    ctx.setLineDash([6, 3])
    ctx.strokeRect(x, y, w, h)
    ctx.fillStyle = 'rgba(64,158,255,0.12)'
    ctx.fillRect(x, y, w, h)
  }
}

function ocrDragStart(e) {
  _ocrDrawing = true
  _ocrStart = _ocrGetPos(e)
  _ocrRect = { x: _ocrStart.x, y: _ocrStart.y, w: 0, h: 0 }
}

function ocrDragMove(e) {
  if (!_ocrDrawing) return
  const cur = _ocrGetPos(e)
  _ocrRect = {
    x: Math.min(_ocrStart.x, cur.x),
    y: Math.min(_ocrStart.y, cur.y),
    w: Math.abs(cur.x - _ocrStart.x),
    h: Math.abs(cur.y - _ocrStart.y),
  }
  _ocrRedraw()
}

async function ocrDragEnd(e) {
  if (!_ocrDrawing) return
  _ocrDrawing = false
  const cur = _ocrGetPos(e)
  _ocrRect = {
    x: Math.min(_ocrStart.x, cur.x),
    y: Math.min(_ocrStart.y, cur.y),
    w: Math.abs(cur.x - _ocrStart.x),
    h: Math.abs(cur.y - _ocrStart.y),
  }
  _ocrRedraw()
  if (_ocrRect.w < 10 || _ocrRect.h < 10) return
  await _ocrSendRegion()
}

async function _ocrSendRegion() {
  if (!_ocrNativeImg) return
  const { x, y, w, h } = _ocrRect
  const canvas = ocrCanvasRef.value
  const scaleX = _ocrNativeImg.naturalWidth / canvas.width
  const scaleY = _ocrNativeImg.naturalHeight / canvas.height
  const crop = document.createElement('canvas')
  crop.width = Math.round(w * scaleX)
  crop.height = Math.round(h * scaleY)
  crop.getContext('2d').drawImage(
    _ocrNativeImg,
    Math.round(x * scaleX), Math.round(y * scaleY), crop.width, crop.height,
    0, 0, crop.width, crop.height
  )
  const base64 = crop.toDataURL('image/jpeg', 0.95)
  ocrLoading.value = true
  try {
    const res = await ocrApi.ocrRegion(base64)
    if (res?.text) {
      if (ocrTargetRow.value) {
        // 从列表行直接调用：直接保存到后端并更新行数据
        await inventoryApi.update(ocrTargetRow.value.id, { name: res.text })
        ocrTargetRow.value.name = res.text
        ElMessage.success(`识别成功并已保存：${res.text}`)
      } else {
        // 从编辑弹窗调用：写入表单
        form.value.name = res.text
        ElMessage.success(`识别成功：${res.text}`)
      }
      ocrVisible.value = false
    } else {
      ElMessage.warning('未识别到文字，请重新框选更清晰的区域')
    }
  } catch {
    ElMessage.error('OCR 识别失败，请确认后端已安装 easyocr 并已重启服务')
  } finally {
    ocrLoading.value = false
  }
}

function getCellKey(row, field) {
  return `${row.id}:${field}`
}

function isEditing(row, field) {
  return editingCell.value === getCellKey(row, field)
}

function startInlineEdit(row, field) {
  if (listingPickMode.value) return
  editingCell.value = getCellKey(row, field)
  const currentValue = row[field]
  editingValue.value = currentValue === null || currentValue === undefined ? '' : String(currentValue)
}

function normalizeInlineValue(field, rawValue) {
  const value = String(rawValue ?? '').trim()
  if (field === 'name') {
    return value || null
  }
  return value || null
}

function setInlineOwnerSelectRef(rowId, el) {
  if (!el) {
    inlineOwnerSelectMap.delete(rowId)
    return
  }
  inlineOwnerSelectMap.set(rowId, el)
}

function openSelectMenuByMap(map, rowId) {
  nextTick(() => {
    const selectRef = map.get(rowId)
    if (!selectRef) return
    if (typeof selectRef.focus === 'function') {
      selectRef.focus()
    }
    if (typeof selectRef.toggleMenu === 'function') {
      selectRef.toggleMenu()
      setTimeout(() => {
        if (selectRef.expanded !== true && typeof selectRef.toggleMenu === 'function') {
          selectRef.toggleMenu()
        }
      }, 0)
    }
  })
}

function openProductTypeInline(row) {
  if (listingPickMode.value) return
  editingProductTypeRowId.value = row.id
}

function openOwnerInline(row) {
  if (listingPickMode.value) return
  editingOwnerRowId.value = row.id
  openSelectMenuByMap(inlineOwnerSelectMap, row.id)
}

function displayProductTypeName(row) {
  const typeId = row?.product_type_id ?? null
  if (typeId != null) {
    const matched = productTypes.value.find((t) => t.id === typeId)
    if (matched?.name) return matched.name
  }
  const name = row?.product_type_name
  if (name == null) return ''
  const text = String(name).trim()
  return text || ''
}

function displayOwnerName(row) {
  const ownerId = row?.owner_user_id ?? null
  if (ownerId != null) {
    const matched = ownerUsers.value.find((u) => u.id === ownerId)
    if (matched) return matched.display_name || matched.username || ''
  }
  const name = row?.owner_user_name
  if (name == null) return ''
  const text = String(name).trim()
  return text || ''
}

async function saveInlineEdit(row, field) {
  const key = getCellKey(row, field)
  if (editingCell.value !== key || savingInlineCell.value === key) return
  let newValue
  try {
    newValue = normalizeInlineValue(field, editingValue.value)
  } catch (err) {
    ElMessage.warning(err.message || '输入格式不正确')
    editingCell.value = ''
    editingValue.value = ''
    return
  }
  if (row[field] === newValue) {
    editingCell.value = ''
    editingValue.value = ''
    return
  }
  savingInlineCell.value = key
  try {
    await inventoryApi.update(row.id, { [field]: newValue })
    row[field] = newValue
    ElMessage.success('已更新')
  } finally {
    if (editingCell.value === key) {
      editingCell.value = ''
      editingValue.value = ''
    }
    savingInlineCell.value = ''
  }
}

async function saveCategoryInline(row, categoryId) {
  const normalizedCategoryId = categoryId || null
  if ((row.category_id || null) === normalizedCategoryId) {
    editingCategoryRowId.value = null
    return
  }
  try {
    await inventoryApi.update(row.id, { category_id: normalizedCategoryId })
    row.category_id = normalizedCategoryId
    const matched = categories.value.find((c) => c.id === normalizedCategoryId)
    row.category_name = matched?.name || null
    ElMessage.success('游戏分类已更新')
  } finally {
    editingCategoryRowId.value = null
  }
}

async function saveProductTypeInline(row, productTypeId) {
  const picked = Array.isArray(productTypeId) ? productTypeId[productTypeId.length - 1] : null
  const normalized = (picked && String(picked).startsWith('PT:'))
    ? Number(String(picked).slice(3))
    : null
  if ((row.product_type_id || null) === normalized) {
    editingProductTypeRowId.value = null
    return
  }
  try {
    await inventoryApi.update(row.id, { product_type_id: normalized })
    row.product_type_id = normalized
    const matched = productTypes.value.find((t) => t.id === normalized)
    row.product_type_name = matched?.name || ''
    ElMessage.success('商品类型已更新')
  } finally {
    editingProductTypeRowId.value = null
  }
}

function getInlineProductTypePath(row) {
  const typeId = Number(row?.product_type_id)
  if (!Number.isFinite(typeId)) return []
  const path = productTypeTreeMeta.value.idToPath.get(typeId)
  return path ? [...path] : []
}

async function saveOwnerInline(row, ownerUserId) {
  const normalized = ownerUserId || null
  if ((row.owner_user_id || null) === normalized) {
    editingOwnerRowId.value = null
    return
  }
  try {
    await inventoryApi.update(row.id, { owner_user_id: normalized })
    row.owner_user_id = normalized
    const matched = ownerUsers.value.find((u) => u.id === normalized)
    row.owner_user_name = matched ? (matched.display_name || matched.username) : ''
    ElMessage.success('商品归属已更新')
  } finally {
    editingOwnerRowId.value = null
  }
}

function startCreateCategory() {
  categoryCreateMode.value = true
  newCategoryName.value = ''
}

function cancelCreateCategory() {
  categoryCreateMode.value = false
  newCategoryName.value = ''
}

function buildProductTypeOptionsFromMappings(mappings) {
  const seen = new Set()
  const out = []
  for (const m of (mappings || [])) {
    const idRaw = String(m?.mapping_id ?? '').trim()
    const name = String(m?.product_type ?? '').trim()
    if (!idRaw || !name) continue
    const id = Number(idRaw)
    if (!Number.isFinite(id) || seen.has(id)) continue
    seen.add(id)
    out.push({ id, name })
  }
  return out
}

function ensureNode(children, value, label) {
  let node = children.find((item) => item.value === value)
  if (!node) {
    node = { value, label, children: [] }
    children.push(node)
  }
  return node
}

const productTypeTreeMeta = computed(() => {
  const roots = []
  const idToPath = new Map()
  for (const m of (listingCategoryMappings.value || [])) {
    const idRaw = String(m?.mapping_id ?? '').trim()
    const typeName = String(m?.product_type ?? '').trim()
    if (!idRaw || !typeName) continue
    const id = Number(idRaw)
    if (!Number.isFinite(id)) continue
    const l1 = String(m?.category_level1 ?? '').trim() || '未分类'
    const l2 = String(m?.category_level2 ?? '').trim()
    const l3 = String(m?.category_level3 ?? '').trim()

    const l1Node = ensureNode(roots, `L1:${l1}`, l1)
    const l1Path = [`L1:${l1}`]
    if (!l2) {
      l1Node.children.push({ value: `PT:${id}`, label: typeName, children: [] })
      idToPath.set(id, [...l1Path, `PT:${id}`])
      continue
    }

    const l2Val = `L2:${l1}__${l2}`
    const l2Node = ensureNode(l1Node.children, l2Val, l2)
    const l2Path = [...l1Path, l2Val]
    if (!l3) {
      l2Node.children.push({ value: `PT:${id}`, label: typeName, children: [] })
      idToPath.set(id, [...l2Path, `PT:${id}`])
      continue
    }

    const l3Val = `L3:${l1}__${l2}__${l3}`
    const l3Node = ensureNode(l2Node.children, l3Val, l3)
    const l3Path = [...l2Path, l3Val]
    l3Node.children.push({ value: `PT:${id}`, label: typeName, children: [] })
    idToPath.set(id, [...l3Path, `PT:${id}`])
  }
  return { roots, idToPath }
})

const productTypeCascaderOptions = computed(() => productTypeTreeMeta.value.roots)

function syncCascaderPathByProductTypeId(typeId) {
  const normalized = typeId == null ? null : Number(typeId)
  if (!Number.isFinite(normalized)) {
    productTypeCascaderPath.value = []
    return
  }
  const path = productTypeTreeMeta.value.idToPath.get(normalized)
  productTypeCascaderPath.value = path ? [...path] : []
}

function handleProductTypeCascaderChange(path) {
  const picked = Array.isArray(path) ? path[path.length - 1] : null
  if (!picked || !String(picked).startsWith('PT:')) {
    form.value.product_type_id = null
    return
  }
  const id = Number(String(picked).slice(3))
  form.value.product_type_id = Number.isFinite(id) ? id : null
}

function handleFilterProductTypeChange(path) {
  const picked = Array.isArray(path) ? path[path.length - 1] : null
  if (!picked || !String(picked).startsWith('PT:')) {
    filterProductType.value = null
    load()
    return
  }
  const id = Number(String(picked).slice(3))
  filterProductType.value = Number.isFinite(id) ? id : null
  load()
}

async function confirmCreateCategory() {
  const name = newCategoryName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分类名称')
    return
  }
  const created = await categoryApi.create({ name })
  categories.value = await categoryApi.list()
  form.value.category_id = created?.id ?? form.value.category_id
  newCategoryName.value = ''
  categoryCreateMode.value = false
  ElMessage.success('分类创建成功')
}

function startCreateWarehouse() {
  warehouseCreateMode.value = true
  newWarehouseName.value = ''
}

function cancelCreateWarehouse() {
  warehouseCreateMode.value = false
  newWarehouseName.value = ''
}

async function confirmCreateWarehouse() {
  const name = newWarehouseName.value.trim()
  if (!name) {
    ElMessage.warning('请输入仓库名称')
    return
  }
  const created = await warehouseApi.create({ name })
  warehouses.value = await warehouseApi.list()
  form.value.warehouse_id = created?.id ?? form.value.warehouse_id
  newWarehouseName.value = ''
  warehouseCreateMode.value = false
  ElMessage.success('仓库创建成功')
  formRef.value?.validateField('warehouse_id')
}

/** 从指定 video 元素抓一帧，返回 Blob（JPEG） */
function captureFrame(videoElRef = videoRef) {
  const video = videoElRef.value
  if (!video || video.readyState < 2 || !video.videoWidth) return null
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0)
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85))
}

async function load(options = {}) {
  const { resetPage = true } = options
  loading.value = true
  const params = {}
  if (keyword.value) params.keyword = keyword.value
  if (filterCat.value) params.category_id = filterCat.value
  if (filterWarehouse.value) params.warehouse_id = filterWarehouse.value
  if (filterProductType.value) params.product_type_id = filterProductType.value
  if (filterOwnerUserId.value) params.owner_user_id = filterOwnerUserId.value
  if (listingPickMode.value) params.in_stock_only = true
  list.value = await inventoryApi.list(params).finally(() => (loading.value = false))
  if (resetPage) {
    inventorySortProp.value = ''
    inventorySortOrder.value = ''
    currentPage.value = 1
    return
  }
  const totalPages = Math.max(1, Math.ceil(list.value.length / pageSize))
  if (currentPage.value > totalPages) currentPage.value = totalPages
  if (currentPage.value < 1) currentPage.value = 1
}

/** 与控制台相同：全库条目/总数量 + 接口返回的今日入出库（手机端不展示统计，一般不请求） */
async function loadInventoryStats() {
  if (isMobile.value) return
  const [inventoryItems, tx] = await Promise.all([
    inventoryApi.list(),
    transactionApi.list({ page_size: 10 }),
  ])
  const totalQuantity = inventoryItems.reduce((sum, p) => sum + (p.quantity || 0), 0)
  inventorySummary.value = {
    total_inventory: inventoryItems.length,
    total_quantity: totalQuantity,
    today_in: tx.today_in ?? '-',
    today_out: tx.today_out ?? '-',
  }
}

const sortedInventoryList = computed(() => {
  const arr = [...list.value]
  const prop = inventorySortProp.value
  const order = inventorySortOrder.value
  if (!prop || !order) return arr
  const mult = order === 'ascending' ? 1 : -1
  arr.sort((a, b) => {
    if (prop === 'price') {
      const va = Number(a.price) || 0
      const vb = Number(b.price) || 0
      if (va < vb) return -1 * mult
      if (va > vb) return 1 * mult
      return 0
    }
    if (prop === 'quantity') {
      const va = Number(a.quantity) || 0
      const vb = Number(b.quantity) || 0
      if (va < vb) return -1 * mult
      if (va > vb) return 1 * mult
      return 0
    }
    if (prop === 'on_sale_quantity') {
      const va = Number(a.on_sale_quantity) || 0
      const vb = Number(b.on_sale_quantity) || 0
      if (va < vb) return -1 * mult
      if (va > vb) return 1 * mult
      return 0
    }
    if (prop === 'pending_outbound_qty') {
      const va = Number(a.pending_outbound_qty) || 0
      const vb = Number(b.pending_outbound_qty) || 0
      if (va < vb) return -1 * mult
      if (va > vb) return 1 * mult
      return 0
    }
    return 0
  })
  return arr
})

function onInventorySortChange({ prop, order }) {
  inventorySortProp.value = order ? prop : ''
  inventorySortOrder.value = order || ''
  currentPage.value = 1
}

/** 库存数量：0 红色；1～3 黄色；大于 3 绿色 */
function quantityTagType(q) {
  const n = Number(q) || 0
  if (n === 0) return 'danger'
  if (n <= 3) return 'warning'
  return 'success'
}

/**
 * 将本地 /imges/ 路径转为缩略图接口 URL（列表小图用）。
 * 非本地图片（外部 URL）原样返回。
 */
function thumbUrl(src, size = 200) {
  if (!src || !src.startsWith('/imges/')) return src
  return `/api/inventory/image-thumb?path=${encodeURIComponent(src)}&size=${size}`
}

function mercariItemIds(row) {
  const raw = String(row?.mercari_item_id || '').trim()
  if (!raw) return []
  const parts = raw
    .split(/[\n,，、\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  const out = []
  const seen = new Set()
  for (const p of parts) {
    if (seen.has(p)) continue
    seen.add(p)
    out.push(p)
  }
  return out
}

function getInventoryExpandSlot(inventoryId) {
  return inventoryExpandById.value[inventoryId] || null
}

function getInventoryExpandRows(row) {
  const slot = getInventoryExpandSlot(row?.id)
  if (!slot || !Array.isArray(slot.rows)) return []
  return slot.rows
}

function formatUnixTs(sec) {
  const n = Number(sec)
  if (!Number.isFinite(n) || n <= 0) return '-'
  const ms = n > 1e12 ? n : n * 1000
  const d = new Date(ms)
  if (Number.isNaN(d.getTime())) return '-'
  const p2 = (x) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`
}

function displayOnSaleStatus(status) {
  const key = String(status ?? '').trim()
  if (!key) return '-'
  return onSaleStatusMap[key]?.label || key
}

function onSaleStatusTagType(status) {
  const key = String(status ?? '').trim()
  return onSaleStatusMap[key]?.tag || 'info'
}

async function ensureInventoryExpandLoaded(row) {
  const id = row?.id
  if (!id) return
  if (!inventoryExpandById.value[id]) {
    inventoryExpandById.value[id] = { loading: false, loaded: false, rows: [] }
  }
  const slot = inventoryExpandById.value[id]
  if (slot.loading || slot.loaded) return
  const itemIds = mercariItemIds(row)
  if (!itemIds.length) {
    slot.rows = []
    slot.loaded = true
    return
  }
  slot.loading = true
  try {
    const res = await onSaleItemApi.listByItemIds({ item_ids: itemIds.join(',') })
    const rows = Array.isArray(res?.items) ? res.items : []
    const byId = new Map(rows.map((r) => [String(r.item_id || '').trim(), r]))
    slot.rows = itemIds.map((iid) => byId.get(String(iid).trim())).filter(Boolean)
    slot.loaded = true
  } catch {
    slot.rows = []
    slot.loaded = true
  } finally {
    slot.loading = false
  }
}

function onInventoryExpandChange(row, expandedRows) {
  const opened = Array.isArray(expandedRows) && expandedRows.some((r) => r?.id === row?.id)
  if (!opened) return
  ensureInventoryExpandLoaded(row)
}

const pagedList = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return sortedInventoryList.value.slice(start, start + pageSize)
})

function openDialog(row = null) {
  categoryCreateMode.value = false
  warehouseCreateMode.value = false
  newCategoryName.value = ''
  newWarehouseName.value = ''
  form.value = row
    ? {
        id: row.id,
        barcode: row.barcode || '',
        name: row.name || null,
        sku: row.sku || null,
        category_id: row.category_id || null,
        product_type_id: row.product_type_id || null,
        owner_user_id: row.owner_user_id || null,
        warehouse_id: row.warehouse_id || null,
        price: Math.round(Number(row.price ?? 0)),
        quantity: row.quantity ?? 0,
        mercari_item_id: row.mercari_item_id ?? '',
        on_sale_quantity: Number(row.on_sale_quantity ?? 0),
        description: row.description || null,
        listing_title: row.listing_title ?? '',
        listing_body: row.listing_body ?? '',
        image_front: row.image_front || row.image || null,
        image_back: row.image_back || null
      }
    : {
        id: null,
        barcode: '',
        name: null,
        sku: null,
        category_id: null,
        product_type_id: null,
        owner_user_id: null,
        warehouse_id: null,
        price: 0,
        quantity: 1,
        mercari_item_id: '',
        on_sale_quantity: 0,
        description: null,
        listing_title: '',
        listing_body: '',
        image_front: null,
        image_back: null
      }
  syncQuantityEditFromForm()
  syncPriceEditFromForm()
  syncMercariIdListFromForm()
  syncCascaderPathByProductTypeId(form.value.product_type_id)
  dialogVisible.value = true
}

watch(dialogVisible, (visible) => {
  if (!visible) {
    categoryCreateMode.value = false
    warehouseCreateMode.value = false
    newCategoryName.value = ''
    newWarehouseName.value = ''
  }
})

function openNoBarcodeEntry() {
  openDialog()
  const uuid = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `nb-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
  form.value.barcode = uuid
}

function buildListingSeedFromInventoryRows(rows) {
  if (!rows?.length) return null
  const first = rows[0]
  const names = rows.map((r) => String(r.name || '').trim()).filter(Boolean)
  let name = names.join('、')
  if (name.length > 200) name = `${name.slice(0, 197)}…`
  const listingTitles = rows.map((r) => String(r.listing_title || '').trim()).filter(Boolean)
  let listingTitle = listingTitles.join('、')
  if (!listingTitle) listingTitle = name
  if (listingTitle.length > 200) listingTitle = `${listingTitle.slice(0, 197)}…`
  const sameType = rows.every((r) => r.product_type_id === first.product_type_id)
  const mappingId =
    sameType && first.product_type_id != null ? String(first.product_type_id) : null
  const descParts = rows
    .map((r) => {
      const b = String(r.listing_body ?? '').trim()
      if (b) return b
      return String(r.description ?? '').trim()
    })
    .filter(Boolean)
  const imageBack = rows.map((r) => r?.image_back).find((x) => x) || ''
  return {
    image: first.image_front || first.image || '',
    image_back: imageBack,
    name: name || String(first.name || '').trim() || '',
    listing_title: listingTitle || '',
    category_mapping_id: mappingId,
    description: descParts.join('\n---\n') || '',
    price: Math.round(Number(first.price ?? 0)),
    inventory_ids: rows.map((r) => r.id)
  }
}

/** 组合出品：仅用于预览多商品图；不预填名称与说明 */
function buildCombinedListingSeedFromInventoryRows(rows) {
  if (!rows?.length) return null
  const first = rows[0]
  const sameType = rows.every((r) => r.product_type_id === first.product_type_id)
  const mappingId =
    sameType && first.product_type_id != null ? String(first.product_type_id) : null
  const combined_images = rows.map((r) => ({
    inventory_id: r.id,
    front: r.image_front || r.image || '',
    back: String(r.image_back || '').trim() || ''
  }))
  return {
    image: '',
    image_back: '',
    name: '',
    listing_title: String(first.listing_title || '').trim(),
    category_mapping_id: mappingId,
    description: '',
    /** 组合出品：取首条库存单价为初始值，保存时写回所选全部条目 */
    price: Math.round(Number(first.price ?? 0)),
    combined_images,
    inventory_ids: rows.map((r) => r.id)
  }
}

/** 出品表单保存：写回所选库存的出品标题、listing_body、price（与编辑商品一致） */
async function onListingFormSaved(data) {
  const ids = (data.inventory_ids || []).map((id) => Number(id)).filter((x) => Number.isFinite(x))
  if (!ids.length) return
  const listing_title = data.listing_title != null ? String(data.listing_title).trim() : ''
  const listing_body = data.description != null ? String(data.description) : ''
  const price = Math.round(Number(data.price ?? 0))
  const safePrice = Number.isFinite(price) && price >= 0 ? price : 0

  // ── 1. 写回库存 出品标题、listing_body 与 price ───────────────────────── //
  try {
    for (const id of ids) {
      await inventoryApi.update(id, { listing_title, listing_body, price: safePrice })
    }
  } catch {
    // 错误提示由拦截器处理
    return
  }

  // ── 2. 派发出品自动化（开启浏览器，填写 Mercari 出品页） ─────────────── //
  const accountId = data.meilu_account_id
  if (!accountId) {
    ElMessage.success('出品标题、商品说明与单价已保存到库存（未选出品账号，跳过自动化）')
    await load({ resetPage: false })
    loadInventoryStats()
    return
  }

  // account_key 规则：meilu_{id}，与 webdrive profile 目录名一致
  const accountKey = `meilu_${accountId}`

  // 收集图片 URL：正面在前、背面在后；组合出品取所有 combined_images 的正面
  const imageUrls = []
  if (data.combined_images && Array.isArray(data.combined_images)) {
    for (const block of data.combined_images) {
      if (block.front) imageUrls.push(block.front)
      if (block.back) imageUrls.push(block.back)
    }
  } else {
    if (data.image) imageUrls.push(data.image)
    if (data.image_back) imageUrls.push(data.image_back)
  }

  ElMessage.info('正在启动浏览器并填写出品页，请稍候…')
  try {
    const res = await listingApi.postToMarket({
      account_key: accountKey,
      name: listing_title,
      description: listing_body,
      image_urls: imageUrls,
      category_mapping_id: data.category_mapping_id != null
        ? String(data.category_mapping_id)
        : null,
      status: data.status || '',
      shipping_payer: data.shipping_payer || 'seller',
      shipping_method: data.shipping_method || 'undecided',
      sale_type: data.sale_type || 'instant_buy',
      auction_duration: data.auction_duration || 'normal',
      price: safePrice,
      shipping_days: data.shipping_days || '2_3_days',
      shipping_from_area_id: data.shipping_from ? String(data.shipping_from) : '',
      use_mitm_proxy: true
    })
    if (res?.success) {
      const d = res.data || {}
      const parts = []
      if (d.images_uploaded) parts.push(`已上传 ${d.images_uploaded} 张图片`)
      if (d.name_filled) parts.push('出品标题已填写')
      if (d.description_filled) parts.push('商品说明已填写')
      if (d.category_selected) parts.push('商品类型已选择')
      if (d.condition_set) parts.push('商品状态已选择')
      if (d.shipping_payer_set) parts.push('快递费负担已设置')
      if (d.shipping_method_set) parts.push('配送方法已设置')
      if (d.sale_type_set && d.price_filled) parts.push('销售方式与价格已填写')
      if (d.shipping_days_set) parts.push('发货天数已设置')
      if (d.shipping_from_set) parts.push('发货地址已设置')
      if (d.submitted === true) {
        ElMessage.success('出品成功！' + (d.submit_message ? `（${d.submit_message}）` : ''))
      } else if (d.submit_error) {
        ElMessage.error(`出品按钮点击失败：${d.submit_error}`)
      } else if (d.submitted === false && d.submit_message) {
        ElMessage.warning(`出品提示异常：${d.submit_message}`)
      } else {
        ElMessage.success(
          parts.length ? `出品页填写完成：${parts.join('、')}` : '浏览器已打开出品页'
        )
      }
    }
  } catch {
    // axios 拦截器已弹窗，此处仅记录
  }

  ElMessage.success('出品标题、商品说明与单价已保存到库存')
  await load({ resetPage: false })
  loadInventoryStats()
}

/** 组合出品可选：库存大于 0 */
function isListingPickSelectable(row) {
  return Number(row?.quantity ?? 0) > 0
}

/** 进入「组合出品」：在列表中多选库存后再填表单 */
async function enterListingPickMode() {
  listingPickMode.value = true
  listingPickIds.value = new Set()
  closeAllInlineEditors()
  await load({ resetPage: false })
}

/** 「出品」：当前行直接打开出品表单（单条库存） */
function openListingFormForRow(row) {
  if (!row || row.id == null) return
  if (!isListingPickSelectable(row)) {
    ElMessage.warning('库存为 0 的商品无法出品')
    return
  }
  listingSeedData.value = buildListingSeedFromInventoryRows([row])
  listingDialogVisible.value = true
}

async function exitListingPickMode() {
  listingPickMode.value = false
  listingPickIds.value = new Set()
  await load({ resetPage: false })
}

function toggleListingPickRow(row) {
  if (!row || row.id == null) return
  const next = new Set(listingPickIds.value)
  if (next.has(row.id)) {
    next.delete(row.id)
    listingPickIds.value = next
    return
  }
  if (!isListingPickSelectable(row)) {
    ElMessage.warning('库存为 0 的商品不能选中')
    return
  }
  next.add(row.id)
  listingPickIds.value = next
}

function rowClassName({ row }) {
  const classes = []
  if (listingPickMode.value && listingPickIds.value.has(row?.id)) {
    classes.push('listing-pick-row-selected')
  }
  if (listingPickMode.value && !isListingPickSelectable(row)) {
    classes.push('listing-pick-row-disabled')
  }
  return classes.filter(Boolean).join(' ')
}

function onTableRowClick(row) {
  if (!listingPickMode.value) return
  toggleListingPickRow(row)
}

function closeAllInlineEditors() {
  editingCategoryRowId.value = null
  editingProductTypeRowId.value = null
  editingOwnerRowId.value = null
  editingCell.value = ''
  editingValue.value = ''
}

async function confirmListingPick() {
  if (!listingPickIds.value.size) {
    ElMessage.warning('请至少选择一条商品')
    return
  }
  const idSet = listingPickIds.value
  const rows = sortedInventoryList.value.filter(
    (r) => idSet.has(r.id) && isListingPickSelectable(r)
  )
  if (!rows.length) {
    ElMessage.warning('所选商品均无库存，无法出品')
    return
  }
  combinedListingSeedData.value = buildCombinedListingSeedFromInventoryRows(rows)
  await exitListingPickMode()
  combinedListingDialogVisible.value = true
}

function triggerUpload(side) {
  if (side === 'front') fileInputFront.value?.click()
  else fileInputBack.value?.click()
}

function handleImageUpload(e, side) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片不能超过5MB')
    return
  }
  const reader = new FileReader()
  reader.onload = (ev) => {
    if (side === 'front') {
      form.value.image_front = ev.target.result
      formRef.value?.validateField('image_front')
    } else {
      form.value.image_back = ev.target.result
    }
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

async function submit() {
  applyQuantityEditToForm()
  applyPriceEditToForm()
  applyMercariIdListToForm()
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = { ...form.value }
    payload.price = Math.round(Number(payload.price ?? 0))
    if (payload.mercari_item_id !== undefined && payload.mercari_item_id !== null) {
      payload.mercari_item_id = String(payload.mercari_item_id).trim() || null
    }
    if (payload.on_sale_quantity != null) {
      payload.on_sale_quantity = Math.max(0, Math.round(Number(payload.on_sale_quantity)))
    }
    if (payload.id) await inventoryApi.update(payload.id, payload)
    else await inventoryApi.create(payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load({ resetPage: false })
    loadInventoryStats()
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  await inventoryApi.remove(id)
  ElMessage.success('删除成功')
  await load({ resetPage: false })
  loadInventoryStats()
}

async function openScanDialog() {
  stopScan()
  scanning.value = false

  // HTTP 非安全上下文下 Chromium 不暴露 mediaDevices → 只能选图
  const canStream = typeof navigator.mediaDevices?.getUserMedia === 'function'
  if (!canStream) {
    if (!window.isSecureContext) {
      ElMessage.warning('HTTP 访问时无法打开摄像头，已改为选图。请使用 https:// 打开本站后再试扫描。')
    }
    cameraInputRef.value.value = ''
    cameraInputRef.value.click()
    return
  }

  scanVisible.value = true
  await nextTick()

  try {
    const savedCam = readSavedInventoryCameraDeviceId()
    mediaStream = await getInventoryCameraStream(savedCam)
    videoRef.value.srcObject = mediaStream

    // 等视频就绪后再开始抓帧
    await new Promise((resolve) => {
      videoRef.value.onloadedmetadata = resolve
    })

    scanTimer = setInterval(async () => {
      if (!scanVisible.value || scanning.value) return
      const blob = await captureFrame()
      if (!blob) return
      scanning.value = true
      try {
        const res = await scanApi.scanBarcode(blob)
        if (res?.found && res.barcode) {
          form.value.barcode = res.barcode
          ElMessage.success(`扫码成功：${res.barcode}`)
          scanVisible.value = false
        }
      } catch {
        // 识别失败时静默，继续下一帧
      } finally {
        scanning.value = false
      }
    }, SCAN_INTERVAL_MS)
  } catch {
    ElMessage.error('无法打开摄像头，请检查浏览器摄像头权限后重试。')
    scanVisible.value = false
  }
}

function stopScan() {
  if (scanTimer) {
    clearInterval(scanTimer)
    scanTimer = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop())
    mediaStream = null
  }
  scanning.value = false
}

/** iOS Safari / 非安全上下文：拍照后将图片文件送后端识别 */
async function handleCameraCapture(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''

  try {
    const res = await scanApi.scanBarcode(file)
    if (res?.found && res.barcode) {
      form.value.barcode = res.barcode
      ElMessage.success(`扫码成功：${res.barcode}`)
    } else {
      ElMessage.warning('未能识别条形码，请确保照片清晰并对准条形码')
    }
  } catch {
    ElMessage.warning('识别请求失败，请检查网络连接后重试')
  }
}

// ============ 连续扫码函数 ============

async function openContScan() {
  stopContScan()
  contQuantity.value = 1
  contBarcode.value = ''
  contProduct.value = null
  contScanNeedsHttpsHint.value = false

  const canUseStream = typeof navigator.mediaDevices?.getUserMedia === 'function'

  // iOS：仍直接唤起相册/相机，避免多余一步
  if (isIOS.value) {
    contScanMode.value = 'fallback'
    contState.value = 'ios-fallback'
    contScanVisible.value = false
    triggerContCapture()
    return
  }

  // Windows / Android 桌面浏览器：HTTP 下无 mediaDevices，先显示说明弹窗，避免直接弹出「打开文件」
  if (!canUseStream) {
    contScanMode.value = 'fallback'
    contState.value = 'ios-fallback'
    contScanNeedsHttpsHint.value = !window.isSecureContext
    contScanVisible.value = true
    return
  }

  contScanMode.value = 'stream'
  contState.value = 'scanning'
  contScanVisible.value = true
  await nextTick()

  try {
    const savedCam = readSavedInventoryCameraDeviceId()
    contStream = await getInventoryCameraStream(savedCam)
    contVideoRef.value.srcObject = contStream
    await new Promise((resolve) => { contVideoRef.value.onloadedmetadata = resolve })
    await refreshInventoryCameraDeviceList()
    syncInventoryCameraSelectFromStream(contStream)
    const curDev = contStream.getVideoTracks()[0]?.getSettings?.()?.deviceId
    if (curDev) writeSavedInventoryCameraDeviceId(curDev)
    startContTimer()
  } catch {
    ElMessage.error('无法打开摄像头，请检查权限后重试')
    contScanVisible.value = false
  }
}

function startContTimer() {
  contTimer = setInterval(async () => {
    if (contState.value !== 'scanning' || contScanning.value) return
    const blob = await captureFrame(contVideoRef)
    if (!blob) return
    contScanning.value = true
    try {
      const res = await scanApi.scanBarcode(blob)
      if (res?.found && res.barcode) {
        await handleContBarcode(res.barcode)
      }
    } catch { /* 静默失败，继续扫 */ } finally {
      contScanning.value = false
    }
  }, SCAN_INTERVAL_MS)
}

async function handleContBarcode(barcode) {
  // 停止扫码循环，等待用户操作
  clearInterval(contTimer)
  contTimer = null
  contBarcode.value = barcode

  try {
    const res = await inventoryApi.findByBarcode(barcode)
    if (res?.found) {
      contProduct.value = res.product
      contQuantity.value = 1
      contState.value = 'found'
    } else {
      contState.value = 'notfound'
    }
  } catch {
    ElMessage.error('查询商品失败，请检查网络连接')
    contState.value = 'notfound'
  }
}

function resumeContScan() {
  contBarcode.value = ''
  contProduct.value = null
  if (contScanMode.value === 'fallback') {
    contState.value = 'ios-fallback'
    triggerContCapture()
    return
  }
  contState.value = 'scanning'
  if (contStream) {
    startContTimer()
  }
}

async function confirmContAction() {
  if (!contProduct.value?.warehouse_id) {
    ElMessage.warning('该商品未设置所属仓库，请先编辑商品后再操作')
    return
  }
  contConfirming.value = true
  try {
    const quantity = Math.max(1, Math.round(Number(contQuantity.value) || 1))
    const res = await inventoryApi.stockIn(contProduct.value.id, {
      warehouse_id: contProduct.value.warehouse_id,
      quantity,
      remark: '连续扫码入库'
    })
    ElMessage.success(`入库成功，当前库存：${res.new_quantity} 件`)
    load()
    loadInventoryStats()
    contScanVisible.value = false
  } catch {
    // 错误由 axios 拦截器统一提示
  } finally {
    contConfirming.value = false
  }
}

function openAddFromScan() {
  const barcode = contBarcode.value
  contScanVisible.value = false
  openDialog()
  // nextTick 等对话框挂载后再填写 barcode
  nextTick(() => { form.value.barcode = barcode })
}

function stopContScan() {
  clearInterval(contTimer)
  contTimer = null
  contScanNeedsHttpsHint.value = false
  if (contStream) {
    contStream.getTracks().forEach((t) => t.stop())
    contStream = null
  }
  contScanning.value = false
}

function triggerContCapture() {
  contCaptureUseA = !contCaptureUseA
  const el = contCaptureUseA ? contCameraRefA.value : contCameraRefB.value
  if (!el) return
  el.value = ''
  el.click()
}

async function handleContCapture(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''
  contScanning.value = true
  try {
    const res = await scanApi.scanBarcode(file)
    if (res?.found && res.barcode) {
      if (!contScanVisible.value) {
        contScanVisible.value = true
        await nextTick()
      }
      await handleContBarcode(res.barcode)
    } else {
      ElMessage.warning('未识别到条形码，请重拍')
    }
  } catch {
    ElMessage.warning('识别失败，请重试')
  } finally {
    contScanning.value = false
  }
}

// ============ 条形码寻找函数 ============

watch(isMobile, (mobile) => {
  if (!mobile) loadInventoryStats()
})

// ============ 生命周期 ============

onBeforeUnmount(stopScan)
onBeforeUnmount(stopContScan)

onMounted(async () => {
  updateViewportState()
  window.addEventListener('resize', updateViewportState)
  const [cats, whs, users, mappings] = await Promise.all([
    categoryApi.list(),
    warehouseApi.list(),
    authApi.listUsers(),
    productTypeCategoryMappingApi.list()
  ])
  categories.value = cats
  warehouses.value = whs
  productTypes.value = buildProductTypeOptionsFromMappings(mappings)
  ownerUsers.value = users
  listingCategoryMappings.value = mappings
  syncCascaderPathByProductTypeId(form.value.product_type_id)
  await Promise.all([load(), loadInventoryStats()])
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateViewportState)
  stopScan()
  stopContScan()
})
</script>

<style scoped>
.section-card { margin-bottom: 16px; border-radius: 8px; }
.inventory-stats-wrap { margin-bottom: 16px; }
.inventory-stat-row { margin-bottom: 0; }
.stat-row .el-col { margin-bottom: 16px; }
.inv-stat-card {
  background: #131c2f;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-top: 3px solid;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  border: 1px solid #2a3446;
}
.inv-stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.inv-stat-value { font-size: 22px; font-weight: 700; color: #ecf2ff; }
.inv-stat-label { font-size: 12px; color: #9ba8bf; margin-top: 2px; }
.search-card { margin-bottom: 16px; border-radius: 8px; }
.search-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; }
.search-actions--ios {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}
.search-actions-ios-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  width: 100%;
  justify-content: stretch;
}
.search-actions-ios-row :deep(.el-button) {
  flex: 1;
  min-width: 0;
  margin: 0;
}
.search-row {
  justify-content: space-between;
}
.search-left-group {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 20px;
}
.search-filters-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 20px;
  flex-shrink: 0;
}
.search-input-control,
.search-select-control {
  width: 180px;
  max-width: 180px;
}
.search-filters-row .search-select-control {
  width: 180px;
  max-width: 180px;
}
.product-field-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  flex-wrap: wrap;
}
.product-field-inline__main {
  flex: 1;
  min-width: 0;
}
.product-field-inline :deep(.el-select),
.product-field-inline :deep(.el-input) {
  width: 100%;
}
.product-qty-input {
  width: 30px;
}
.product-qty-input :deep(.el-input__wrapper) {
  padding-left: 1px;
  padding-right: 1px;
  justify-content: center;
}
.product-qty-input :deep(input) {
  text-align: center;
}
.table-card { border-radius: 8px; }
/* 与订单页 #/orders 列表缩略图一致 */
.order-thumb {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  display: block;
}
.thumb-fallback {
  color: #909399;
  font-size: 12px;
}
.table-scroll { width: 100%; overflow-x: auto; }
.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.editable-cell {
  min-height: 24px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.editable-cell:hover {
  background: rgba(64, 158, 255, 0.12);
}
.inline-input { width: 100%; }
.cell-center { text-align: center; }
.cell-right { text-align: right; }
.cell-muted { color: #909399; font-size: 13px; }
.multi-line-cell {
  display: flex;
  flex-direction: column;
}
.multi-line-cell > div {
  min-height: 30px;
  line-height: 30px;
  box-sizing: border-box;
}
.multi-line-cell--compact > div {
  min-height: 22px;
  line-height: 22px;
}
/* ---- 库存展开：二级表格 ---- */
.inventory-expand-wrap {
  padding: 8px 12px 12px 48px;
  min-height: 48px;
}
.inventory-expand-inner-table {
  width: 100%;
}

/* ---- 编辑弹窗：煤炉商品ID 列表编辑器 ---- */
.mercari-id-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.mercari-id-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mercari-id-input {
  flex: 1;
}
.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}

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
.image-upload-area.large {
  width: 100%;
  height: 180px;
}
.image-upload-area:hover { border-color: #409EFF; }
.preview-img { width: 100%; height: 100%; object-fit: cover; }
.upload-placeholder { text-align: center; }
.upload-tip { font-size: 12px; color: #8e9bb3; margin-top: 8px; }
.img-label { font-size: 13px; color: #8e9bb3; margin-bottom: 8px; }
.img-actions { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
.scanning-hint { color: #409EFF; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* ---- OCR ---- */
.ocr-hint { font-size: 13px; color: #8e9bb3; text-align: center; margin-bottom: 10px; }
.ocr-img-tabs { display: flex; gap: 8px; margin-bottom: 10px; }
.ocr-canvas-wrap { width: 100%; background: #000; border-radius: 6px; overflow: hidden; }
.ocr-canvas { display: block; width: 100%; cursor: crosshair; touch-action: none; user-select: none; }
.ocr-loading { text-align: center; padding: 10px 0; }

/* ---- 连续扫码结果区 ---- */
.header-actions { display: flex; gap: 10px; }
.barcode-tag {
  display: inline-flex; align-items: center; gap: 8px;
  background: #1e2d42; border: 1px solid #3b4961; border-radius: 20px;
  padding: 6px 16px; font-size: 15px; font-weight: 600;
  color: #7eb8f7; margin-bottom: 16px;
}
.product-images-row {
  display: flex; gap: 12px; justify-content: center; margin-bottom: 14px;
}
.result-img-wrap {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.img-side-label { font-size: 11px; color: #8e9bb3; }
.result-img { width: 130px; height: 130px; object-fit: cover; border-radius: 8px; border: 1px solid #2d3f56; }
.no-image-placeholder {
  display: flex; flex-direction: column; align-items: center;
  color: #4a5a72; padding: 20px;
}
.product-meta {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 4px;
}
.product-meta-name { font-size: 15px; font-weight: 600; color: #c8d8f0; }
.cont-quantity-row {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.cont-quantity-label { color: #8e9bb3; font-size: 13px; }
.notfound-box {
  display: flex; flex-direction: column; align-items: center;
  padding: 24px 0; color: #e6a23c;
}
.notfound-box p { margin-top: 10px; font-size: 15px; }
.cont-result { display: flex; flex-direction: column; align-items: center; padding: 8px 0 4px; }
.cont-actions { display: flex; gap: 14px; margin-top: 20px; }
.ios-fallback-box { display: flex; flex-direction: column; align-items: center; padding: 32px 0; }
.cont-https-hint {
  color: #e6a23c;
  font-size: 13px;
  line-height: 1.55;
  text-align: left;
  max-width: 100%;
  margin: 0 0 12px;
  padding: 10px 12px;
  background: rgba(230, 162, 60, 0.12);
  border-radius: 8px;
  border: 1px solid rgba(230, 162, 60, 0.35);
}
.cont-https-hint code { font-size: 12px; }

.scan-box { display: flex; flex-direction: column; gap: 10px; }
.camera-device-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.camera-device-label {
  flex-shrink: 0;
  color: #9aa7be;
  font-size: 13px;
}
.camera-device-select {
  flex: 1;
  min-width: 0;
}
.scan-video {
  width: 100%;
  max-height: 360px;
  border-radius: 8px;
  background: #000;
  border: 1px solid #2a3446;
}
.scan-tip { color: #9aa7be; font-size: 13px; text-align: center; }

/* 编辑商品弹窗底部：一行内排完 OCR / 删除 / 取消 / 保存 */
.product-dialog-footer {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  box-sizing: border-box;
}
.product-dialog-footer__left,
.product-dialog-footer__right {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.product-price-input {
  width: 100%;
  max-width: 100%;
}

@media (max-width: 768px) {
  .search-card :deep(.el-row) {
    row-gap: 8px;
  }
  .search-left-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }
  .search-input-control {
    width: 100%;
    max-width: none;
  }
  .search-filters-row {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    gap: 8px;
    width: 100%;
  }
  .search-filters-row .search-select-control {
    flex: 1;
    width: 0;
    min-width: 0;
    max-width: none;
  }
  .search-actions {
    justify-content: stretch;
  }
  /* 非 iOS 小屏：保持纵向满宽按钮，与原先一致 */
  .search-actions:not(.search-actions--ios) {
    flex-direction: column;
    align-items: stretch;
  }
  .search-actions:not(.search-actions--ios) :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }
  .search-actions--ios {
    margin-top: 4px;
  }
  .table-scroll {
    -webkit-overflow-scrolling: touch;
  }
  .row-actions {
    gap: 4px;
  }
  .row-actions :deep(.el-button) {
    padding: 5px 8px;
  }
  .add-btn {
    width: 100%;
  }
  .image-upload-area.large {
    height: 150px;
  }
  .product-dialog-footer {
    flex-wrap: nowrap;
    gap: 6px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 2px;
  }
  .product-dialog-footer :deep(.el-button) {
    flex-shrink: 0;
  }
  :deep(.product-dialog .el-dialog),
  :deep(.scan-dialog .el-dialog) {
    margin-top: 6vh !important;
  }
  :deep(.product-dialog .el-dialog__body),
  :deep(.scan-dialog .el-dialog__body) {
    padding: 14px;
  }
}
</style>

<!-- 无 scoped：须覆盖 App.vue 全局 `.el-input { width: 180px !important }`，否则标题与商品说明不同宽 -->
<style>
.product-dialog .listing-field-fullwidth.el-input {
  width: 100% !important;
  max-width: 100%;
}

.product-dialog .product-price-input {
  width: 100% !important;
  max-width: 100%;
}

.inventory-inline-select {
  width: 100% !important;
}

.inventory-inline-select-popper {
  min-width: 120px !important;
}

.product-type-cascader-popper .el-cascader-menu {
  height: 300px !important;
}

.product-type-cascader-popper .el-cascader-menu__wrap {
  height: 300px !important;
  max-height: 300px !important;
}

.product-type-cascader-popper .el-scrollbar__wrap {
  height: 300px !important;
  max-height: 300px !important;
}

.product-type-cascader-popper .el-cascader-menu__list {
  min-height: 300px !important;
}

.listing-pick-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.listing-pick-count {
  font-size: 13px;
  color: #67C23A;
  font-weight: 600;
  margin-right: 4px;
}
/* 选择模式下：选中行整行浅绿色覆盖（含固定列），80% 透明（alpha 0.2） */
.el-table tr.listing-pick-row-selected > td.el-table__cell {
  background-color: rgba(103, 194, 58, 0.2) !important;
  cursor: pointer;
}
.el-table tr.listing-pick-row-selected:hover > td.el-table__cell,
.el-table tr.listing-pick-row-selected.hover-row > td.el-table__cell {
  background-color: rgba(103, 194, 58, 0.32) !important;
}
.el-table tbody tr.listing-pick-row-disabled {
  cursor: not-allowed !important;
  opacity: 0.55;
}
/* 选择模式下，整张表行的鼠标指针变为可点击 */
.listing-pick-mode-active .el-table tbody tr {
  cursor: pointer;
}
</style>
