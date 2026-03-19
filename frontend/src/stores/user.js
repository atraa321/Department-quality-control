import { defineStore } from "pinia"
import { authApi } from "../api"

export const useUserStore = defineStore("user", {
  state: () => ({
    user: JSON.parse(localStorage.getItem("user") || "null"),
    token: localStorage.getItem("token") || "",
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === "admin",
    isDoctor: (state) => state.user?.role === "doctor",
    isNurse: (state) => state.user?.role === "nurse",
  },
  actions: {
    async login(username, password) {
      const res = await authApi.login({ username, password })
      this.token = res.data.token
      this.user = res.data.user
      localStorage.setItem("token", this.token)
      localStorage.setItem("user", JSON.stringify(this.user))
    },
    logout() {
      this.token = ""
      this.user = null
      localStorage.removeItem("token")
      localStorage.removeItem("user")
    },
  },
})
