<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>疑难病例讨论</span>
          <el-button type="primary" @click="showDialog()">新增记录</el-button>
        </div>
      </template>
      <el-row :gutter="12" style="margin-bottom:16px">
        <el-col :span="8">
          <el-date-picker v-model="dateRange" type="daterange" start-placeholder="开始日期"
            end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="loadList">查询</el-button>
        </el-col>
      </el-row>
      <el-table :data="list" stripe>
        <el-table-column prop="record_no" label="记录编号" width="170" />
        <el-table-column prop="discussion_date" label="日期" width="110" />
        <el-table-column prop="patient_name" label="患者姓名" width="100" />
        <el-table-column prop="diagnosis" label="诊断" width="150" />
        <el-table-column prop="moderator" label="主持人" width="100" />
        <el-table-column prop="speaker" label="主讲人" width="100" />
        <el-table-column prop="participant_count" label="参加人数" width="90" />
        <el-table-column prop="location" label="地点" width="140" show-overflow-tooltip />
        <el-table-column prop="discussion_purpose" label="讨论目的" width="160" show-overflow-tooltip />
        <el-table-column prop="discussion_content" label="讨论内容" show-overflow-tooltip />
        <el-table-column prop="participants" label="参与人员" width="150" />
        <el-table-column prop="conclusion" label="结论" show-overflow-tooltip />
        <el-table-column prop="creator_name" label="记录人" width="80" />
        <el-table-column label="操作" width="260">
          <template #default="{ row }">
            <el-button type="warning" link @click="handlePrintPreview(row)">打印预览</el-button>
            <el-button type="success" link @click="handleExport(row)">导出Word</el-button>
            <el-button type="primary" link @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button type="danger" link>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑讨论记录' : '新增讨论记录'"
      width="1080px"
      top="3vh"
      class="record-dialog"
    >
      <el-form :model="form" label-position="top" class="record-form">
        <div class="paper-sheet">
          <div class="paper-title">疑难病例讨论记录</div>
          <div class="paper-subtitle">科室疑难病例讨论书面记录单</div>

          <div class="meta-grid meta-grid-discussion">
            <div class="meta-item meta-item-wide">
              <div class="meta-label">关联任务</div>
              <div class="meta-control">
                <el-select v-model="form.task_id" placeholder="选择关联任务（可选）" clearable style="width:100%">
                  <el-option v-for="t in myTasks" :key="t.id" :label="t.title" :value="t.id" />
                </el-select>
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">记录编号</div>
              <div class="meta-control">
                <el-input v-model="form.record_no" placeholder="留空则自动生成" />
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">讨论日期</div>
              <div class="meta-control">
                <el-date-picker v-model="form.discussion_date" value-format="YYYY-MM-DD" style="width:100%" />
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">患者姓名</div>
              <div class="meta-control">
                <el-input v-model="form.patient_name" placeholder="请输入患者姓名" />
              </div>
            </div>
            <div class="meta-item meta-item-wide">
              <div class="meta-label">临床诊断</div>
              <div class="meta-control">
                <el-input v-model="form.diagnosis" placeholder="请输入主要诊断或并发症情况" />
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">讨论主持人</div>
              <div class="meta-control">
                <el-input v-model="form.moderator" placeholder="请输入讨论主持人" />
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">主讲人</div>
              <div class="meta-control">
                <el-input v-model="form.speaker" placeholder="请输入主讲人或病例汇报人" />
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">讨论地点</div>
              <div class="meta-control">
                <el-input v-model="form.location" placeholder="请输入讨论地点" />
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">参加人数</div>
              <div class="meta-control">
                <el-input-number v-model="form.participant_count" :min="0" controls-position="right" style="width:100%" />
              </div>
            </div>
            <div class="meta-item meta-item-full">
              <div class="meta-label">讨论目的</div>
              <div class="meta-control">
                <el-input v-model="form.discussion_purpose" placeholder="请输入本次讨论的主要目的或待解决问题" />
              </div>
            </div>
            <div class="meta-item meta-item-full">
              <div class="meta-label">参与人员</div>
              <div class="meta-control">
                <el-input v-model="form.participants" placeholder="请输入参与人员，多人可用逗号分隔" />
              </div>
            </div>
          </div>

          <div class="print-block">
            <div class="print-block-title">病例信息摘要</div>
            <el-input
              v-model="form.case_info"
              type="textarea"
              :rows="10"
              resize="none"
              placeholder="请填写病史、检查结果、治疗经过、当前问题等病例摘要"
            />
          </div>

          <div class="print-block">
            <div class="print-block-title">讨论内容</div>
            <el-input
              v-model="form.discussion_content"
              type="textarea"
              :rows="14"
              resize="none"
              placeholder="请详细填写病例讨论过程、各方观点、分析重点和诊疗思路"
            />
          </div>

          <div class="print-block">
            <div class="print-block-title">讨论结论与处理意见</div>
            <el-input
              v-model="form.conclusion"
              type="textarea"
              :rows="10"
              resize="none"
              placeholder="请填写形成的结论、后续处理意见、处理方案或整改措施"
            />
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { discussionApi, taskApi } from "../api"
import { ElMessage } from "element-plus"
import { openRecordPrintPreview } from "../utils/recordPrint"

