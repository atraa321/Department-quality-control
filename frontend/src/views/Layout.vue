<template>
  <el-container style="height: 100vh">
    <el-aside :width="isCollapsed ? '64px' : '220px'" style="transition: width 0.3s">
      <div class="logo" @click="isCollapsed = !isCollapsed">
        <el-icon size="24"><Monitor /></el-icon>
        <span v-show="!isCollapsed" style="margin-left:8px">质控平台</span>
      </div>
      <el-menu :default-active="$route.path" router :collapse="isCollapsed"
        background-color="#304156" text-color="#bfcbd9" active-text-color="#409EFF">
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/tasks">
          <el-icon><List /></el-icon>
          <template #title>任务分配</template>
        </el-menu-item>
        <el-menu-item index="/discussions">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>疑难病例讨论</template>
        </el-menu-item>
        <el-menu-item index="/studies">
          <el-icon><Reading /></el-icon>
          <template #title>业务学习</template>
        </el-menu-item>
        <el-menu-item index="/checks">
          <el-icon><Document /></el-icon>
          <template #title>病历质控检查</template>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/patients">
          <el-icon><Upload /></el-icon>
          <template #title>出院患者导入</template>
        </el-menu-item>
        <el-menu-item index="/followups">
          <el-icon><Phone /></el-icon>
          <template #title>出院患者回访</template>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/reports">
          <el-icon><TrendCharts /></el-icon>
          <template #title>数据汇总</template>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/users">
          <el-icon><UserFilled /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display:flex;align-items:center;justify-content:space-between;background:#fff;box-shadow:0 1px 4px rgba(0,21,41,.08)">
        <span style="font-size:16px;font-weight:500">{{ pageTitle }}</span>
        <div style="display:flex;align-items:center;gap:16px">
          <span>{{ userStore.user?.real_name }}（{{ roleLabel }}）</span>
          <el-button text @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main style="background:#f0f2f5;overflow-y:auto">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useUserStore } from "../stores/user"

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isCollapsed = ref(false)

const isAdmin = computed(() => userStore.isAdmin)
const roleLabel = computed(() => {
  const m = { admin: "管理员", doctor: "医师", nurse: "护士" }
  return m[userStore.user?.role] || ""
})

const titleMap = {
  "/dashboard": "工作台",
  "/tasks": "任务分配",
  "/discussions": "疑难病例讨论",
  "/studies": "业务学习",
  "/checks": "病历质控检查",
  "/patients": "出院患者导入",
  "/followups": "出院患者回访",
  "/reports": "数据汇总",
  "/users": "用户管理",
}
const pageTitle = computed(() => titleMap[route.path] || "科室质控平台")

function handleLogout() {
  userStore.logout()
  router.push("/login")
}
</script>

<style scoped>
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  background: #263445;
  cursor: pointer;
}
.el-aside {
  background: #304156;
  overflow: hidden;
}
</style>
