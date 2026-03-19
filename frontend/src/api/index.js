import axios from "axios"
import { ElMessage } from "element-plus"
import router from "../router"

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response) {
      const { status, data } = err.response
      if (status === 401) {
        localStorage.removeItem("token")
        localStorage.removeItem("user")
        router.push("/login")
        ElMessage.error("登录已过期，请重新登录")
      } else if (status === 403) {
        ElMessage.error(data.msg || "没有权限")
      } else {
        ElMessage.error(data.msg || "请求失败")
      }
    } else {
      ElMessage.error("网络连接失败")
    }
    return Promise.reject(err)
  }
)

export default api

// Auth
export const authApi = {
  login: (data) => api.post("/auth/login", data),
  me: () => api.get("/auth/me"),
  listUsers: () => api.get("/auth/users"),
  createUser: (data) => api.post("/auth/users", data),
  updateUser: (id, data) => api.put(`/auth/users/${id}`, data),
  changePassword: (data) => api.post("/auth/change-password", data),
}

// Tasks
export const taskApi = {
  list: (params) => api.get("/tasks", { params }),
  create: (data) => api.post("/tasks", data),
  get: (id) => api.get(`/tasks/${id}`),
  update: (id, data) => api.put(`/tasks/${id}`, data),
  delete: (id) => api.delete(`/tasks/${id}`),
  batchDelete: (ids) => api.post("/tasks/batch-delete", { ids }),
  myPending: () => api.get("/tasks/my-pending"),
  dashboardSummary: () => api.get("/tasks/dashboard-summary"),
}

// Discussions
export const discussionApi = {
  list: (params) => api.get("/discussions", { params }),
  create: (data) => api.post("/discussions", data),
  get: (id) => api.get(`/discussions/${id}`),
  update: (id, data) => api.put(`/discussions/${id}`, data),
  delete: (id) => api.delete(`/discussions/${id}`),
  exportWord: (id) => api.get(`/discussions/${id}/export-word`, { responseType: "blob" }),
}

// Studies
export const studyApi = {
  list: (params) => api.get("/studies", { params }),
  create: (data) => api.post("/studies", data),
  get: (id) => api.get(`/studies/${id}`),
  update: (id, data) => api.put(`/studies/${id}`, data),
  delete: (id) => api.delete(`/studies/${id}`),
  exportWord: (id) => api.get(`/studies/${id}/export-word`, { responseType: "blob" }),
}

// Checks
export const checkApi = {
  list: (params) => api.get("/checks", { params }),
  meta: () => api.get("/checks/meta"),
  stats: (params) => api.get("/checks/stats", { params }),
  create: (data) => api.post("/checks", data),
  get: (id) => api.get(`/checks/${id}`),
  update: (id, data) => api.put(`/checks/${id}`, data),
  delete: (id) => api.delete(`/checks/${id}`),
}

// Patients
export const patientApi = {
  list: (params) => api.get("/patients", { params }),
  import: (formData) => api.post("/patients/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }),
  preview: (formData) => api.post("/patients/preview", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }),
  template: () => api.get("/patients/template", { responseType: "blob" }),
  backup: () => api.get("/patients/backup", { responseType: "blob" }),
  batches: () => api.get("/patients/batches"),
  clearData: () => api.delete("/patients/clear"),
  delete: (id) => api.delete(`/patients/${id}`),
}

// Followups
export const followupApi = {
  list: (params) => api.get("/followups", { params }),
  create: (data) => api.post("/followups", data),
  get: (id) => api.get(`/followups/${id}`),
  update: (id, data) => api.put(`/followups/${id}`, data),
  delete: (id) => api.delete(`/followups/${id}`),
  stats: (params) => api.get("/followups/stats", { params }),
}

// Reports
export const reportApi = {
  summary: (params) => api.get("/reports/summary", { params }),
  exportExcel: (params) => api.get("/reports/export/excel", { params, responseType: "blob" }),
  exportWord: (params) => api.get("/reports/export/word", { params, responseType: "blob" }),
}
