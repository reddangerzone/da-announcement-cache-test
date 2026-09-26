const endpoint = "/.netlify/functions/admin-data";
let password = "";
let data = { war_label: "negotiating", notes: "", events: [] };

const $ = selector => document.querySelector(selector);

async function request(action, payload = {}) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, password, ...payload })
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}

function utcValue(value) {
  return value ? `${value}:00Z` : null;
}

function localInputValue(value) {
  return value ? value.replace(/Z$/, "").slice(0, 16) : "";
}

function populate() {
  $(`input[name="war-label"][value="${data.war_label}"]`).checked = true;
  $("#notes").value = data.notes || "";
  const rows = $("#event-rows");
  rows.replaceChildren();
  if (!data.events.length) {
    const row = rows.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 3;
    cell.textContent = "No faction events have been entered.";
    return;
  }
  data.events.forEach((event, index) => {
    const row = rows.insertRow();
    row.insertCell().textContent = event.title;
    row.insertCell().textContent = event.starts_at.replace("T", " ").replace("Z", " TCT");
    const actions = row.insertCell();
    actions.className = "table-actions";
    const edit = document.createElement("button");
    edit.type = "button"; edit.textContent = "Edit";
    edit.addEventListener("click", () => editEvent(index));
    const remove = document.createElement("button");
    remove.type = "button"; remove.textContent = "Delete"; remove.className = "secondary";
    remove.addEventListener("click", () => deleteEvent(index));
    actions.append(edit, remove);
  });
}

async function save(message = "Saved") {
  const state = $("#save-state");
  state.textContent = "Saving…";
  try {
    const result = await request("write", { data });
    data = result.data;
    populate();
    state.textContent = message;
  } catch (error) {
    state.textContent = error.message;
  }
}

function resetEventForm() {
  $("#event-form").reset();
  $("#event-index").value = "";
  $("#event-form-title").textContent = "Add an event";
  $("#cancel-edit").hidden = true;
}

function editEvent(index) {
  const event = data.events[index];
  $("#event-index").value = index;
  $("#event-title").value = event.title;
  $("#event-start").value = localInputValue(event.starts_at);
  $("#event-end").value = localInputValue(event.ends_at);
  $("#event-description").value = event.description || "";
  $("#event-form-title").textContent = "Edit event";
  $("#cancel-edit").hidden = false;
  $("#event-form").scrollIntoView({ behavior: "smooth" });
}

async function deleteEvent(index) {
  if (!confirm(`Delete “${data.events[index].title}”?`)) return;
  data.events.splice(index, 1);
  await save("Event deleted");
}

$("#login-form").addEventListener("submit", async event => {
  event.preventDefault();
  password = $("#password").value;
  try {
    const result = await request("read");
    data = result.data;
    populate();
    $("#login-panel").hidden = true;
    $("#controls").hidden = false;
  } catch (error) {
    alert(error.message);
  }
});

$("#save-controls").addEventListener("click", async () => {
  data.war_label = $('input[name="war-label"]:checked').value;
  data.notes = $("#notes").value.trim();
  await save("Controls saved");
});

$("#event-form").addEventListener("submit", async event => {
  event.preventDefault();
  const record = {
    title: $("#event-title").value.trim(),
    starts_at: utcValue($("#event-start").value),
    ends_at: utcValue($("#event-end").value),
    description: $("#event-description").value.trim()
  };
  const index = $("#event-index").value;
  if (index === "") data.events.push(record); else data.events[Number(index)] = record;
  data.events.sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  resetEventForm();
  await save("Event saved");
});

$("#cancel-edit").addEventListener("click", resetEventForm);
