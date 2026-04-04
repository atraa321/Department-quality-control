<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>出院患者回访</span>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="待回访患者" name="todo">
          <el-row :gutter="12" style="margin-bottom:16px">
            <el-col :span="8">
              <el-date-picker v-model="dateRange" type="daterange" start-placeholder="出院开始"
                end-placeholder="出院结束" value-format="YYYY-MM-DD" style="width:100%" />
            </el-col>
            <el-col :span="4"><el-button type="primary" @click="loadPatients">查询</el-button></el-col>
          </el-row>
          <el-table :data="patients" stripe>
            <el-table-column prop="patient_name" label="患者姓名" width="100" />
            <el-table-column prop="record_no" label="病案号" width="120" />
            <el-table-column prop="phone" label="电话" width="140" />
            <el-table-column prop="address" label="住址" min-width="220" show-overflow-tooltip />
            <el-table-column prop="diagnosis" label="诊断" show-overflow-tooltip />
            <el-table-column prop="discharge_date" label="出院日期" width="110" />
            <el-table-column prop="attending_doctor" label="主管医师" width="100" />
            <el-table-column label="医师回访" width="90">
              <template #default="{ row }">
                <el-tag :type="row.doctor_followup_done ? 'success' : 'danger'" size="small">
                  {{ row.doctor_followup_done ? "已回访" : "未回访" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="护士回访" width="90">
              <template #default="{ row }">
                <el-tag :type="row.nurse_followup_done ? 'success' : 'danger'" size="small">
                  {{ row.nurse_followup_done ? "已回访" : "未回访" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" link @click="showFollowupDialog(row)">回访</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="回访记录" name="records">
          <el-row :gutter="12" style="margin-bottom:16px">
            <el-col :span="8">
              <el-date-picker v-model="recordDateRange" type="daterange" start-placeholder="回访开始"
                end-placeholder="回访结束" value-format="YYYY-MM-DD" style="width:100%" />
            </el-col>
            <el-col :span="4"><el-button type="primary" @click="loadFollowups">查询</el-button></el-col>
          </el-row>
          <el-table :data="followups" stripe>
            <el-table-column prop="followup_date" label="回访日期" width="110" />
            <el-table-column prop="patient_name" label="患者姓名" width="100" />
            <el-table-column label="回访方式" width="90">
              <template #default="{ row }">{{ methodLabel(row.followup_method) }}</template>
            </el-table-column>
            <el-table-column prop="feedback" label="患者反馈" show-overflow-tooltip />
            <el-table-column label="满意度" width="80">
              <template #default="{ row }">
                <el-rate v-model="row.satisfaction" disabled size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="followup_by_name" label="回访人" width="80" />
            <el-table-column label="需关注" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.needs_attention" type="danger" size="small">是</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" link @click="showEditDialog(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="工作量统计" name="stats">
          <el-row :gutter="12" style="margin-bottom:16px">
            <el-col :span="8">
              <el-date-picker v-model="statsDateRange" type="daterange" start-placeholder="开始"
                end-placeholder="结束" value-format="YYYY-MM-DD" style="width:100%" />
            </el-col>
            <el-col :span="4"><el-button type="primary" @click="loadStats">统计</el-button></el-col>
          </el-row>
          <el-table :data="statsData" stripe>
            <el-table-column prop="real_name" label="姓名" width="120" />
            <el-table-column label="角色" width="80">
              <template #default="{ row }">{{ row.role === "nurse" ? "护士" : "医师" }}</template>
            </el-table-column>
            <el-table-column prop="count" label="回访次数" width="100" />
            <el-table-column prop="avg_satisfaction" label="平均满意度" width="120" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 回访对话框 -->
    <el-dialog v-model="followupDialog" :title="isEditMode ? '编辑回访' : '登记回访'" width="550px">
      <div v-if="!isEditMode" style="margin-bottom:16px;padding:12px;background:#f5f7fa;border-radius:8px">
        <div><strong>{{ currentPatient.patient_name }}</strong> | {{ currentPatient.diagnosis }} | 出院：{{ currentPatient.discharge_date }}</div>
        <div style="margin-top:6px;color:#606266">电话：{{ currentPatient.phone || "未登记" }}</div>
        <div style="margin-top:4px;color:#606266">住址：{{ currentPatient.address || "未登记" }}</div>
      </div>
      <el-form :model="followupForm" label-width="90px">
        <el-form-item label="回访日期"><el-date-picker v-model="followupForm.followup_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="回访方式">
          <el-radio-group v-model="followupForm.followup_method">
            <el-radio value="phone">电话</el-radio>
            <el-radio value="visit">上门</el-radio>
            <el-radio value="online">线上</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="患者反馈"><el-input v-model="followupForm.feedback" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="满意度"><el-rate v-model="followupForm.satisfaction" /></el-form-item>
        <el-form-item label="意见建议"><el-input v-model="followupForm.suggestions" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="需重点关注"><el-switch v-model="followupForm.needs_attention" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="followupDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveFollowup">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { patientApi, followupApi } from "../api"
import { ElMessage } from "element-plus"

const activeTab = ref("todo")
const dateRange = ref(null)
const recordDateRange = ref(null)
const statsDateRange = ref(null)
const patients = ref([])
const followups = ref([])
const statsData = ref([])
const followupDialog = ref(false)
const isEditMode = ref(false)
const editFollowupId = ref(null)
const currentPatient = ref({})
const emptyFollowup = { patient_id: null, followup_date: "", followup_method: "phone", feedback: "", satisfaction: 5, suggestions: "", needs_attention: false }
const followupForm = ref({ ...emptyFollowup })

function methodLabel(m) { return { phone: "电话", visit: "上门", online: "线上" }[m] || m }

async function loadPatients() {
  const params = {}
  if (dateRange.value) { params.start = dateRange.value[0]; params.end = dateRange.value[1] }
  const res = await patientApi.list(params)
  patients.value = res.data
}

async function loadFollowups() {
  const params = {}
  if (recordDateRange.value) { params.start = recordDateRange.value[0]; params.end = recordDateRange.value[1] }
  const res = await followupApi.list(params)
  followups.value = res.data
}

async function loadStats() {
  const params = {}
  if (statsDateRange.value) { params.start = statsDateRange.value[0]; params.end = statsDateRange.value[1] }
  const res = await followupApi.stats(params)
  statsData.value = res.data
}

function showFollowupDialog(patient) {
  isEditMode.value = false; editFollowupId.value = null
  currentPatient.value = patient
  followupForm.value = { ...emptyFollowup, patient_id: patient.id }
  followupDialog.value = true
}

function showEditDialog(row) {
  isEditMode.value = true; editFollowupId.value = row.id
  followupForm.value = { followup_date: row.followup_date, followup_method: row.followup_method, feedback: row.feedback, satisfaction: row.satisfaction, suggestions: row.suggestions, needs_attention: row.needs_attention }
  followupDialog.value = true
}

async function handleSaveFollowup() {
  if (!followupForm.value.followup_date) { ElMessage.warning("请选择回访日期"); return }
  if (isEditMode.value) {
    await followupApi.update(editFollowupId.value, followupForm.value)
    ElMessage.success("已更新"); loadFollowups()
  } else {
    await followupApi.create(followupForm.value)
    ElMessage.success("回访已登记"); loadPatients()
  }
  followupDialog.value = false
}

onMounted(() => { loadPatients(); loadFollowups() })
</script>
