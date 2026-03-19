<template>
  <div>
    <el-card style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>病历质控检查</span>
          <el-button type="primary" @click="showDialog()">新增检查</el-button>
        </div>
      </template>
      <el-row :gutter="12" style="margin-bottom:16px">
        <el-col :span="8">
          <el-date-picker v-model="dateRange" type="daterange" start-placeholder="开始日期"
            end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterRectified" placeholder="整改状态" clearable style="width:100%">
            <el-option label="待整改" value="pending" />
            <el-option label="已整改" value="rectified" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filterCategory" placeholder="问题分类" clearable style="width:100%">
            <el-option v-for="item in categories" :key="item.code" :label="item.label" :value="item.code" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filterDoctor" placeholder="责任医师" clearable style="width:100%">
            <el-option v-for="doctor in doctors" :key="doctor.id" :label="doctor.real_name" :value="doctor.id" />
          </el-select>
        </el-col>
        <el-col :span="4"><el-button type="primary" @click="reloadAll">查询</el-button></el-col>
      </el-row>

      <el-alert
        v-if="myTasks.length"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom:16px"
        :title="`当前待处理病历检查任务 ${myTasks.length} 条，可在新增检查时直接关联任务。`"
      />

      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="6">
          <el-card shadow="never"><div class="summary-line"><span>检查总数</span><strong>{{ stats.summary?.count || 0 }}</strong></div></el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never"><div class="summary-line"><span>严重问题</span><strong style="color:#f56c6c">{{ stats.summary?.serious || 0 }}</strong></div></el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never"><div class="summary-line"><span>已整改</span><strong style="color:#67c23a">{{ stats.summary?.rectified || 0 }}</strong></div></el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never"><div class="summary-line"><span>待整改</span><strong style="color:#e6a23c">{{ stats.summary?.pending || 0 }}</strong></div></el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header><span>按问题分类统计</span></template>
            <el-table :data="stats.category_stats || []" size="small" stripe>
              <el-table-column prop="label" label="分类" />
              <el-table-column prop="count" label="总数" width="70" />
              <el-table-column prop="serious" label="严重" width="70" />
              <el-table-column prop="rectified" label="已整改" width="80" />
              <el-table-column prop="pending" label="待整改" width="80" />
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header><span>按责任医师统计</span></template>
            <el-table :data="stats.doctor_stats || []" size="small" stripe>
              <el-table-column prop="doctor_name" label="责任医师" />
              <el-table-column prop="count" label="总数" width="70" />
              <el-table-column prop="rectified" label="已整改" width="80" />
              <el-table-column prop="pending" label="待整改" width="80" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-table :data="filteredList" stripe>
        <el-table-column prop="check_date" label="检查日期" width="110" />
        <el-table-column prop="record_no" label="病案号" width="120" />
        <el-table-column prop="patient_name" label="患者姓名" width="100" />
        <el-table-column prop="issue_category_label" label="问题分类" width="140" />
        <el-table-column prop="issue_template" label="预设问题" width="150" show-overflow-tooltip />
        <el-table-column prop="responsible_doctor_name" label="管床医师" width="100" />
        <el-table-column label="整改待办" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.rectification_task_id && !row.is_rectified" type="warning">已通知</el-tag>
            <el-tag v-else-if="row.is_rectified" type="success">已关闭</el-tag>
            <span v-else>未生成</span>
          </template>
        </el-table-column>
        <el-table-column prop="issue_found" label="发现问题" show-overflow-tooltip />
        <el-table-column label="严重程度" width="90">
          <template #default="{ row }">
            <el-tag :type="row.severity === 'serious' ? 'danger' : 'warning'">{{ row.severity === "serious" ? "严重" : "一般" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="整改状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_rectified ? 'success' : 'info'">{{ row.is_rectified ? "已整改" : "待整改" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rectified_date" label="整改日期" width="110" />
        <el-table-column prop="creator_name" label="检查人" width="80" />
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button type="primary" link @click="showDialog(row)">{{ canEditCoreFieldsForRow(row) || canRectifyRow(row) ? "编辑" : "查看" }}</el-button>
            <el-button v-if="canRectifyRow(row) && !row.is_rectified" type="success" link @click="handleRectify(row)">确认整改</el-button>
            <el-popconfirm v-if="canDelete(row)" title="确认删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button type="danger" link>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '病历检查记录' : '新增检查记录'" width="860px" top="4vh">
      <el-form :model="form" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="关联任务">
              <el-select v-model="form.task_id" placeholder="可选" clearable style="width:100%" :disabled="!canEditCoreFields" @change="handleTaskChange">
                <el-option v-for="t in myTasks" :key="t.id" :label="t.title" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检查日期"><el-date-picker v-model="form.check_date" value-format="YYYY-MM-DD" style="width:100%" :disabled="!canEditCoreFields" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="病案号"><el-input v-model="form.record_no" :disabled="!canEditCoreFields" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="患者姓名"><el-input v-model="form.patient_name" :disabled="!canEditCoreFields" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="问题分类">
              <el-select v-model="form.issue_category" style="width:100%" :disabled="!canEditCoreFields" @change="handleCategoryChange">
                <el-option v-for="item in categories" :key="item.code" :label="item.label" :value="item.code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="管床医师">
              <el-select v-model="form.responsible_doctor_id" placeholder="请选择管床医师" style="width:100%" :disabled="!canEditCoreFields">
                <el-option v-for="doctor in selectableDoctors" :key="doctor.id" :label="doctor.real_name" :value="doctor.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="预设问题模板">
          <el-select v-model="form.issue_template" placeholder="请选择预设问题模板" style="width:100%" :disabled="!canEditCoreFields" @change="applySelectedTemplate">
            <el-option v-for="template in currentTemplates" :key="template" :label="template" :value="template" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="canEditCoreFields" label="模板提示">
          <div class="template-help">
            <span v-for="template in currentTemplates" :key="template" class="template-chip" @click="quickFillTemplate(template)">{{ template }}</span>
          </div>
        </el-form-item>
        <el-form-item label="发现问题">
          <el-input v-model="form.issue_found" type="textarea" :rows="4" :disabled="!canEditCoreFields" placeholder="可在预设模板基础上补充具体问题描述" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="严重程度">
              <el-radio-group v-model="form.severity" :disabled="!canEditCoreFields">
                <el-radio value="general">一般问题</el-radio>
                <el-radio value="serious">严重问题</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="整改状态">
              <el-tag :type="form.is_rectified ? 'success' : 'info'">{{ form.is_rectified ? "已整改" : "待整改" }}</el-tag>
              <span v-if="form.rectified_by_name" style="margin-left:12px;color:#909399">整改人：{{ form.rectified_by_name }}</span>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="整改反馈">
          <el-input v-model="form.rectification_feedback" type="textarea" :rows="3" :disabled="!canRectify" placeholder="责任医师填写整改说明，确认整改后将显示为已整改" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remarks" type="textarea" :rows="3" :disabled="!canEditCoreFields" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button v-if="canRectify && !form.is_rectified" type="success" @click="handleSave(true)">确认整改</el-button>
        <el-button v-if="canEditCoreFields" type="primary" @click="handleSave(false)">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from "vue"
import { useRoute, useRouter } from "vue-router"
import { checkApi, taskApi } from "../api"
import { ElMessage, ElMessageBox } from "element-plus"
import { useUserStore } from "../stores/user"

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const list = ref([])
const stats = ref({ summary: {}, category_stats: [], doctor_stats: [] })
const myTasks = ref([])
const categories = ref([])
const doctors = ref([])
const dateRange = ref(null)
const filterRectified = ref("")
const filterCategory = ref("")
const filterDoctor = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const emptyForm = () => ({ task_id: null, check_date: "", record_no: "", patient_name: "", responsible_doctor_id: null, issue_category: "record_writing", issue_template: "", issue_found: "", severity: "general", rectification_feedback: "", rectification_status: "pending", is_rectified: false, rectified_date: null, rectified_by_name: "", remarks: "", created_by: null })
const form = ref(emptyForm())

const currentUser = computed(() => userStore.user || null)
const currentTemplates = computed(() => categories.value.find(item => item.code === form.value.issue_category)?.templates || [])
const selectableDoctors = computed(() => {
  if (currentUser.value?.role === "doctor") {
    return doctors.value.filter(doctor => doctor.id !== currentUser.value.id)
  }
  return doctors.value
})
const filteredList = computed(() => list.value.filter((item) => {
  const matchedRectified = !filterRectified.value || (filterRectified.value === "rectified" ? item.is_rectified : !item.is_rectified)
  const matchedCategory = !filterCategory.value || item.issue_category === filterCategory.value
  const matchedDoctor = !filterDoctor.value || item.responsible_doctor_id === filterDoctor.value
  return matchedRectified && matchedCategory && matchedDoctor
}))
const canEditCoreFields = computed(() => !isEdit.value || currentUser.value?.role === "admin" || form.value.created_by === currentUser.value?.id)
const canRectify = computed(() => !!isEdit.value && (currentUser.value?.role === "admin" || form.value.responsible_doctor_id === currentUser.value?.id))

function enrichItem(item) {
  const label = categories.value.find(category => category.code === item.issue_category)?.label || "其他问题"
  return { ...item, issue_category_label: label }
}

function canDelete(row) {
  return currentUser.value?.role === "admin" || row.created_by === currentUser.value?.id
}

function canEditCoreFieldsForRow(row) {
  return currentUser.value?.role === "admin" || row.created_by === currentUser.value?.id
}

function canRectifyRow(row) {
  return currentUser.value?.role === "admin" || row.responsible_doctor_id === currentUser.value?.id
}

async function loadMeta() {
  const res = await checkApi.meta()
  categories.value = res.data.categories || []
  doctors.value = res.data.doctors || []
}

async function loadList() {
  const params = {}
  if (dateRange.value) { params.start = dateRange.value[0]; params.end = dateRange.value[1] }
  if (route.query.taskId) { params.task_id = route.query.taskId }
  const res = await checkApi.list(params)
  list.value = res.data.map(enrichItem)
}

async function loadStats() {
  const params = {}
  if (dateRange.value) { params.start = dateRange.value[0]; params.end = dateRange.value[1] }
  const res = await checkApi.stats(params)
  stats.value = res.data
}

async function loadMyTasks() {
  const res = await taskApi.list({ type: "check" })
  myTasks.value = res.data.filter(t => t.status !== "completed" && t.title.includes("病历检查任务"))
}

async function reloadAll() {
  await Promise.all([loadList(), loadStats(), loadMyTasks()])
  await focusFromRoute()
}

async function focusFromRoute() {
  const checkId = route.query.checkId ? Number(route.query.checkId) : null
  const taskId = route.query.taskId ? Number(route.query.taskId) : null
  if (!checkId && !taskId) return

  let target = null
  if (checkId) {
    target = list.value.find(item => item.id === checkId) || null
  }
  if (!target && taskId) {
    target = list.value.find(item => item.task_id === taskId || item.rectification_task_id === taskId) || null
  }
  if (!target) return

  await nextTick()
  showDialog(target)
  router.replace({ path: "/checks", query: {} })
}

function handleCategoryChange() {
  const templates = currentTemplates.value
  if (!templates.includes(form.value.issue_template)) {
    form.value.issue_template = ""
  }
}

function quickFillTemplate(template) {
  form.value.issue_template = template
  form.value.issue_found = template
}

function applySelectedTemplate() {
  if (!form.value.issue_template) return
  if (!form.value.issue_found || form.value.issue_found === form.value.issue_template) {
    form.value.issue_found = form.value.issue_template
  }
}

function handleTaskChange(taskId) {
  if (!taskId) return
  const task = myTasks.value.find(item => item.id === taskId)
  if (!task) return
  if (!form.value.responsible_doctor_id && task.assigned_to) {
    form.value.responsible_doctor_id = task.assigned_to
  }
}

function showDialog(row) {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.value = {
      task_id: row.task_id,
      check_date: row.check_date,
      record_no: row.record_no,
      patient_name: row.patient_name,
      responsible_doctor_id: row.responsible_doctor_id,
      issue_category: row.issue_category,
      issue_template: row.issue_template || "",
      issue_found: row.issue_found,
      severity: row.severity,
      rectification_feedback: row.rectification_feedback || "",
      rectification_status: row.rectification_status || (row.is_rectified ? "rectified" : "pending"),
      is_rectified: row.is_rectified,
      rectified_date: row.rectified_date,
      rectified_by_name: row.rectified_by_name || "",
      remarks: row.remarks,
      created_by: row.created_by,
    }
  } else {
    isEdit.value = false
    editId.value = null
    form.value = emptyForm()
  }
  dialogVisible.value = true
}

async function handleSave(asRectified) {
  if (!form.value.check_date) { ElMessage.warning("请选择检查日期"); return }
  if (!form.value.issue_found) { ElMessage.warning("请填写发现问题"); return }
  if (!form.value.responsible_doctor_id) { ElMessage.warning("请选择管床医师"); return }

  const payload = {
    task_id: form.value.task_id,
    check_date: form.value.check_date,
    record_no: form.value.record_no,
    patient_name: form.value.patient_name,
    responsible_doctor_id: form.value.responsible_doctor_id,
    issue_category: form.value.issue_category,
    issue_template: form.value.issue_template,
    issue_found: form.value.issue_found,
    severity: form.value.severity,
    rectification_feedback: form.value.rectification_feedback,
    remarks: form.value.remarks,
  }
  if (asRectified) {
    payload.rectification_status = "rectified"
    payload.is_rectified = true
  }

  if (isEdit.value) {
    await checkApi.update(editId.value, payload)
    ElMessage.success(asRectified ? "已确认整改" : "已更新")
  } else {
    await checkApi.create(payload)
    ElMessage.success("已创建")
  }
  dialogVisible.value = false
  await reloadAll()
}

async function handleRectify(row) {
  try {
    const { value } = await ElMessageBox.prompt("请输入整改反馈，可留空", "确认整改", {
      inputType: "textarea",
      inputPlaceholder: "例如：已补全病程记录并重新审核",
      confirmButtonText: "确认整改",
      cancelButtonText: "取消",
    })
    await checkApi.update(row.id, {
      rectification_feedback: value || "",
      rectification_status: "rectified",
      is_rectified: true,
    })
    ElMessage.success("已确认整改")
    await reloadAll()
  } catch (e) {
    if (e !== "cancel") {
      // handled by interceptor
    }
  }
}

async function handleDelete(id) {
  await checkApi.delete(id)
  ElMessage.success("已删除")
  await reloadAll()
}

onMounted(async () => {
  await loadMeta()
  await reloadAll()
})
</script>

<style scoped>
.summary-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.summary-line strong {
  font-size: 20px;
}

.template-help {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.template-chip {
  padding: 4px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 999px;
  background: #f5f7fa;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s ease;
}

.template-chip:hover {
  border-color: #409eff;
  color: #409eff;
  background: #ecf5ff;
}
</style>
