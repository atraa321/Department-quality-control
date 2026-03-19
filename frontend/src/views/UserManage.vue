<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>用户管理</span>
          <el-button type="primary" @click="showDialog()">新增用户</el-button>
        </div>
      </template>
      <el-table :data="users" stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="real_name" label="姓名" width="120" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'nurse' ? 'success' : ''">
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "禁用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button type="primary" link @click="showDialog(row)">编辑</el-button>
            <el-button type="warning" link @click="resetPassword(row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="420px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="form.username" :disabled="isEdit" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.real_name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="管理员" value="admin" />
            <el-option label="医师" value="doctor" />
            <el-option label="护士" value="nurse" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!isEdit" label="初始密码"><el-input v-model="form.password" placeholder="默认123456" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" /></el-form-item>
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
import { authApi } from "../api"
import { ElMessage, ElMessageBox } from "element-plus"

const users = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = ref({ username: "", real_name: "", role: "doctor", password: "", is_active: true })

function roleLabel(r) { return { admin: "管理员", doctor: "医师", nurse: "护士" }[r] || r }

async function loadUsers() {
  const res = await authApi.listUsers()
  users.value = res.data
}

function showDialog(row) {
  if (row) {
    isEdit.value = true; editId.value = row.id
    form.value = { username: row.username, real_name: row.real_name, role: row.role, password: "", is_active: row.is_active }
  } else {
    isEdit.value = false; editId.value = null
    form.value = { username: "", real_name: "", role: "doctor", password: "", is_active: true }
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.username || !form.value.real_name) { ElMessage.warning("请填写必要信息"); return }
  if (isEdit.value) {
    const data = { real_name: form.value.real_name, role: form.value.role, is_active: form.value.is_active }
    if (form.value.password) data.password = form.value.password
    await authApi.updateUser(editId.value, data)
    ElMessage.success("已更新")
  } else {
    await authApi.createUser({ ...form.value, password: form.value.password || "123456" })
    ElMessage.success("已创建")
  }
  dialogVisible.value = false; loadUsers()
}

async function resetPassword(row) {
  try {
    await ElMessageBox.confirm(`确认将 ${row.real_name} 的密码重置为 123456？`, "重置密码")
    await authApi.updateUser(row.id, { password: "123456" })
    ElMessage.success("密码已重置为 123456")
  } catch (e) { /* cancelled */ }
}

onMounted(loadUsers)
</script>
