import { createRouter, createWebHistory } from "vue-router"

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/Login.vue"),
  },
  {
    path: "/",
    component: () => import("../views/Layout.vue"),
    redirect: "/dashboard",
    children: [
      { path: "dashboard", name: "Dashboard", component: () => import("../views/Dashboard.vue") },
      { path: "tasks", name: "Tasks", component: () => import("../views/TaskManage.vue"), meta: { admin: true } },
      { path: "discussions", name: "Discussions", component: () => import("../views/CaseDiscussion.vue") },
      { path: "studies", name: "Studies", component: () => import("../views/BusinessStudy.vue") },
      { path: "checks", name: "Checks", component: () => import("../views/MedicalCheck.vue") },
      { path: "patients", name: "Patients", component: () => import("../views/PatientImport.vue"), meta: { admin: true } },
      { path: "followups", name: "Followups", component: () => import("../views/PatientFollowup.vue") },
      { path: "reports", name: "Reports", component: () => import("../views/Reports.vue"), meta: { admin: true } },
      { path: "users", name: "Users", component: () => import("../views/UserManage.vue"), meta: { admin: true } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("token")
  if (to.path !== "/login" && !token) {
    next("/login")
  } else if (to.meta.admin) {
    const user = JSON.parse(localStorage.getItem("user") || "{}")
    if (user.role !== "admin") {
      next("/dashboard")
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
