import { createRouter, createWebHistory } from "vue-router";

import Login from "../pages/Login.vue";
import Entry from "../pages/Entry.vue";
import Quiz from "../pages/Quiz.vue";
import StudentHome from "../pages/StudentHome.vue";
import AdminUpload from "../pages/AdminUpload.vue";

const routes = [
  { path: "/", redirect: "/login" },
  { path: "/login", component: Login },
  { path: "/entry", component: Entry },
  { path: "/quiz", component: Quiz },
  { path: "/home", component: StudentHome },
//   { path: "/admin/upload", component: () => import("../pages/AdminUpload.vue") }
  { path: "/admin/upload", component: () => import("../pages/AdminUpload.vue") },
  { path: "/admin/upload", component: AdminUpload }
];


export const router = createRouter({
  history: createWebHistory(),
  routes
});
