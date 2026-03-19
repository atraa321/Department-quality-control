<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>任务分配管理</span>
          <div style="display:flex;gap:12px;align-items:center">
            <el-button type="danger" plain :disabled="selectedIds.length === 0" @click="handleBatchDelete">批量删除</el-button>
            <el-button type="primary" @click="showDialog()">批量分配任务</el-button>
          </div>
        </div>
      </template>
      <el-row :gutter="12" style="margin-bottom:16px">
        <el-col :span="6">
          <el-select v-model="filter.type" placeholder="任务类型" clearable style="width:100%">
            <el-option label="病例讨论" value="discussion" />
            <el-option label="业务学习" value="study" />
            <el-option label="病历检查" value="check" />
            <el-option label="患者回访" value="followup" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filter.status" placeholder="状态" clearable style="width:100%">
            <el-option label="待完成" value="pending" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已过期" value="overdue" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filter.assigned_to" placeholder="负责人" clearable style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.real_name" :value="u.id" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="loadTasks">查询</el-button>
        </el-col>
      </el-row>
      <el-table :data="tasks" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="title" label="标题" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">{{ typeLabel(row.type) }}</template>
        </el-table-column>
        <el-table-column prop="assignee_name" label="负责人" width="100" />
        <el-table-column label="来源" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.is_carryover" type="danger">结转任务</el-tag>
            <span v-else>本期生成</span>
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止日期" width="120" />
        <el-table-column prop="description" label="说明" width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button type="primary" link @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button type="danger" link>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑任务' : '批量分配任务'" width="560px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width:100%">
            <el-option label="病例讨论" value="discussion" />
            <el-option label="业务学习" value="study" />
            <el-option label="病历检查" value="check" />
            <el-option label="患者回访" value="followup" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="form.assigned_to" style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.real_name" :value="u.id" />
          </el-select>
        </el-form-item>
        <template v-if="isEdit">
          <el-form-item label="截止日期">
            <el-date-picker v-model="form.deadline" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item :label="quantityLabel">
            <el-input-number v-model="form.quantity" :min="1" :step="1" style="width:100%" />
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item>
        </template>
        <el-form-item v-if="!isEdit" label="说明">
          <span style="color:#909399;font-size:12px;line-height:1.6">{{ createHint }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue"
import { taskApi, authApi } from "../api"
import { ElMessage, ElMessageBox } from "element-plus"

const tasks = ref([])
const users = ref([])
const selectedIds = ref([])
const filter = ref({ type: "", status: "", assigned_to: null })
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const emptyCreateForm = () => ({ type: "discussion", description: "", assigned_to: null, quantity: 1, start_date: "", end_date: "" })
const emptyEditForm = () => ({ type: "discussion", description: "", assigned_to: null, deadline: "" })
const form = ref(emptyCreateForm())
const quantityLabel = computed(() => {
  if (form.value.type === "followup") return "病例总数"
  if (form.value.type === "check") return "病例数"
  return "任务数量"
})
const createHint = computed(() => {
  if (form.value.type === "followup") {
    return "患者回访按周生成任务，系统会把开始日期到结束日期按周拆分，并将填写的病例总数平均分配到各周。"
  }
  if (form.value.type === "check") {
    return "病历检查按周生成任务，系统会把日期范围按周拆分，并将填写的病例数平均分配到每周；本期未完成任务会在下一周自动结转为代办。"
  }
  return "系统会把开始日期到结束日期均分为指定份数，并取每一段的结束日期作为任务截止时间，标题自动生成。"
})

function typeLabel(t) {
  return { discussion: "病例讨论", study: "业务学习", check: "病历检查", followup: "患者回访" }[t] || t
}
function statusLabel(s) {
  return { pending: "待完成", in_progress: "进行中", completed: "已完成", overdue: "已过期" }[s] || s
}
function statusTag(s) {
  return { pending: "warning", in_progress: "", completed: "success", overdue: "danger" }[s] || ""
}

async function loadTasks() {
  const params = {}
  if (filter.value.type) params.type = filter.value.type
  if (filter.value.status) params.status = filter.value.status
  if (filter.value.assigned_to) params.assigned_to = filter.value.assigned_to
  const res = await taskApi.list(params)
  tasks.value = res.data
  selectedIds.value = []
}

function handleSelectionChange(rows) {
  selectedIds.value = rows.map(row => row.id)
}

function showDialog(row) {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.value = { type: row.type, description: row.description, assigned_to: row.assigned_to, deadline: row.deadline }
  } else {
    isEdit.value = false
    editId.value = null
    form.value = emptyCreateForm()
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (isEdit.value) {
    if (!form.value.assigned_to || !form.value.deadline) {
      ElMessage.warning("请填写完整信息")
      return
    }
    await taskApi.update(editId.value, form.value)
    ElMessage.success("更新成功")
  } else {
    if (!form.value.assigned_to || !form.value.quantity || !form.value.start_date || !form.value.end_date) {
      ElMessage.warning("请填写完整信息")
      return
    }
    const res = await taskApi.create(form.value)
    const count = res.data?.count || 1
    ElMessage.success(`已分配 ${count} 个任务`)
  }
  dialogVisible.value = false
  loadTasks()
}

async function handleDelete(id) {
  await taskApi.delete(id)
  ElMessage.success("已删除")
  loadTasks()
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning("请先选择要删除的任务")
    return
  }

  await ElMessageBox.confirm(
    `确认删除已选中的 ${selectedIds.value.length} 个任务吗？此操作不可恢复。`,
    "批量删除确认",
    {
      type: "warning",
      confirmButtonText: "确认删除",
      cancelButtonText: "取消",
    }
  )

  const res = await taskApi.batchDelete(selectedIds.value)
  ElMessage.success(`已删除 ${res.data?.count || selectedIds.value.length} 个任务`)
  loadTasks()
}

onMounted(async () => {
  loadTasks()
  const res = await authApi.listUsers()
  users.value = res.data.filter(u => u.is_active)
})
</script>
