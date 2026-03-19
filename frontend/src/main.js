import { createApp } from "vue"
import { createPinia } from "pinia"
import ElementPlus from "element-plus"
import "element-plus/dist/index.css"
import zhCn from "element-plus/dist/locale/zh-cn.mjs"
import {
  ArrowDown,
  ChatDotRound,
  CircleCheck,
  DataAnalysis,
  Document,
  List,
  Monitor,
  Phone,
  Reading,
  TrendCharts,
  Upload,
  UserFilled,
  Warning,
} from "@element-plus/icons-vue"
import App from "./App.vue"
import router from "./router"

function bootstrapClientAuth() {
  const url = new URL(window.location.href)
  const token = url.searchParams.get("client_token")
  const rawUser = url.searchParams.get("client_user")
  const clientRoute = url.searchParams.get("client_route")

  if (token) {
    localStorage.setItem("token", token)

    if (rawUser) {
      try {
        const user = JSON.parse(rawUser)
        localStorage.setItem("user", JSON.stringify(user))
      } catch (error) {
        console.error("解析客户端用户信息失败", error)
      }
    }
  }

  url.searchParams.delete("client_token")
  url.searchParams.delete("client_user")
  url.searchParams.delete("client_route")

  if (clientRoute) {
    const targetUrl = new URL(clientRoute, window.location.origin)
    window.history.replaceState({}, document.title, `${targetUrl.pathname}${targetUrl.search}${targetUrl.hash}`)
    return
  }

  if (token || rawUser) {
    window.history.replaceState({}, document.title, `${url.pathname}${url.search}${url.hash}`)
  }
}

bootstrapClientAuth()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

const icons = {
  ArrowDown,
  ChatDotRound,
  CircleCheck,
  DataAnalysis,
  Document,
  List,
  Monitor,
  Phone,
  Reading,
  TrendCharts,
  Upload,
  UserFilled,
  Warning,
}

for (const [key, component] of Object.entries(icons)) {
  app.component(key, component)
}

app.mount("#app")
