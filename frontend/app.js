"use strict";

const API = "/api/tasks";
const state = { tasks: [], filter: "all", query: "", editingId: null };
const $ = (selector) => document.querySelector(selector);
const statusLabels = { todo: "To do", in_progress: "In progress", completed: "Completed" };

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.error?.message || body?.detail || "Something went wrong. Please try again.");
  }
  return body;
}

function localDateTimeValue(isoDate) {
  const date = new Date(isoDate);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function formatDate(isoDate) {
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric", month: "short", year: "numeric",
  }).format(new Date(isoDate));
}

function dueLabel(isoDate) {
  const due = new Date(isoDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dueDay = new Date(due);
  dueDay.setHours(0, 0, 0, 0);
  const days = Math.round((dueDay - today) / 86400000);
  const time = due.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (days < 0) return { label: "Overdue", sub: formatDate(isoDate), overdue: true };
  if (days === 0) return { label: "Due today", sub: time, overdue: false };
  if (days === 1) return { label: "Tomorrow", sub: time, overdue: false };
  return { label: formatDate(isoDate), sub: time, overdue: false };
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("visible"), 2600);
}

function updateStats() {
  const count = (status) => state.tasks.filter((task) => task.status === status).length;
  $("#stat-total").textContent = state.tasks.length;
  $("#stat-todo").textContent = count("todo");
  $("#stat-progress").textContent = count("in_progress");
  $("#stat-completed").textContent = count("completed");
}

function filteredTasks() {
  return state.tasks.filter((task) => {
    const statusMatch = state.filter === "all" || task.status === state.filter;
    const text = (task.title + " " + (task.description || "")).toLowerCase();
    return statusMatch && text.includes(state.query.toLowerCase());
  });
}

