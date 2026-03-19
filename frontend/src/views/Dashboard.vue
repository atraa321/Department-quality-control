<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background:#409EFF"><el-icon size="28"><List /></el-icon></div>
            <div><div class="stat-num">{{ stats.pendingTasks }}</div><div class="stat-label">待完成任务</div></div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background:#E6A23C"><el-icon size="28"><Warning /></el-icon></div>
            <div><div class="stat-num" style="color:#E6A23C">{{ stats.overdueTasks }}</div><div class="stat-label">过期任务</div></div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background:#67C23A"><el-icon size="28"><CircleCheck /></el-icon></div>
            <div><div class="stat-num" style="color:#67C23A">{{ stats.completedTasks }}</div><div class="stat-label">已完成任务</div></div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background:#F56C6C"><el-icon size="28"><Phone /></el-icon></div>
            <div><div class="stat-num">{{ stats.pendingFollowups }}</div><div class="stat-label">待回访患者</div></div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 待办任务列表 -->
    <el-card>
      <template #header>
        <span style="font-weight:600">我的待办任务</span>
      </template>
      <el-table :data="pendingTasks" stripe empty-text="暂无待办任务">
        <el-table-column prop="title" label="任务标题" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.type)">{{ typeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deadline" label="截止日期" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_overdue ? 'danger' : 'warning'" effect="dark">
              {{ row.is_overdue ? "已过期" : "待完成" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link @click="goToTask(row)">去完成</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"
import { taskApi } from "../api"

const router = useRouter()
const pendingTasks = ref([])
const stats = ref({ pendingTasks: 0, overdueTasks: 0, completedTasks: 0, pendingFollowups: 0 })

function typeLabel(t) {
  return { discussion: "病例讨论", study: "业务学习", check: "病历检查", followup: "患者回访" }[t] || t
}
function typeTag(t) {
  return { discussion: "", study: "success", check: "warning", followup: "danger" }[t] || ""
}
function goToModule(type) {
  const map = { discussion: "/discussions", study: "/studies", check: "/checks", followup: "/followups" }
  router.push(map[type] || "/dashboard")
}

function goToTask(task) {
  if (task.type === "check") {
    const query = {}
    if (task.linked_check_id) query.checkId = String(task.linked_check_id)
    else if (task.id) query.taskId = String(task.id)
    router.push({ path: "/checks", query })
    return
  }
  goToModule(task.type)
}

onMounted(async () => {
  try {
    const res = await taskApi.dashboardSummary()
    pendingTasks.value = res.data.pending_tasks || []
    stats.value.pendingTasks = res.data.stats?.pending_tasks || 0
    stats.value.overdueTasks = res.data.stats?.overdue_tasks || 0
    stats.value.completedTasks = res.data.stats?.completed_tasks || 0
    stats.value.pendingFollowups = res.data.stats?.pending_followups || 0
  } catch (e) { /* handled */ }
})
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-icon {
  width: 56px; height: 56px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: white;
}
.stat-num { font-size: 28px; font-weight: 700; color: #333; }
.stat-label { font-size: 13px; color: #999; margin-top: 4px; }
</style>
