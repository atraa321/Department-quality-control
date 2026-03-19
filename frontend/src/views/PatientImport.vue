<template>
  <div>
    <el-card style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px">
          <span>出院患者数据导入</span>
          <div style="display:flex;gap:8px">
            <el-button @click="backupData">数据备份</el-button>
            <el-popconfirm
              title="确认清空全部出院患者数据和回访记录？"
              confirm-button-text="确认清空"
              cancel-button-text="取消"
              @confirm="clearData"
            >
              <template #reference>
                <el-button type="danger">数据清除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </template>

      <el-row :gutter="16">
        <el-col :span="12">
          <h4>第1步：上传文件</h4>
          <el-upload ref="uploadRef" :auto-upload="false" :limit="1" :on-change="handleFileChange"
            accept=".xlsx,.xls,.csv" drag>
            <el-icon size="40"><Upload /></el-icon>
            <div>将文件拖到此处，或<em>点击上传</em></div>
            <template #tip><div class="el-upload__tip">支持 .xlsx / .csv 格式</div></template>
          </el-upload>
          <el-button style="margin-top:8px" @click="downloadTemplate">下载标准模板</el-button>
        </el-col>
        <el-col :span="12">
          <h4>第2步：列映射（自动匹配或手动选择）</h4>
          <div v-if="previewColumns.length">
            <el-form label-width="90px" size="small">
              <el-form-item v-for="(label, field) in fieldLabels" :key="field" :label="label">
                <el-select v-model="columnMap[field]" placeholder="选择对应列" clearable style="width:100%">
                  <el-option v-for="col in previewColumns" :key="col" :label="col" :value="col" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
          <div v-else style="color:#999;margin-top:20px">请先上传文件，系统将自动识别列名</div>
        </el-col>
      </el-row>

      <div v-if="sampleRows.length" style="margin-top:16px">
        <h4>数据预览（前5行）</h4>
        <el-table :data="sampleRows" size="small" border max-height="200">
          <el-table-column v-for="(col, i) in previewColumns" :key="i" :label="col" :prop="String(i)" min-width="100">
            <template #default="{ row }">{{ row[i] }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div style="margin-top:16px;text-align:right">
        <el-button type="primary" size="large" :loading="importing" :disabled="!selectedFile"
          @click="handleImport">确认导入</el-button>
      </div>
    </el-card>

    <el-card>
      <template #header><span>导入批次记录</span></template>
      <el-table :data="batches" stripe>
        <el-table-column prop="batch" label="批次号" />
        <el-table-column prop="count" label="导入数量" width="100" />
        <el-table-column prop="imported_at" label="导入时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { patientApi } from "../api"
import { ElMessage } from "element-plus"

const fieldLabels = {
  patient_name: "患者姓名", record_no: "病案号", gender: "性别", age: "年龄",
  diagnosis: "诊断", admission_date: "入院日期", discharge_date: "出院日期", attending_doctor: "主管医师",
}
const selectedFile = ref(null)
const previewColumns = ref([])
const sampleRows = ref([])
const columnMap = ref({})
const importing = ref(false)
const batches = ref([])

function handleFileChange(file) {
  selectedFile.value = file.raw
  previewFile(file.raw)
}

async function previewFile(file) {
  const fd = new FormData()
  fd.append("file", file)
  try {
    const res = await patientApi.preview(fd)
    previewColumns.value = res.data.columns
    sampleRows.value = res.data.sample_rows
    // 自动匹配列映射
    const reverseLabels = {}
    for (const [f, l] of Object.entries(fieldLabels)) reverseLabels[l] = f
    columnMap.value = {}
    for (const col of previewColumns.value) {
      if (reverseLabels[col]) columnMap.value[reverseLabels[col]] = col
    }
  } catch (e) { /* handled */ }
}

async function handleImport() {
  if (!selectedFile.value) return
  importing.value = true
  try {
    const fd = new FormData()
    fd.append("file", selectedFile.value)
    fd.append("column_map", JSON.stringify(columnMap.value))
    const res = await patientApi.import(fd)
    ElMessage.success(res.data.msg)
    loadBatches()
    selectedFile.value = null; previewColumns.value = []; sampleRows.value = []
  } catch (e) { /* handled */ }
  finally { importing.value = false }
}

async function downloadTemplate() {
  try {
    const res = await patientApi.template()
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement("a")
    a.href = url; a.download = "出院患者导入模板.xlsx"; a.click()
    URL.revokeObjectURL(url)
  } catch (e) { /* handled */ }
}

async function backupData() {
  try {
    const res = await patientApi.backup()
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement("a")
    a.href = url
    a.download = `出院患者数据备份_${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, "")}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success("数据备份已下载")
  } catch (e) { /* handled */ }
}

async function clearData() {
  try {
    const res = await patientApi.clearData()
    ElMessage.success(res.data.msg)
    selectedFile.value = null
    previewColumns.value = []
    sampleRows.value = []
    columnMap.value = {}
    loadBatches()
  } catch (e) { /* handled */ }
}

async function loadBatches() {
  const res = await patientApi.batches()
  batches.value = res.data
}

onMounted(loadBatches)
</script>