function makeNode(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderTasks() {
  updateStats();
  const tasks = filteredTasks();
  $("#task-count").textContent =
    "Showing " + tasks.length + " of " + state.tasks.length +
    " task" + (state.tasks.length === 1 ? "" : "s");

  const list = $("#task-list");
  list.replaceChildren();
  if (!tasks.length) {
    const empty = makeNode("div", "empty-state");
    empty.append(makeNode("div", "empty-icon", state.tasks.length ? "⌕" : "✦"));
    empty.append(makeNode("strong", "", state.tasks.length ? "No matching tasks" : "A clear space to get started."));
    empty.append(makeNode("p", "", state.tasks.length
      ? "Try changing your search or status filter."
      : "Add your first task and give your day some structure."));
    if (!state.tasks.length) {
      const button = makeNode("button", "primary-button", "＋ Create your first task");
      button.type = "button";
      button.dataset.action = "new";
      empty.append(button);
    }
    list.append(empty);
    return;
  }

  tasks.forEach((task) => {
    const due = dueLabel(task.due_at);
    const row = makeNode("article", "task-row");
    row.dataset.taskId = String(task.id);
    const main = makeNode("div", "task-main");
    main.append(makeNode("div", "task-title", task.title));
    main.append(makeNode("div", "task-description", task.description || "No description added"));
    const status = makeNode("span", "status-pill status-" + task.status, statusLabels[task.status]);
    const date = makeNode("div", "due-date" + (due.overdue ? " overdue" : ""), due.label);
    date.append(makeNode("small", "", due.sub));
    const actions = makeNode("div", "row-actions");
    const edit = makeNode("button", "row-action", "✎");
    edit.type = "button"; edit.dataset.action = "edit"; edit.title = "Edit"; edit.setAttribute("aria-label", "Edit " + task.title);
    const remove = makeNode("button", "row-action delete", "×");
    remove.type = "button"; remove.dataset.action = "delete"; remove.title = "Delete"; remove.setAttribute("aria-label", "Delete " + task.title);
    actions.append(edit, remove);
    row.append(main, status, date, actions);
    list.append(row);
  });
}

async function refreshTasks() {
  const list = $("#task-list");
  list.replaceChildren(makeNode("div", "loading-state", "Loading your tasks…"));
  try {
    state.tasks = await request(API);
    renderTasks();
  } catch (error) {
    const empty = makeNode("div", "empty-state");
    empty.append(makeNode("strong", "", "We couldn't load your tasks."));
    empty.append(makeNode("p", "", error.message));
    const retry = makeNode("button", "secondary-button", "Try again");
    retry.type = "button"; retry.dataset.action = "retry";
    empty.append(retry);
    list.replaceChildren(empty);
  }
}

function openModal(task = null) {
  state.editingId = task ? task.id : null;
  $("#task-form").reset();
  $("#title-error").textContent = "";
  $("#due-error").textContent = "";
  $("#form-feedback").textContent = "";
  $("#modal-title").textContent = task ? "Edit task" : "Create a task";
  $("#save-task-button").textContent = task ? "Save changes" : "Save task";
  if (task) {
    $("#task-title").value = task.title;
    $("#task-description").value = task.description || "";
    $("#task-due").value = localDateTimeValue(task.due_at);
    $("#task-status").value = task.status;
  } else {
    $("#task-due").value = localDateTimeValue(new Date(Date.now() + 86400000).toISOString());
    $("#task-status").value = "todo";
  }
  $("#task-modal").hidden = false;
  document.body.style.overflow = "hidden";
  $("#task-title").focus();
}

function closeModal() {
  $("#task-modal").hidden = true;
  document.body.style.overflow = "";
  state.editingId = null;
}

async function saveTask(event) {
  event.preventDefault();
  $("#title-error").textContent = "";
  $("#due-error").textContent = "";
  $("#form-feedback").textContent = "";
  const title = $("#task-title").value.trim();
  if (!title) {
    $("#title-error").textContent = "Please enter a task title.";
    $("#task-title").focus();
    return;
  }
  if (!$("#task-due").value) {
    $("#due-error").textContent = "Please choose a due date and time.";
    $("#task-due").focus();
    return;
  }

  const editing = state.editingId !== null;
  const id = state.editingId;
  const payload = {
    title,
    description: $("#task-description").value.trim() || null,
    status: $("#task-status").value,
    due_at: new Date($("#task-due").value).toISOString(),
  };
  const save = $("#save-task-button");
  save.disabled = true;
  save.textContent = "Saving…";
  try {
    if (editing) {
      await request(API + "/" + id, { method: "PATCH", body: JSON.stringify(payload) });
      toast("Task updated successfully.");
    } else {
      await request(API, { method: "POST", body: JSON.stringify(payload) });
      toast("Your new task has been added.");
    }
    closeModal();
    await refreshTasks();
  } catch (error) {
    $("#form-feedback").textContent = error.message;
  } finally {
    save.disabled = false;
    save.textContent = editing ? "Save changes" : "Save task";
  }
}

async function handleListAction(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  if (button.dataset.action === "new") return openModal();
  if (button.dataset.action === "retry") return refreshTasks();
  const row = button.closest("[data-task-id]");
  const task = state.tasks.find((item) => item.id === Number(row?.dataset.taskId));
  if (!task) return;
  if (button.dataset.action === "edit") return openModal(task);
  if (button.dataset.action === "delete") {
    if (!window.confirm("Delete “" + task.title + "”? This cannot be undone.")) return;
    try {
      await request(API + "/" + task.id, { method: "DELETE" });
      toast("Task deleted.");
      await refreshTasks();
    } catch (error) {
      toast(error.message);
    }
  }
}

function setActiveView(filter, clearSearch = false) {
  state.filter = filter;
  $("#status-filter").value = filter;
  if (clearSearch) {
    state.query = "";
    $("#task-search").value = "";
  }
  const navFilter = filter === "todo" ? "all" : filter;
  document.querySelectorAll("[data-nav-filter]").forEach((link) => {
    const active = link.dataset.navFilter === navFilter;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  const labels = { all: "My tasks", todo: "My tasks", in_progress: "In progress", completed: "Completed" };
  $("#current-view-label").textContent = labels[filter] || "My tasks";
  renderTasks();
}

function init() {
  $("#today-label").textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "short", day: "numeric", month: "short",
  }).format(new Date());
  $("#new-task-button").addEventListener("click", () => openModal());
  $("#close-modal-button").addEventListener("click", closeModal);
  $("#cancel-modal-button").addEventListener("click", closeModal);
  $("#task-modal").addEventListener("click", (event) => {
    if (event.target === $("#task-modal")) closeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("#task-modal").hidden) closeModal();
  });
  $("#task-form").addEventListener("submit", saveTask);
  $("#task-list").addEventListener("click", handleListAction);
  $("#task-search").addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    renderTasks();
  });
  $("#status-filter").addEventListener("change", (event) => setActiveView(event.target.value));
  document.querySelectorAll("[data-nav-filter]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      setActiveView(link.dataset.navFilter, link.dataset.navFilter === "all");
    });
  });

  const profileMenu = document.querySelector(".profile-menu");
  profileMenu.querySelectorAll("[data-menu-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      profileMenu.open = false;
      if (button.dataset.menuAction === "all") {
        setActiveView("all", true);
      } else if (button.dataset.menuAction === "refresh") {
        await refreshTasks();
        toast("Tasks refreshed.");
      }
    });
  });
  document.addEventListener("click", (event) => {
    if (!profileMenu.contains(event.target)) profileMenu.open = false;
  });

  refreshTasks();
}

init();
