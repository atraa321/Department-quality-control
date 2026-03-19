<template>
  <div>
    <el-card style="margin-bottom:16px">
      <template #header><span>数据汇总</span></template>
      <el-row :gutter="12" style="margin-bottom:16px">
        <el-col :span="8">
          <el-date-picker v-model="dateRange" type="daterange" start-placeholder="开始"
            end-placeholder="结束" value-format="YYYY-MM-DD" style="width:100%" />
        </el-col>
        <el-col :span="12">
          <el-button type="primary" @click="loadSummary">查询</el-button>
          <el-button @click="exportWord">导出Word汇总</el-button>
          <el-dropdown style="margin-left:8px">
            <el-button>导出Excel<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="exportExcel('discussions')">疑难病例讨论</el-dropdown-item>
                <el-dropdown-item @click="exportExcel('studies')">业务学习</el-dropdown-item>
                <el-dropdown-item @click="exportExcel('checks')">病历检查</el-dropdown-item>
                <el-dropdown-item @click="exportExcel('followups')">回访记录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="8">
          <el-card shadow="hover">
            <h4>任务完成</h4>
            <div class="stat-row"><span>总任务数</span><strong>{{ summary.tasks?.total || 0 }}</strong></div>
            <div class="stat-row"><span>已完成</span><strong style="color:#67C23A">{{ summary.tasks?.completed || 0 }}</strong></div>
            <div class="stat-row"><span>已过期</span><strong style="color:#F56C6C">{{ summary.tasks?.overdue || 0 }}</strong></div>
            <div class="stat-row"><span>完成率</span><strong>{{ summary.tasks?.completion_rate || 0 }}%</strong></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <h4>业务工作</h4>
            <div class="stat-row"><span>疑难讨论</span><strong>{{ summary.discussions?.count || 0 }} 次</strong></div>
            <div class="stat-row"><span>业务学习</span><strong>{{ summary.studies?.count || 0 }} 次</strong></div>
            <div class="stat-row"><span>病历检查</span><strong>{{ summary.checks?.count || 0 }} 份</strong></div>
            <div class="stat-row"><span>严重问题</span><strong style="color:#F56C6C">{{ summary.checks?.serious || 0 }}</strong></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <h4>出院回访</h4>
            <div class="stat-row"><span>出院患者</span><strong>{{ summary.patients?.count || 0 }} 人</strong></div>
            <div class="stat-row"><span>回访次数</span><strong>{{ summary.followups?.count || 0 }} 次</strong></div>
            <div class="stat-row"><span>平均满意度</span><strong style="color:#E6A23C">{{ summary.followups?.avg_satisfaction || 0 }} / 5</strong></div>
            <div class="stat-row"><span>已整改</span><strong style="color:#67C23A">{{ summary.checks?.rectified || 0 }}</strong></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top:16px">
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header><span>病历检查按分类统计</span></template>
            <el-table :data="summary.checks?.category_stats || []" size="small" stripe>
              <el-table-column prop="label" label="分类" />
              <el-table-column prop="count" label="总数" width="70" />
              <el-table-column prop="serious" label="严重" width="70" />
              <el-table-column prop="rectified" label="已整改" width="80" />
              <el-table-column prop="pending" label="待整改" width="80" />
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header><span>病历检查按责任医师统计</span></template>
            <el-table :data="summary.checks?.doctor_stats || []" size="small" stripe>
              <el-table-column prop="doctor_name" label="责任医师" />
              <el-table-column prop="count" label="总数" width="70" />
              <el-table-column prop="rectified" label="已整改" width="80" />
              <el-table-column prop="pending" label="待整改" width="80" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { reportApi } from "../api"
import { ElMessage } from "element-plus"

const dateRange = ref(null)
const summary = ref({})

async function loadSummary() {
  const params = {}
  if (dateRange.value) { params.start = dateRange.value[0]; params.end = dateRange.value[1] }
  const res = await reportApi.summary(params)
  summary.value = res.data
}

function downloadBlob(res, filename) {
  const url = URL.createObjectURL(new Blob([res.data]))
  const a = document.createElement("a"); a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

async function exportExcel(module) {
  const params = { module }
  if (dateRange.value) { params.start = dateRange.value[0]; params.end = dateRange.value[1] }
  try {
    const res = await reportApi.exportExcel(params)
    downloadBlob(res, `${module}.xlsx`)
    ElMessage.success("导出成功")
  } catch (e) { /* handled */ }
}

async function exportWord() {
  const params = {}
  if (dateRange.value) { params.start = dateRange.value[0]; params.end = dateRange.value[1] }
  try {
    const res = await reportApi.exportWord(params)
    downloadBlob(res, "科室质控汇总报告.docx")
    ElMessage.success("导出成功")
  } catch (e) { /* handled */ }
}

onMounted(loadSummary)
</script>

<style scoped>
.stat-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.stat-row:last-child { border-bottom: none; }
h4 { margin: 0 0 12px 0; color: #333; }
</style>
