<template>
  <div class="voice-agent-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Voice Agent</h1>
        <p class="page-subtitle">AI-powered phone agent that handles calls, books appointments, and captures leads.</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary btn-sm" @click="startWebCall" :disabled="webCallLoading">
          {{ webCallLoading ? 'Connecting...' : 'Test Call' }}
        </button>
      </div>
    </div>
    <div class="stats-grid" style="margin-bottom: 24px">
      <div class="stat-card">
        <div class="stat-label">Total Calls</div>
        <div class="stat-value">{{ stats.total_calls || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Completed</div>
        <div class="stat-value text-success">{{ stats.completed_calls || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Missed</div>
        <div class="stat-value" :class="(stats.missed_calls || 0) > 0 ? 'text-warning' : ''">{{ stats.missed_calls || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Duration</div>
        <div class="stat-value">{{ formatDuration(stats.avg_duration || 0) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Appointments Booked</div>
        <div class="stat-value text-success">{{ stats.appointments_booked || 0 }}</div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tab-bar">
      <button v-for="tab in tabs" :key="tab.id" class="tab-btn" :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">
        {{ tab.label }}
        <span v-if="tab.badge" class="tab-badge">{{ tab.badge }}</span>
      </button>
    </div>

    <!-- Tab: Get Started (onboarding) -->
    <div v-if="activeTab === 'getStarted'" class="tab-content">
      <div class="getstarted-intro">
        <h2>Welcome to your AI Voice Agent</h2>
        <p>
          Two ways to use it. Pick the one you want to set up first — you can do both later.
        </p>
        <ul class="getstarted-bullets">
          <li><strong>AI Receptionist (Inbound):</strong> when someone calls your business, the AI answers, helps the caller, and books appointments or creates a todo for you.</li>
          <li><strong>AI Sales Caller (Outbound):</strong> upload a list of leads and the AI calls them, plays a welcome message, and pitches your product using a script you write in a markdown file.</li>
        </ul>
        <p class="getstarted-hint">
          Need a starting point? Click <strong>Apply</strong> on a template below — we'll fill in your knowledge base for you. You can edit the markdown after.
        </p>
      </div>
      <!-- Recent Calls preview -->
      <div class="card" style="margin: 20px 0">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px">
          <h3 class="card-title" style="margin:0">Recent Calls</h3>
          <button class="btn btn-secondary btn-xs" @click="activeTab = 'calls'">View all</button>
        </div>
        <p class="text-sm text-muted" style="margin-bottom:12px">
          Latest inbound and outbound calls handled by your AI agent. If a caller looks like a possible lead, we capture their details here automatically. They are not pushed to your Leads table yet — review them first and promote the ones you want.
        </p>
        <div v-if="loading.calls" class="loading-state">Loading calls...</div>
        <div v-else-if="!calls.length" class="empty-state" style="padding:16px">
          <p>No calls yet. Once you add a forwarded phone number, calls will appear here.</p>
        </div>
        <div v-else class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Caller</th>
                <th>Phone</th>
                <th>Duration</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="call in calls.slice(0, 5)" :key="call.id" class="clickable-row" @click="selectedCall = call">
                <td class="font-medium">{{ call.caller_name || 'Unknown' }}</td>
                <td>{{ call.caller_phone }}</td>
                <td>{{ call.duration_display }}</td>
                <td><span class="status-pill" :class="'status-' + call.status">{{ call.status }}</span></td>
                <td class="text-muted">{{ formatDate(call.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <VoiceOnboarding
        :website-id="wid"
        @navigate="handleOnboardingNavigate"
        @applied="handleTemplateApplied"
      />
    </div>

    <!-- Tab: Phone Numbers -->
    <div v-if="activeTab === 'phones'" class="tab-content">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
        <p class="text-sm text-muted">Add your work phone numbers. Enable forwarding to route calls to the AI agent.</p>
        <button class="btn btn-primary btn-sm" @click="showPhoneModal = true">+ Add Number</button>
      </div>

      <div v-if="loading.phones" class="loading-state">Loading phone numbers...</div>
      <div v-else-if="!phoneNumbers.length" class="empty-state">
        <p>No phone numbers added yet. Add your work number and enable forwarding to start receiving AI-handled calls.</p>
      </div>
      <div v-else class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Number</th>
              <th>Label</th>
              <th>Provider</th>
              <th>Forward to Agent</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="num in phoneNumbers" :key="num.id">
              <td class="font-medium">{{ num.number }}</td>
              <td>{{ num.label || '-' }}</td>
              <td><span class="provider-badge">{{ num.provider }}</span></td>
              <td>
                <span v-if="num.forwarded_to_agent" class="status-pill status-completed">Yes</span>
                <span v-else class="status-pill status-dismissed">No</span>
              </td>
              <td>
                <span v-if="num.is_active" class="status-pill status-confirmed">Active</span>
                <span v-else class="status-pill status-cancelled">Inactive</span>
              </td>
              <td style="display: flex; gap: 6px">
                <button class="btn btn-secondary btn-xs" @click="editPhone(num)">Edit</button>
                <button class="btn btn-danger btn-xs" @click="deletePhone(num.id)">Remove</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card" style="margin-top: 24px; max-width: 680px">
        <h3 class="card-title" style="margin-bottom: 8px">How Call Forwarding Works</h3>
        <p class="text-sm text-muted" style="margin-bottom: 12px">To route calls from your business number to the AI agent:</p>
        <ol class="text-sm" style="padding-left: 20px; display: flex; flex-direction: column; gap: 6px; color: var(--text-secondary)">
          <li>Add your work phone number above with <strong>Forward to Agent</strong> enabled.</li>
          <li>Log in to your phone carrier portal (Telnyx, Twilio, or your mobile provider).</li>
          <li>Set up call forwarding to the SIP endpoint shown in <strong>Settings</strong> (the Forwarding Number field).</li>
          <li>Callers will be answered by the AI immediately — 24/7.</li>
        </ol>
      </div>
    </div>

    <!-- Tab: Lead Detection -->
    <div v-if="activeTab === 'leadDetection'" class="tab-content">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px">
        <p class="text-sm text-muted" style="max-width: 640px">
          We score every completed call from its transcript — intent, sentiment, contact info shared, appointment talk, and buying-signal keywords. High-scoring callers show up here for you to review. Promoting one creates a real Lead in your CRM. Nothing is auto-pushed.
        </p>
        <button class="btn btn-secondary btn-sm" @click="loadPossibleLeads">Refresh</button>
      </div>

      <div v-if="loading.leads" class="loading-state">Loading possible leads...</div>
      <div v-else-if="!possibleLeads.length" class="empty-state">
        <p>No flagged callers right now. As completed calls are scored, possible leads will appear here.</p>
      </div>
      <div v-else class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Caller</th>
              <th>Phone</th>
              <th>Intent</th>
              <th>Score</th>
              <th>Signals</th>
              <th>Date</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="call in possibleLeads" :key="call.id">
              <td class="font-medium">{{ call.caller_name || 'Unknown' }}</td>
              <td>{{ call.caller_phone }}</td>
              <td>{{ call.call_intent || '-' }}</td>
              <td>
                <span class="status-pill" :class="call.lead_score >= 70 ? 'status-confirmed' : 'status-completed'">
                  {{ call.lead_score }}
                </span>
              </td>
              <td>
                <span v-for="(pts, label) in call.lead_signals" :key="label" class="provider-badge" style="margin-right:4px" :title="`+${pts}`">
                  {{ label }}
                </span>
              </td>
              <td class="text-muted">{{ formatDate(call.created_at) }}</td>
              <td style="display:flex; gap:6px">
                <button class="btn btn-secondary btn-xs" @click="selectedCall = call">View</button>
                <button class="btn btn-primary btn-xs" @click="promoteLead(call)" :disabled="leadActionId === call.id">
                  {{ leadActionId === call.id ? '...' : 'Promote' }}
                </button>
                <button class="btn btn-danger btn-xs" @click="dismissLead(call)" :disabled="leadActionId === call.id">
                  Dismiss
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab: Calls -->
    <div v-if="activeTab === 'calls'" class="tab-content">
      <div class="filter-row" style="margin-bottom: 16px">
        <select v-model="callFilter.status" class="form-input form-input-sm" style="width:140px" @change="loadCalls">
          <option value="">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="missed">Missed</option>
          <option value="in_progress">In Progress</option>
          <option value="failed">Failed</option>
        </select>
        <select v-model="callFilter.direction" class="form-input form-input-sm" style="width:140px" @change="loadCalls">
          <option value="">All Directions</option>
          <option value="inbound">Inbound</option>
          <option value="outbound">Outbound</option>
        </select>
      </div>

      <div v-if="loading.calls" class="loading-state">Loading calls...</div>
      <div v-else-if="!calls.length" class="empty-state">
        <p>No calls recorded yet. Activate the agent and share the phone number to start receiving calls.</p>
      </div>
      <div v-else class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Caller</th>
              <th>Phone</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Intent</th>
              <th>Sentiment</th>
              <th>Date</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="call in calls" :key="call.id" class="clickable-row" @click="selectedCall = call">
              <td class="font-medium">{{ call.caller_name || 'Unknown' }}</td>
              <td>{{ call.caller_phone }}</td>
              <td><span class="status-pill" :class="'status-' + call.status">{{ call.status }}</span></td>
              <td>{{ call.duration_display }}</td>
              <td>{{ call.call_intent || '-' }}</td>
              <td>
                <span v-if="call.sentiment" class="sentiment-badge" :class="'sentiment-' + call.sentiment">{{ call.sentiment }}</span>
                <span v-else>-</span>
              </td>
              <td class="text-muted">{{ formatDate(call.created_at) }}</td>
              <td><button class="btn-ghost btn-icon btn-xs">View</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab: Calendar -->
    <div v-if="activeTab === 'calendar'" class="tab-content">
      <div class="calendar-header" style="margin-bottom: 16px; display: flex; gap: 12px; align-items: center">
        <button class="btn btn-primary btn-sm" @click="showBookModal = true">+ Book Appointment</button>
        <input type="date" v-model="availabilityDate" class="form-input form-input-sm" style="width:180px" @change="checkAvailability" />
      </div>

      <!-- Available Slots -->
      <div v-if="availableSlots.length" class="slots-grid" style="margin-bottom: 24px">
        <div class="section-title" style="margin-bottom: 8px">Available Slots for {{ availabilityDate }}</div>
        <div class="slots-row">
          <span v-for="slot in availableSlots" :key="slot.start" class="slot-chip" @click="prefillSlot(slot)">
            {{ slot.start }} - {{ slot.end }}
          </span>
        </div>
      </div>

      <div v-if="loading.events" class="loading-state">Loading appointments...</div>
      <div v-else-if="!events.length" class="empty-state">
        <p>No upcoming appointments. The voice agent will book them automatically during calls.</p>
      </div>
      <div v-else class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Attendee</th>
              <th>Phone</th>
              <th>Date & Time</th>
              <th>Status</th>
              <th>Assigned To</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ev in events" :key="ev.id">
              <td class="font-medium">{{ ev.title }}</td>
              <td>{{ ev.attendee_name }}</td>
              <td>{{ ev.attendee_phone }}</td>
              <td>{{ formatDateTime(ev.start_time) }} - {{ formatTime(ev.end_time) }}</td>
              <td><span class="status-pill" :class="'status-' + ev.status">{{ ev.status }}</span></td>
              <td>{{ ev.assigned_to_name || '-' }}</td>
              <td>
                <button v-if="ev.status === 'scheduled' || ev.status === 'confirmed'" class="btn btn-danger btn-xs" @click="cancelEvent(ev.id)">Cancel</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab: Reminders -->
    <div v-if="activeTab === 'reminders'" class="tab-content">
      <button class="btn btn-primary btn-sm" style="margin-bottom: 16px" @click="showReminderModal = true">+ Add Reminder</button>

      <div v-if="loading.reminders" class="loading-state">Loading reminders...</div>
      <div v-else-if="!reminders.length" class="empty-state">
        <p>No pending callback reminders. The voice agent creates these automatically when callers request a callback.</p>
      </div>
      <div v-else class="reminder-cards">
        <div v-for="rem in reminders" :key="rem.id" class="reminder-card">
          <div class="reminder-header">
            <div>
              <div class="font-semibold">{{ rem.contact_name }}</div>
              <div class="text-sm text-muted">{{ rem.contact_phone }}</div>
            </div>
            <span class="status-pill" :class="'status-' + rem.status">{{ rem.status }}</span>
          </div>
          <p v-if="rem.reason" class="text-sm" style="margin: 8px 0">{{ rem.reason }}</p>
          <div class="text-xs text-muted">Remind at: {{ formatDateTime(rem.remind_at) }}</div>
          <div v-if="rem.call_summary" class="text-xs text-muted" style="margin-top: 4px">Call summary: {{ rem.call_summary }}</div>
          <div class="reminder-actions" style="margin-top: 12px; display: flex; gap: 8px">
            <button class="btn btn-primary btn-xs" @click="completeReminder(rem.id)">Mark Complete</button>
            <button class="btn btn-secondary btn-xs" @click="dismissReminder(rem.id)">Dismiss</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab: Todos -->
    <div v-if="activeTab === 'todos'" class="tab-content">
      <div class="todo-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
        <div class="todo-stats-row" style="display: flex; gap: 16px">
          <span class="todo-stat"><strong>{{ todoStats.open || 0 }}</strong> open</span>
          <span class="todo-stat"><strong>{{ todoStats.in_progress || 0 }}</strong> in progress</span>
          <span class="todo-stat"><strong>{{ todoStats.done || 0 }}</strong> done</span>
          <span v-if="todoStats.high_priority" class="todo-stat todo-stat-urgent"><strong>{{ todoStats.high_priority }}</strong> urgent</span>
        </div>
        <div class="filter-row">
          <select v-model="todoFilter.status" class="form-input form-input-sm" style="width: 130px" @change="loadTodos">
            <option value="">All Status</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
          <select v-model="todoFilter.priority" class="form-input form-input-sm" style="width: 130px" @change="loadTodos">
            <option value="">All Priority</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <div v-if="loading.todos" class="loading-state">Loading todos...</div>
      <div v-else-if="!todos.length" class="empty-state">
        <p>No action items yet. Todos are automatically extracted from call transcripts by the AI.</p>
      </div>
      <div v-else class="todo-list">
        <div v-for="todo in todos" :key="todo.id" class="todo-card" :class="'todo-priority-' + todo.priority">
          <div class="todo-main">
            <button class="todo-check" :class="{ 'todo-checked': todo.status === 'done' }" @click="toggleTodo(todo)">
              <svg v-if="todo.status === 'done'" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="2,7 5.5,10.5 12,3.5"/></svg>
            </button>
            <div class="todo-content" :class="{ 'todo-done': todo.status === 'done' }">
              <div class="todo-description">{{ todo.description }}</div>
              <div class="todo-meta">
                <span class="priority-badge" :class="'priority-' + todo.priority">{{ todo.priority }}</span>
                <span v-if="todo.call_caller_name" class="text-xs text-muted">From: {{ todo.call_caller_name }} ({{ todo.call_caller_phone }})</span>
                <span v-if="todo.due_date" class="text-xs text-muted">Due: {{ todo.due_date }}</span>
                <span class="text-xs text-muted">{{ formatDate(todo.created_at) }}</span>
              </div>
            </div>
          </div>
          <div class="todo-actions">
            <select :value="todo.status" @change="updateTodoStatus(todo.id, $event.target.value)" class="form-input form-input-sm" style="width: 110px; font-size: 12px">
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="done">Done</option>
              <option value="dismissed">Dismiss</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab: Settings -->
    <div v-if="activeTab === 'settings'" class="tab-content">
      <div class="settings-card card" style="max-width: 700px">
        <h3 class="card-title" style="margin-bottom: 16px">Agent Configuration</h3>

        <div class="form-group">
          <label class="form-label">Business Name</label>
          <input v-model="config.business_name" class="form-input" placeholder="Your Business Name" />
        </div>

        <div class="form-group">
          <label class="form-label">Phone Number</label>
          <input v-model="config.phone_number" class="form-input" placeholder="Assigned by Retell AI" disabled />
          <p class="form-hint">Phone number is assigned when you activate the agent via Retell AI dashboard.</p>
        </div>

        <div class="form-group">
          <label class="form-label">Greeting Message</label>
          <textarea v-model="config.greeting_message" class="form-input" rows="2" placeholder="Hello! Thank you for calling..."></textarea>
        </div>

        <div class="form-group">
          <label class="form-label">AI System Prompt</label>
          <textarea v-model="config.system_prompt" class="form-input" rows="4" placeholder="Instructions for the AI agent..."></textarea>
        </div>

        <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px">
          <div class="form-group">
            <label class="form-label">Appointment Duration (minutes)</label>
            <input v-model.number="config.appointment_duration_minutes" class="form-input" type="number" min="15" max="120" step="15" />
          </div>
          <div class="form-group">
            <label class="form-label">Timezone</label>
            <select v-model="config.timezone" class="form-input">
              <option value="UTC">UTC</option>
              <option value="America/New_York">Eastern (ET)</option>
              <option value="America/Chicago">Central (CT)</option>
              <option value="America/Denver">Mountain (MT)</option>
              <option value="America/Los_Angeles">Pacific (PT)</option>
              <option value="Europe/London">London (GMT)</option>
              <option value="Europe/Berlin">Berlin (CET)</option>
              <option value="Asia/Tokyo">Tokyo (JST)</option>
              <option value="Asia/Kolkata">India (IST)</option>
              <option value="Australia/Sydney">Sydney (AEST)</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Business Hours</label>
          <div class="hours-grid">
            <div v-for="day in weekdays" :key="day" class="hours-row">
              <label class="hours-day">
                <input type="checkbox" :checked="config.business_hours[day]" @change="toggleDay(day, $event.target.checked)" />
                {{ day.charAt(0).toUpperCase() + day.slice(1) }}
              </label>
              <template v-if="config.business_hours[day]">
                <input type="time" :value="config.business_hours[day]?.start" @input="config.business_hours[day].start = $event.target.value" class="form-input form-input-sm" style="width:120px" />
                <span class="text-muted">to</span>
                <input type="time" :value="config.business_hours[day]?.end" @input="config.business_hours[day].end = $event.target.value" class="form-input form-input-sm" style="width:120px" />
              </template>
              <span v-else class="text-muted text-sm">Closed</span>
            </div>
          </div>
        </div>

        <div style="margin-top: 20px; display: flex; gap: 8px; justify-content: flex-end">
          <button class="btn btn-primary" @click="saveConfig" :disabled="saving">{{ saving ? 'Saving...' : 'Save Configuration' }}</button>
        </div>
      </div>

      <!-- Knowledge Base / Context Documents -->
      <div class="card" style="max-width: 700px; margin-top: 24px">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
          <div>
            <h3 class="card-title">Knowledge Base</h3>
            <p class="text-sm text-muted" style="margin-top: 4px">Markdown documents injected into the agent prompt. The AI reads these to answer caller questions.</p>
          </div>
          <div style="display: flex; gap: 8px">
            <input
              ref="docFileInput"
              type="file"
              accept=".md,.markdown,.txt"
              style="display: none"
              @change="onDocFileSelected"
            />
            <button class="btn btn-secondary btn-sm" @click="$refs.docFileInput.click()" :disabled="uploadingDoc">
              {{ uploadingDoc ? 'Uploading...' : 'Upload .md' }}
            </button>
            <button class="btn btn-primary btn-sm" @click="showDocModal = true">+ Add Document</button>
          </div>
        </div>

        <div v-if="loading.docs" class="loading-state" style="padding: 20px 0">Loading...</div>
        <div v-else-if="!contextDocs.length" class="empty-state" style="padding: 20px 0">
          <p>No documents yet. Add your Services & Pricing, FAQs, or Policies to help the agent answer questions accurately.</p>
        </div>
        <div v-else class="docs-list">
          <div v-for="doc in contextDocs" :key="doc.id" class="doc-card">
            <div class="doc-header">
              <div>
                <div class="font-semibold">{{ doc.title }}</div>
                <div class="text-xs text-muted">{{ doc.content.length }} characters</div>
              </div>
              <div style="display: flex; align-items: center; gap: 8px">
                <span class="status-pill" :class="doc.is_active ? 'status-confirmed' : 'status-dismissed'">
                  {{ doc.is_active ? 'Active' : 'Inactive' }}
                </span>
                <button class="btn btn-secondary btn-xs" @click="editDoc(doc)">Edit</button>
                <button class="btn btn-danger btn-xs" @click="deleteDoc(doc.id)">Delete</button>
              </div>
            </div>
            <pre class="doc-preview">{{ doc.content.slice(0, 200) }}{{ doc.content.length > 200 ? '...' : '' }}</pre>
          </div>
        </div>
      </div>

    </div>

    <!-- Call Detail Modal -->
    <div v-if="selectedCall" class="modal-overlay" @click.self="selectedCall = null">
      <div class="modal-card" style="max-width: 650px">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
          <h3 class="card-title">Call Details</h3>
          <button class="btn-ghost btn-icon" @click="selectedCall = null">X</button>
        </div>

        <div class="detail-grid">
          <div class="detail-item"><span class="detail-label">Caller</span><span>{{ selectedCall.caller_name || 'Unknown' }}</span></div>
          <div class="detail-item"><span class="detail-label">Phone</span><span>{{ selectedCall.caller_phone }}</span></div>
          <div class="detail-item"><span class="detail-label">Email</span><span>{{ selectedCall.caller_email || '-' }}</span></div>
          <div class="detail-item"><span class="detail-label">Company</span><span>{{ selectedCall.caller_company || '-' }}</span></div>
          <div class="detail-item"><span class="detail-label">Direction</span><span>{{ selectedCall.direction }}</span></div>
          <div class="detail-item"><span class="detail-label">Status</span><span class="status-pill" :class="'status-' + selectedCall.status">{{ selectedCall.status }}</span></div>
          <div class="detail-item"><span class="detail-label">Duration</span><span>{{ selectedCall.duration_display }}</span></div>
          <div class="detail-item"><span class="detail-label">Intent</span><span>{{ selectedCall.call_intent || '-' }}</span></div>
          <div class="detail-item"><span class="detail-label">Sentiment</span><span :class="selectedCall.sentiment ? 'sentiment-badge sentiment-' + selectedCall.sentiment : ''">{{ selectedCall.sentiment || '-' }}</span></div>
        </div>

        <div v-if="selectedCall.summary" style="margin-top: 16px">
          <div class="detail-label">Summary</div>
          <p class="text-sm" style="margin-top: 4px">{{ selectedCall.summary }}</p>
        </div>

        <div v-if="selectedCall.transcript" style="margin-top: 16px">
          <div class="detail-label">Transcript</div>
          <pre class="transcript-box">{{ selectedCall.transcript }}</pre>
        </div>

        <div v-if="Object.keys(selectedCall.extracted_data || {}).length" style="margin-top: 16px">
          <div class="detail-label">Extracted Data</div>
          <div class="extracted-data">
            <div v-for="(val, key) in selectedCall.extracted_data" :key="key" class="extracted-row">
              <span class="text-muted">{{ key }}:</span> <span>{{ val }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Book Appointment Modal -->
    <div v-if="showBookModal" class="modal-overlay" @click.self="showBookModal = false">
      <div class="modal-card" style="max-width: 500px">
        <h3 class="card-title" style="margin-bottom: 6px">Book Appointment</h3>
        <p class="text-sm text-muted" style="margin-bottom:14px">
          Appointments are created on your connected <strong>Google Calendar</strong>. The attendee receives a Google Calendar invite with a Meet link.
        </p>
        <div class="form-group">
          <label class="form-label">Attendee Name</label>
          <input v-model="newEvent.attendee_name" class="form-input" placeholder="John Doe" />
        </div>
        <div class="form-group">
          <label class="form-label">Phone</label>
          <input v-model="newEvent.attendee_phone" class="form-input" placeholder="+1234567890" />
        </div>
        <div class="form-group">
          <label class="form-label">Email (optional)</label>
          <input v-model="newEvent.attendee_email" class="form-input" placeholder="john@example.com" />
        </div>
        <div class="form-group">
          <label class="form-label">Title</label>
          <input v-model="newEvent.title" class="form-input" placeholder="Consultation call" />
        </div>
        <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px">
          <div class="form-group">
            <label class="form-label">Start Time</label>
            <input v-model="newEvent.start_time" type="datetime-local" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">End Time (optional)</label>
            <input v-model="newEvent.end_time" type="datetime-local" class="form-input" />
          </div>
        </div>
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px">
          <button class="btn btn-secondary" @click="showBookModal = false">Cancel</button>
          <button class="btn btn-primary" @click="bookAppointment" :disabled="bookingEvent">{{ bookingEvent ? 'Booking...' : 'Book' }}</button>
        </div>
        <p v-if="bookError" class="text-sm" style="color:var(--color-danger);margin-top:8px">{{ bookError }}</p>
      </div>
    </div>

    <!-- Add / Edit Phone Number Modal -->
    <div v-if="showPhoneModal" class="modal-overlay" @click.self="closePhoneModal">
      <div class="modal-card" style="max-width: 480px">
        <h3 class="card-title" style="margin-bottom: 8px">{{ editingPhone ? 'Edit Phone Number' : 'Add Phone Number' }}</h3>
        <div class="info-banner" style="background: var(--bg-surface); border-radius:6px; padding:10px 12px; margin-bottom:14px; font-size:13px; color: var(--text-secondary)">
          <strong>What happens next?</strong> We provision this number through our telephony vendor (Telnyx by default, Twilio supported). The vendor terminates the SIP/PSTN call and bridges it to our LiveKit-based AI agent. You keep your existing carrier — just point call forwarding at the SIP endpoint shown in Settings, and the vendor handles the rest.
        </div>
        <div class="form-group">
          <label class="form-label">Number (E.164 format)</label>
          <input
            v-model="phoneForm.number"
            class="form-input"
            placeholder="+12025551234"
            :disabled="!!editingPhone || mfa.verified"
          />
        </div>

        <!-- MFA: Step 1 — choose channel & send code -->
        <div v-if="!editingPhone && !mfa.sent && !mfa.verified" class="form-group" style="background: var(--bg-surface); padding:12px; border-radius:6px">
          <p class="text-sm" style="margin:0 0 8px"><strong>Verify ownership.</strong> We need to confirm you control this number before we attach it. Choose how you want to receive a 6-digit code:</p>
          <div style="display:flex; gap:8px">
            <button type="button" class="btn btn-secondary btn-sm" @click="sendMfaCode('sms')" :disabled="mfa.sending">{{ mfa.sending && mfa.channel === 'sms' ? 'Sending...' : 'Text me a code' }}</button>
            <button type="button" class="btn btn-secondary btn-sm" @click="sendMfaCode('call')" :disabled="mfa.sending">{{ mfa.sending && mfa.channel === 'call' ? 'Calling...' : 'Call me with the code' }}</button>
          </div>
          <p v-if="mfa.error" class="text-sm" style="color:var(--color-danger);margin-top:8px">{{ mfa.error }}</p>
        </div>

        <!-- MFA: Step 2 — enter the code -->
        <div v-if="!editingPhone && mfa.sent && !mfa.verified" class="form-group" style="background: var(--bg-surface); padding:12px; border-radius:6px">
          <label class="form-label">Verification code</label>
          <p class="text-sm text-muted" style="margin:0 0 6px">
            We {{ mfa.channel === 'sms' ? 'texted' : 'called' }} {{ phoneForm.number }} with a 6-digit code. Enter it below.
          </p>
          <input v-model="mfa.code" class="form-input" placeholder="123456" maxlength="6" inputmode="numeric" />
          <div style="display:flex; gap:8px; margin-top:8px">
            <button type="button" class="btn btn-secondary btn-sm" @click="mfaBack">← Back</button>
            <button type="button" class="btn btn-primary btn-sm" @click="confirmMfaCode" :disabled="mfa.confirming || !mfa.code">{{ mfa.confirming ? 'Verifying...' : 'Verify' }}</button>
            <button type="button" class="btn btn-ghost btn-sm" @click="sendMfaCode(mfa.channel)" :disabled="mfa.sending">{{ mfa.sending ? 'Resending...' : 'Resend' }}</button>
          </div>
          <p v-if="mfa.error" class="text-sm" style="color:var(--color-danger);margin-top:8px">{{ mfa.error }}</p>
        </div>

        <div v-if="mfa.verified" class="form-group" style="background: var(--bg-surface); padding:10px 12px; border-radius:6px; display:flex; justify-content:space-between; align-items:center; gap:8px">
          <p class="text-sm" style="margin:0; color: var(--color-success)"><strong>Verified.</strong> Fill in the details below and save.</p>
          <button type="button" class="btn btn-ghost btn-xs" @click="resetMfa">← Change number</button>
        </div>

        <div class="form-group">
          <label class="form-label">Label</label>
          <input v-model="phoneForm.label" class="form-input" placeholder="Main Line, Sales, Support..." />
        </div>
        <div class="form-group">
          <label class="form-label">Provider</label>
          <select v-model="phoneForm.provider" class="form-input">
            <option value="telnyx">Telnyx</option>
            <option value="twilio">Twilio</option>
            <option value="retell">Retell AI</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="form-group">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px">
            <input type="checkbox" v-model="phoneForm.forwarded_to_agent" />
            Forward inbound calls to AI agent
          </label>
        </div>
        <div class="form-group">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px">
            <input type="checkbox" v-model="phoneForm.is_active" />
            Active
          </label>
        </div>
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px">
          <button class="btn btn-secondary" @click="closePhoneModal">Cancel</button>
          <button class="btn btn-primary" @click="savePhone" :disabled="savingPhone || (!editingPhone && !mfa.verified)">{{ savingPhone ? 'Saving...' : 'Save' }}</button>
        </div>
      </div>
    </div>

    <!-- Add / Edit Context Document Modal -->
    <div v-if="showDocModal" class="modal-overlay" @click.self="closeDocModal">
      <div class="modal-card" style="max-width: 640px">
        <h3 class="card-title" style="margin-bottom: 16px">{{ editingDoc ? 'Edit Document' : 'Add Knowledge Document' }}</h3>
        <div class="form-group">
          <label class="form-label">Title</label>
          <input v-model="docForm.title" class="form-input" placeholder="Services & Pricing, FAQs, Policies..." />
        </div>
        <div class="form-group">
          <label class="form-label">Content (Markdown)</label>
          <textarea v-model="docForm.content" class="form-input" rows="12" placeholder="# Services&#10;&#10;## Web Development&#10;- Custom websites: $3,000 - $15,000&#10;..."></textarea>
          <p class="form-hint">{{ docForm.content.length }} / 10,000 characters</p>
        </div>
        <div class="form-group">
          <label class="form-label">Sort Order</label>
          <input v-model.number="docForm.sort_order" class="form-input" type="number" min="0" style="width: 100px" />
          <p class="form-hint">Lower numbers appear first in the agent prompt.</p>
        </div>
        <div class="form-group">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px">
            <input type="checkbox" v-model="docForm.is_active" />
            Active (include in agent prompt)
          </label>
        </div>
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px">
          <button class="btn btn-secondary" @click="closeDocModal">Cancel</button>
          <button class="btn btn-primary" @click="saveDoc" :disabled="savingDoc">{{ savingDoc ? 'Saving...' : 'Save' }}</button>
        </div>
      </div>
    </div>

    <!-- Add Reminder Modal -->
    <div v-if="showReminderModal" class="modal-overlay" @click.self="showReminderModal = false">
      <div class="modal-card" style="max-width: 500px">
        <h3 class="card-title" style="margin-bottom: 16px">Add Callback Reminder</h3>
        <div class="form-group">
          <label class="form-label">Contact Name</label>
          <input v-model="newReminder.contact_name" class="form-input" placeholder="John Doe" />
        </div>
        <div class="form-group">
          <label class="form-label">Phone</label>
          <input v-model="newReminder.contact_phone" class="form-input" placeholder="+1234567890" />
        </div>
        <div class="form-group">
          <label class="form-label">Remind At</label>
          <input v-model="newReminder.remind_at" type="datetime-local" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Reason</label>
          <textarea v-model="newReminder.reason" class="form-input" rows="2" placeholder="Why should we call back?"></textarea>
        </div>
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px">
          <button class="btn btn-secondary" @click="showReminderModal = false">Cancel</button>
          <button class="btn btn-primary" @click="addReminder" :disabled="addingReminder">{{ addingReminder ? 'Adding...' : 'Add Reminder' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useToast } from '@/composables/useToast'
import voiceAgentApi from '@/api/voiceAgent'
import VoiceOnboarding from '@/components/voice/VoiceOnboarding.vue'

const props = defineProps({ websiteId: String })
const appStore = useAppStore()
const toast = useToast()

const wid = computed(() => props.websiteId || appStore.activeWebsite?.id)

const activeTab = ref('getStarted')
const tabs = computed(() => [
  { id: 'getStarted', label: 'Get Started' },
  { id: 'calls', label: 'Call Log' },
  { id: 'todos', label: 'Todos', badge: todoStats.value.open || null },
  { id: 'calendar', label: 'Calendar', badge: events.value.length || null },
  { id: 'reminders', label: 'Reminders', badge: reminders.value.length || null },
  { id: 'phones', label: 'Phone Numbers' },
  { id: 'leadDetection', label: 'Lead Detection' },
  { id: 'settings', label: 'Settings' },
])

// State
const config = reactive({
  is_active: false,
  retell_agent_id: '',
  phone_number: '',
  greeting_message: '',
  system_prompt: '',
  business_name: '',
  business_hours: {},
  appointment_duration_minutes: 30,
  timezone: 'UTC',
})
const stats = ref({})
const calls = ref([])
const events = ref([])
const reminders = ref([])
const todos = ref([])
const todoStats = ref({})
const todoFilter = reactive({ status: '', priority: '' })
const availableSlots = ref([])
const availabilityDate = ref('')
const selectedCall = ref(null)

// Phone numbers
const phoneNumbers = ref([])
const showPhoneModal = ref(false)
const editingPhone = ref(null)
const savingPhone = ref(false)
const phoneForm = reactive({ number: '', label: '', provider: 'telnyx', is_active: true, forwarded_to_agent: true })
const mfa = reactive({
  sending: false,
  sent: false,
  channel: '',
  verificationId: '',
  code: '',
  confirming: false,
  verified: false,
  error: '',
})
function resetMfa() {
  mfa.sending = false
  mfa.sent = false
  mfa.channel = ''
  mfa.verificationId = ''
  mfa.code = ''
  mfa.confirming = false
  mfa.verified = false
  mfa.error = ''
}
function mfaBack() {
  // Step 2 → Step 1: keep the number the user typed, but drop the sent code
  // and channel choice so they can pick again or edit the number.
  mfa.sent = false
  mfa.code = ''
  mfa.channel = ''
  mfa.verificationId = ''
  mfa.error = ''
}
async function sendMfaCode(channel) {
  mfa.error = ''
  if (!phoneForm.number || !phoneForm.number.startsWith('+')) {
    mfa.error = 'Enter the number in E.164 format (e.g. +12025551234) first.'
    return
  }
  mfa.sending = true
  mfa.channel = channel
  try {
    const { data } = await voiceAgentApi.startPhoneVerification(wid.value, { number: phoneForm.number, channel })
    mfa.verificationId = data.verification_id
    mfa.sent = true
  } catch (e) {
    mfa.error = e?.response?.data?.error || 'Could not send verification code.'
  } finally {
    mfa.sending = false
  }
}
async function confirmMfaCode() {
  mfa.error = ''
  mfa.confirming = true
  try {
    await voiceAgentApi.confirmPhoneVerification(wid.value, {
      verification_id: mfa.verificationId,
      code: mfa.code,
    })
    mfa.verified = true
  } catch (e) {
    mfa.error = e?.response?.data?.error || 'Incorrect or expired code.'
  } finally {
    mfa.confirming = false
  }
}

// Context documents
const contextDocs = ref([])
const showDocModal = ref(false)
const editingDoc = ref(null)
const savingDoc = ref(false)
const docForm = reactive({ title: '', content: '', is_active: true, sort_order: 0 })

// Lead detection
const possibleLeads = ref([])
const leadActionId = ref(null)

// Loading states
const loading = reactive({ calls: false, events: false, reminders: false, todos: false, phones: false, docs: false, leads: false })
const saving = ref(false)
const webCallLoading = ref(false)
const bookingEvent = ref(false)
const addingReminder = ref(false)
const bookError = ref('')

// Modals
const showBookModal = ref(false)
const showReminderModal = ref(false)
const newEvent = reactive({ attendee_name: '', attendee_phone: '', attendee_email: '', title: '', start_time: '', end_time: '' })
const newReminder = reactive({ contact_name: '', contact_phone: '', remind_at: '', reason: '' })

const weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

const callFilter = reactive({ status: '', direction: '' })

// Track which tabs have been loaded
const _loaded = reactive({ calls: false, calendar: false, reminders: false, todos: false, settings: false, phones: false, leads: false })

onMounted(() => {
  loadConfig()
  loadStats()
  loadCalls()  // default tab
})

// Lazy-load tab data on first visit
watch(activeTab, (tab) => {
  if (tab === 'todos' && !_loaded.todos)         { loadTodos(); loadTodoStats(); _loaded.todos = true }
  if (tab === 'calendar' && !_loaded.calendar)   { loadEvents(); _loaded.calendar = true }
  if (tab === 'reminders' && !_loaded.reminders) { loadReminders(); _loaded.reminders = true }
  if (tab === 'phones' && !_loaded.phones)       { loadPhoneNumbers(); _loaded.phones = true }
  if (tab === 'leadDetection' && !_loaded.leads) { loadPossibleLeads(); _loaded.leads = true }
  if (tab === 'settings' && !_loaded.settings)   { loadContextDocs(); _loaded.settings = true }
})

// Onboarding tab event handlers
function handleOnboardingNavigate(url) {
  // Map the backend's CTA hints to the matching tab on this page so the user
  // doesn't get bounced into a route that doesn't exist yet.
  if (!url) return
  if (url.includes('/config')) activeTab.value = 'settings'
  else if (url.includes('/knowledge-base')) activeTab.value = 'settings'
  else if (url.includes('/phone-numbers')) activeTab.value = 'phones'
}

function handleTemplateApplied() {
  // Refresh anything that depends on the KB so the rest of the page reflects it.
  loadConfig()
  toast.success('Template applied to your knowledge base.')
}

async function loadConfig() {
  try {
    const data = await voiceAgentApi.getConfig(wid.value)
    Object.assign(config, data)
  } catch { /* first visit, no config yet */ }
}

async function loadStats() {
  try { stats.value = await voiceAgentApi.getCallStats(wid.value) } catch {}
}

async function loadCalls() {
  loading.calls = true
  try {
    const params = {}
    if (callFilter.status) params.status = callFilter.status
    if (callFilter.direction) params.direction = callFilter.direction
    const res = await voiceAgentApi.getCalls(wid.value, params)
    calls.value = res.results || res
  } catch {} finally { loading.calls = false }
}

async function loadEvents() {
  loading.events = true
  try {
    const res = await voiceAgentApi.getEvents(wid.value, { days: 30 })
    events.value = res.results || res
  } catch {} finally { loading.events = false }
}

async function loadReminders() {
  loading.reminders = true
  try {
    const res = await voiceAgentApi.getReminders(wid.value)
    reminders.value = res.results || res
  } catch {} finally { loading.reminders = false }
}

async function loadTodos() {
  loading.todos = true
  try {
    const params = {}
    if (todoFilter.status) params.status = todoFilter.status
    if (todoFilter.priority) params.priority = todoFilter.priority
    const res = await voiceAgentApi.getTodos(wid.value, params)
    todos.value = res.results || res
  } catch {} finally { loading.todos = false }
}

async function loadTodoStats() {
  try { todoStats.value = await voiceAgentApi.getTodoStats(wid.value) } catch {}
}

async function toggleTodo(todo) {
  const newStatus = todo.status === 'done' ? 'open' : 'done'
  await updateTodoStatus(todo.id, newStatus)
}

async function updateTodoStatus(todoId, newStatus) {
  try {
    await voiceAgentApi.updateTodo(wid.value, todoId, { status: newStatus })
    loadTodos()
    loadTodoStats()
  } catch { toast.error('Failed to update todo.') }
}

async function saveConfig() {
  saving.value = true
  try {
    const data = await voiceAgentApi.updateConfig(wid.value, { ...config })
    Object.assign(config, data)
    toast.success('Configuration saved.')
  } catch (e) {
    toast.error('Failed to save configuration.')
  } finally { saving.value = false }
}

async function startWebCall() {
  webCallLoading.value = true
  try {
    const data = await voiceAgentApi.createWebCall(wid.value)
    // Retell returns an access_token for the web SDK
    toast.success('Web call session created. Use Retell Web SDK to connect.')
    console.log('Web call data:', data)
  } catch (e) {
    toast.error('Failed to start web call.')
  } finally { webCallLoading.value = false }
}

async function checkAvailability() {
  if (!availabilityDate.value) return
  try {
    const data = await voiceAgentApi.getAvailability(wid.value, availabilityDate.value)
    availableSlots.value = data.available_slots || []
  } catch {
    availableSlots.value = []
  }
}

function prefillSlot(slot) {
  const date = availabilityDate.value
  newEvent.start_time = `${date}T${slot.start}`
  newEvent.end_time = `${date}T${slot.end}`
  showBookModal.value = true
}

async function bookAppointment() {
  bookError.value = ''
  bookingEvent.value = true
  try {
    await voiceAgentApi.createEvent(wid.value, {
      attendee_name: newEvent.attendee_name,
      attendee_phone: newEvent.attendee_phone,
      attendee_email: newEvent.attendee_email,
      title: newEvent.title,
      start_time: new Date(newEvent.start_time).toISOString(),
      end_time: newEvent.end_time ? new Date(newEvent.end_time).toISOString() : undefined,
    })
    toast.success('Appointment booked.')
    showBookModal.value = false
    Object.assign(newEvent, { attendee_name: '', attendee_phone: '', attendee_email: '', title: '', start_time: '', end_time: '' })
    loadEvents()
    loadStats()
  } catch (e) {
    bookError.value = e?.response?.data?.error || 'Failed to book appointment.'
  } finally { bookingEvent.value = false }
}

async function cancelEvent(eventId) {
  try {
    await voiceAgentApi.cancelEvent(wid.value, eventId)
    toast.success('Appointment cancelled.')
    loadEvents()
    loadStats()
  } catch {
    toast.error('Failed to cancel appointment.')
  }
}

async function addReminder() {
  addingReminder.value = true
  try {
    await voiceAgentApi.createReminder(wid.value, {
      contact_name: newReminder.contact_name,
      contact_phone: newReminder.contact_phone,
      remind_at: new Date(newReminder.remind_at).toISOString(),
      reason: newReminder.reason,
    })
    toast.success('Reminder added.')
    showReminderModal.value = false
    Object.assign(newReminder, { contact_name: '', contact_phone: '', remind_at: '', reason: '' })
    loadReminders()
  } catch {
    toast.error('Failed to add reminder.')
  } finally { addingReminder.value = false }
}

async function completeReminder(id) {
  try {
    await voiceAgentApi.updateReminder(wid.value, id, { action: 'complete' })
    toast.success('Reminder completed.')
    loadReminders()
  } catch { toast.error('Failed to update reminder.') }
}

async function dismissReminder(id) {
  try {
    await voiceAgentApi.updateReminder(wid.value, id, { action: 'dismiss' })
    toast.success('Reminder dismissed.')
    loadReminders()
  } catch { toast.error('Failed to dismiss reminder.') }
}

// ── Phone Numbers ──────────────────────────────────────────────────────────────

async function loadPhoneNumbers() {
  loading.phones = true
  try {
    const res = await voiceAgentApi.getPhoneNumbers(wid.value)
    phoneNumbers.value = res.data || res
  } catch {} finally { loading.phones = false }
}

function editPhone(num) {
  editingPhone.value = num
  Object.assign(phoneForm, {
    number: num.number,
    label: num.label,
    provider: num.provider,
    is_active: num.is_active,
    forwarded_to_agent: num.forwarded_to_agent,
  })
  showPhoneModal.value = true
}

function closePhoneModal() {
  showPhoneModal.value = false
  editingPhone.value = null
  Object.assign(phoneForm, { number: '', label: '', provider: 'telnyx', is_active: true, forwarded_to_agent: true })
  resetMfa()
}

async function savePhone() {
  savingPhone.value = true
  try {
    if (editingPhone.value) {
      await voiceAgentApi.updatePhoneNumber(wid.value, editingPhone.value.id, phoneForm)
      toast.success('Phone number updated.')
    } else {
      await voiceAgentApi.addPhoneNumber(wid.value, { ...phoneForm, verification_id: mfa.verificationId })
      toast.success('Phone number added.')
    }
    closePhoneModal()
    loadPhoneNumbers()
  } catch { toast.error('Failed to save phone number.') } finally { savingPhone.value = false }
}

async function deletePhone(id) {
  try {
    await voiceAgentApi.deletePhoneNumber(wid.value, id)
    toast.success('Phone number removed.')
    loadPhoneNumbers()
  } catch { toast.error('Failed to remove phone number.') }
}

// ── Context Documents ──────────────────────────────────────────────────────────

async function loadContextDocs() {
  loading.docs = true
  try {
    const res = await voiceAgentApi.getContextDocs(wid.value)
    contextDocs.value = res.data || res
  } catch {} finally { loading.docs = false }
}

function editDoc(doc) {
  editingDoc.value = doc
  Object.assign(docForm, {
    title: doc.title,
    content: doc.content,
    is_active: doc.is_active,
    sort_order: doc.sort_order,
  })
  showDocModal.value = true
}

function closeDocModal() {
  showDocModal.value = false
  editingDoc.value = null
  Object.assign(docForm, { title: '', content: '', is_active: true, sort_order: 0 })
}

async function saveDoc() {
  savingDoc.value = true
  try {
    if (editingDoc.value) {
      await voiceAgentApi.updateContextDoc(wid.value, editingDoc.value.id, docForm)
      toast.success('Document updated.')
    } else {
      await voiceAgentApi.createContextDoc(wid.value, docForm)
      toast.success('Document created.')
    }
    closeDocModal()
    loadContextDocs()
  } catch { toast.error('Failed to save document.') } finally { savingDoc.value = false }
}

async function deleteDoc(id) {
  try {
    await voiceAgentApi.deleteContextDoc(wid.value, id)
    toast.success('Document deleted.')
    loadContextDocs()
  } catch { toast.error('Failed to delete document.') }
}

const uploadingDoc = ref(false)

async function onDocFileSelected(e) {
  const file = e.target.files && e.target.files[0]
  e.target.value = ''
  if (!file) return
  if (file.size > 100 * 1024) {
    toast.error('File too large. Max 100 KB.')
    return
  }
  uploadingDoc.value = true
  try {
    const res = await voiceAgentApi.uploadContextDoc(wid.value, file)
    const data = res.data || res
    if (data.retell_sync === 'failed') {
      toast.error('Uploaded, but failed to sync to voice agent. Edit and save to retry.')
    } else {
      toast.success('Document uploaded. Live on next call.')
    }
    loadContextDocs()
  } catch (err) {
    const msg = err?.response?.data?.error || 'Upload failed.'
    toast.error(msg)
  } finally {
    uploadingDoc.value = false
  }
}

// ── Lead Detection ─────────────────────────────────────────────────────────────

async function loadPossibleLeads() {
  loading.leads = true
  try {
    const res = await voiceAgentApi.getPossibleLeads(wid.value)
    possibleLeads.value = res.results || res.data || []
  } catch {
    toast.error('Failed to load possible leads.')
  } finally {
    loading.leads = false
  }
}

async function promoteLead(call) {
  leadActionId.value = call.id
  try {
    await voiceAgentApi.promotePossibleLead(wid.value, call.id)
    toast.success('Lead created from this call.')
    possibleLeads.value = possibleLeads.value.filter(c => c.id !== call.id)
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Failed to promote lead.')
  } finally {
    leadActionId.value = null
  }
}

async function dismissLead(call) {
  leadActionId.value = call.id
  try {
    await voiceAgentApi.dismissPossibleLead(wid.value, call.id)
    possibleLeads.value = possibleLeads.value.filter(c => c.id !== call.id)
  } catch {
    toast.error('Failed to dismiss.')
  } finally {
    leadActionId.value = null
  }
}

function toggleDay(day, checked) {
  if (checked) {
    config.business_hours[day] = { start: '09:00', end: '17:00' }
  } else {
    delete config.business_hours[day]
  }
}

function formatDuration(seconds) {
  if (!seconds) return '0m'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s > 0 ? `${m}m ${s}s` : `${m}m`
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatDateTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}
</script>

<style scoped>
.voice-agent-page { max-width: 1200px; }

.agent-status-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 20px;
  border-radius: 10px;
  margin-bottom: 20px;
  border: 1px solid;
}
.agent-status-banner .status-icon { font-size: 24px; flex-shrink: 0; }
.agent-status-banner .status-content { flex: 1; }
.agent-status-banner .status-content strong { display: block; font-size: var(--font-sm); margin-bottom: 2px; }
.agent-status-banner .status-content p { margin: 0; font-size: 12px; color: var(--text-muted); line-height: 1.4; }
.agent-status-banner .status-actions { flex-shrink: 0; }
.status-enabled {
  background: rgba(34, 197, 94, 0.06);
  border-color: rgba(34, 197, 94, 0.2);
}
.status-enabled strong { color: #22c55e; }
.status-inactive {
  background: var(--bg-secondary);
  border-color: var(--border);
}

.tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}
.tab-btn {
  padding: 8px 16px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  font-size: var(--font-sm);
  display: flex;
  align-items: center;
  gap: 6px;
}
.tab-btn.active {
  color: var(--text-primary);
  border-bottom-color: var(--color-primary);
}
.tab-badge {
  background: var(--color-primary);
  color: white;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
}

.filter-row { display: flex; gap: 8px; align-items: center; }

.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.status-completed { background: rgba(34,197,94,0.12); color: #16a34a; }
.status-scheduled { background: rgba(59,130,246,0.12); color: #2563eb; }
.status-confirmed { background: rgba(34,197,94,0.12); color: #16a34a; }
.status-in_progress { background: rgba(245,158,11,0.12); color: #d97706; }
.status-missed, .status-failed { background: rgba(239,68,68,0.12); color: #dc2626; }
.status-cancelled { background: rgba(107,114,128,0.12); color: #6b7280; }
.status-no_show { background: rgba(239,68,68,0.08); color: #9ca3af; }
.status-pending { background: rgba(245,158,11,0.12); color: #d97706; }
.status-sent { background: rgba(59,130,246,0.12); color: #2563eb; }
.status-dismissed { background: rgba(107,114,128,0.12); color: #6b7280; }
.status-ringing { background: rgba(168,85,247,0.12); color: #7c3aed; }

.sentiment-badge { padding: 2px 8px; border-radius: 12px; font-size: 12px; }
.sentiment-positive { background: rgba(34,197,94,0.12); color: #16a34a; }
.sentiment-negative { background: rgba(239,68,68,0.12); color: #dc2626; }
.sentiment-neutral { background: rgba(107,114,128,0.12); color: #6b7280; }

.clickable-row { cursor: pointer; }
.clickable-row:hover { background: var(--bg-hover); }

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.detail-item { display: flex; flex-direction: column; gap: 2px; }
.detail-label { font-size: 12px; color: var(--text-muted); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }

.transcript-box {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  margin-top: 4px;
}

.extracted-data {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 12px;
  margin-top: 4px;
}
.extracted-row { font-size: 13px; padding: 2px 0; }

.slots-row { display: flex; flex-wrap: wrap; gap: 8px; }
.slot-chip {
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.slot-chip:hover {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.reminder-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.reminder-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
}
.reminder-header { display: flex; justify-content: space-between; align-items: flex-start; }

.hours-grid { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.hours-row { display: flex; align-items: center; gap: 12px; }
.hours-day { width: 130px; display: flex; align-items: center; gap: 8px; font-size: 14px; }

.cost-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cost-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.cost-total {
  font-weight: 600;
  border-bottom: 2px solid var(--border);
}
.cost-highlight {
  font-weight: 700;
  font-size: 16px;
  color: #16a34a;
  border-bottom: none;
  padding-top: 12px;
}
.cost-retell {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-muted);
  border-bottom: none;
  padding-top: 12px;
}

.cost-option {
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
}
.cost-option-recommended {
  border-color: #16a34a;
  background: rgba(22,163,74,0.04);
}
.cost-option-header {
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cost-badge-recommended {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: #16a34a;
  color: white;
}

.savings-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(22,163,74,0.08);
  border: 1px solid rgba(22,163,74,0.2);
  border-radius: 10px;
}
.savings-amount {
  font-weight: 700;
  font-size: 18px;
  color: #16a34a;
}

.form-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.todo-list { display: flex; flex-direction: column; gap: 8px; }
.todo-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  border-left: 3px solid var(--border);
}
.todo-priority-high { border-left-color: #ef4444; }
.todo-priority-medium { border-left-color: #f59e0b; }
.todo-priority-low { border-left-color: #6b7280; }

.todo-main { display: flex; align-items: flex-start; gap: 12px; flex: 1; }
.todo-check {
  width: 22px; height: 22px; min-width: 22px;
  border: 2px solid var(--border);
  border-radius: 6px;
  background: none;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  margin-top: 2px;
}
.todo-checked { background: #16a34a; border-color: #16a34a; color: white; }
.todo-content { flex: 1; }
.todo-description { font-size: 14px; line-height: 1.4; }
.todo-done .todo-description { text-decoration: line-through; color: var(--text-muted); }
.todo-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; align-items: center; }
.todo-actions { display: flex; gap: 8px; align-items: center; }

.priority-badge { font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 8px; }
.priority-high { background: rgba(239,68,68,0.12); color: #dc2626; }
.priority-medium { background: rgba(245,158,11,0.12); color: #d97706; }
.priority-low { background: rgba(107,114,128,0.12); color: #6b7280; }

.todo-stats-row { display: flex; gap: 16px; font-size: 14px; }
.todo-stat-urgent { color: #ef4444; font-weight: 600; }

.loading-state, .empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

/* Provider badge */
.provider-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  text-transform: capitalize;
}

/* Context documents */
.docs-list { display: flex; flex-direction: column; gap: 10px; }
.doc-card {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px;
  background: var(--bg-card);
}
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}
.doc-preview {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-surface);
  border-radius: 6px;
  padding: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 80px;
  overflow: hidden;
  margin: 0;
}

.section-title {
  font-size: var(--font-base);
  font-weight: 600;
  color: var(--text-primary);
}

.getstarted-intro {
  background: linear-gradient(135deg, #eef2ff, #ecfeff);
  border: 1px solid #c7d2fe;
  border-radius: 12px;
  padding: 24px 28px;
  margin-bottom: 24px;
}
.getstarted-intro h2 {
  margin: 0 0 6px;
  font-size: 20px;
}
.getstarted-intro > p {
  margin: 0 0 12px;
  color: #475569;
  font-size: 14px;
}
.getstarted-bullets {
  margin: 0 0 12px;
  padding-left: 20px;
  font-size: 14px;
  line-height: 1.6;
  color: #1e293b;
}
.getstarted-bullets li {
  margin-bottom: 6px;
}
.getstarted-hint {
  margin: 0;
  padding: 10px 14px;
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
  border-radius: 6px;
  font-size: 13px;
  color: #78350f;
}
</style>