const list = ref([])
const myTasks = ref([])
const dateRange = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const emptyForm = { task_id: null, record_no: "", discussion_date: "", patient_name: "", diagnosis: "", moderator: "", speaker: "", location: "", participant_count: 0, discussion_purpose: "", case_info: "", discussion_content: "", participants: "", conclusion: "" }
const form = ref({ ...emptyForm })

function downloadBlob(res, filename) {
  const url = URL.createObjectURL(new Blob([res.data]))
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function loadList() {
  const params = {}
  if (dateRange.value) { params.start = dateRange.value[0]; params.end = dateRange.value[1] }
  const res = await discussionApi.list(params)
  list.value = res.data
}

function showDialog(row) {
  if (row) {
    isEdit.value = true; editId.value = row.id
    form.value = { task_id: row.task_id, record_no: row.record_no || "", discussion_date: row.discussion_date, patient_name: row.patient_name, diagnosis: row.diagnosis, moderator: row.moderator, speaker: row.speaker || "", location: row.location, participant_count: row.participant_count || 0, discussion_purpose: row.discussion_purpose || "", case_info: row.case_info, discussion_content: row.discussion_content, participants: row.participants, conclusion: row.conclusion }
  } else {
    isEdit.value = false; editId.value = null; form.value = { ...emptyForm }
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.discussion_date) { ElMessage.warning("请选择日期"); return }
  if (isEdit.value) { await discussionApi.update(editId.value, form.value); ElMessage.success("已更新") }
  else { await discussionApi.create(form.value); ElMessage.success("已创建") }
  dialogVisible.value = false; loadList()
}

async function handleDelete(id) { await discussionApi.delete(id); ElMessage.success("已删除"); loadList() }

async function handleExport(row) {
  try {
    const res = await discussionApi.exportWord(row.id)
    downloadBlob(res, `${row.record_no || row.patient_name || "疑难病例讨论记录"}.docx`)
    ElMessage.success("导出成功")
  } catch (e) { /* handled */ }
}

function handlePrintPreview(row) {
  try {
    const recordNo = row.record_no || ""
    openRecordPrintPreview({
      title: "疑难病例讨论记录",
      subtitle: "科室疑难病例讨论打印版",
      fileTitle: `${recordNo || row.patient_name || "疑难病例讨论记录"}_打印预览`,
      metaRows: [
        ["记录编号", recordNo, "讨论日期", row.discussion_date || ""],
        ["患者姓名", row.patient_name || "", "临床诊断", row.diagnosis || ""],
        ["讨论主持人", row.moderator || "", "主讲人", row.speaker || ""],
        ["参加人数", row.participant_count || "", "讨论地点", row.location || ""],
        ["讨论目的", row.discussion_purpose || "", "记录人", row.creator_name || ""],
        ["参与人员", row.participants || "", "", ""],
      ],
      sections: [
        { heading: "病例信息摘要", content: row.case_info || "" },
        { heading: "讨论内容", content: row.discussion_content || "" },
        { heading: "讨论结论与处理意见", content: row.conclusion || "" },
      ],
      signatures: [{ label: "记录人签名" }, { label: "审核人签名" }, { label: "日期" }],
      footerText: `文书编号：${recordNo || "待系统生成"}    打印日期：${new Date().toLocaleDateString("zh-CN")}`,
    })
  } catch (e) {
    ElMessage.warning("打印预览窗口被浏览器拦截，请允许弹出窗口后重试")
  }
}

onMounted(async () => {
  loadList()
  const res = await taskApi.list({ type: "discussion" })
  myTasks.value = res.data.filter(t => t.status !== "completed")
})
</script>

<style scoped>
.record-form {
  padding-top: 4px;
}

.paper-sheet {
  padding: 20px 22px 24px;
  border: 1px solid #dcdfe6;
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%);
}

.paper-title {
  text-align: center;
  font-size: 24px;
  font-weight: 700;
  color: #1f2d3d;
  letter-spacing: 1px;
}

.paper-subtitle {
  margin: 6px 0 18px;
  text-align: center;
  font-size: 13px;
  color: #606266;
}

.meta-grid {
  display: grid;
  gap: 0;
  border: 1px solid #dcdfe6;
  background: #fff;
}

.meta-grid-discussion {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.meta-item {
  border-right: 1px solid #dcdfe6;
  border-bottom: 1px solid #dcdfe6;
}

.meta-item-wide {
  grid-column: span 2;
}

.meta-item-full {
  grid-column: 1 / -1;
}

.meta-label {
  padding: 10px 12px 6px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  background: #f7f9fc;
}

.meta-control {
  padding: 10px 12px 12px;
}

.print-block {
  margin-top: 18px;
}

.print-block-title {
  margin-bottom: 8px;
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-bottom: none;
  background: #f7f9fc;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

:deep(.record-dialog .el-dialog__body) {
  max-height: 78vh;
  overflow-y: auto;
  padding-top: 10px;
}

:deep(.record-dialog .el-form-item__label) {
  font-weight: 600;
}

:deep(.paper-sheet .el-textarea__inner),
:deep(.paper-sheet .el-input__wrapper) {
  border-radius: 0;
}

:deep(.print-block .el-textarea__inner) {
  border-radius: 0;
  border-color: #dcdfe6;
}
</style>
