import { createRouter, createWebHistory } from "vue-router";

import Login from "../pages/Login.vue";
import Entry from "../pages/Entry.vue";
import Quiz from "../pages/Quiz.vue";
import StudentHome from "../pages/StudentHome.vue";
import AdminUpload from "../pages/AdminUpload.vue";

const routes = [
  { path: "/", redirect: "/login" },
<<<<<<< HEAD
  { path: "/login", component: Login },
  { path: "/entry", component: Entry },
  { path: "/quiz", component: Quiz },
  { path: "/home", component: StudentHome },
  { path: "/admin/upload", component: AdminUpload },
=======

  { path: "/login", name: "login", component: Login, meta: { public: true } },
  { path: "/entry", name: "entry", component: Entry, meta: { public: true } },

  // 學生（可放行）
  { path: "/learn/:unit", name: "StudentLearning", component: () => import("../pages/StudentLearning.vue"), meta: { public: true } },
  { path: "/parsons/:videoId", name: "parsons", component: () => import("../pages/parsons.vue"), meta: { public: true } },
  { path: "/quiz", name: "quiz", component: Quiz, meta: { public: true } },
  { path: "/home", name: "home", component: StudentHome, meta: { public: true } },

  // 老師端（需登入）
  { path: "/admin/upload", name: "adminUpload", component: AdminUpload },
  { path: "/teacher/dashboard", name: "teacherDashboard", component: () => import("../pages/TeacherDashboard.vue") },
  { path: "/teacher/subtitle", name: "teacherSubtitle", component: () => import("../pages/TeacherSubtitles.vue") },

  // ✅ 新增：alias 路由（避免按字幕校正跑去 login）
  { path: "/subtitle-verify", name: "subtitleVerify", component: () => import("../pages/TeacherSubtitles.vue") },

  { path: "/teacher/agentlog", name: "teacherAgentLog", component: () => import("../pages/TeacherT5AgentLog.vue") },
  { path: "/teacher/videos", name: "teacherVideos", component: () => import("../pages/TeacherVideoManage.vue") },
  { path: "/teacher/parsons", name: "teacherParsons", component: () => import("../pages/TeacherParsonsManage.vue") },
  { path: "/teacher/students", name: "teacherStudents", component: () => import("../pages/TeacherStudentRecords.vue") },

  { path: "/student/learning", name: "studentLearning", component: () => import("../pages/StudentLearning.vue"), meta: { public: true } },
  { path: "/student/dashboard", name: "studentDashboard", component: () => import("../pages/StudentDashboard.vue"), meta: { public: true } },

>>>>>>> 816ab8e (0207 新增AdminUpload頁面內容)
  { path: "/:pathMatch(.*)*", redirect: "/login" },
  { path: "/learn/:unit", name: "StudentLearning", component: () => import("../pages/StudentLearning.vue") },
];

export const router = createRouter({
  history: createWebHistory(),
  routes
});
<<<<<<< HEAD
=======

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("token");

  // Parsons 練習頁一律放行
  if (to.path.startsWith("/parsons")) return next();
  if (to.meta?.public) return next();
  if (token) return next();

  return next("/login");
});

export default router;
export { router };
>>>>>>> 816ab8e (0207 新增AdminUpload頁面內容)
