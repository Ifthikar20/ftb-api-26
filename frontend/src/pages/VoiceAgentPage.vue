<template>
  <div class="voice-agent-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Voice Agent</h1>
        <p class="page-subtitle">AI-powered phone agent that handles calls, books appointments, and captures leads.</p>
      </div>
      <div class="header-actions">
        <button v-if="config.is_active" class="btn btn-secondary btn-sm" @click="startWebCall" :disabled="webCallLoading">
          {{ webCallLoading ? 'Connecting...' : 'Test Call' }}
        </button>
        <button class="btn btn-sm" :class="config.is_active ? 'btn-danger' : 'btn-primary'" @click="toggleAgent" :disabled="activating">
          {{ activating ? 'Processing...' : (config.is_active ? 'Deactivate Agent' : 'Activate Agent') }}
        </button>
      </div>
    </div>

    <!-- Stats Row -->
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

      <!-- Cost Estimator -->
      <div class="card" style="max-width: 700px; margin-top: 24px">
        <h3 class="card-title" style="margin-bottom: 12px">Cost Comparison</h3>
        <p class="text-sm text-muted" style="margin-bottom: 16px">Two deployment options. Self-hosted saves 88-94%.</p>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px">
          <!-- Retell AI (Managed) -->
          <div class="cost-option">
            <div class="cost-option-header" style="color: var(--text-muted)">
              <h4 style="margin:0">Retell AI (Managed)</h4>
              <span class="text-xs">Easy setup, higher cost</span>
            </div>
            <div class="cost-grid">
              <div class="cost-row"><span>Platform fee</span><span>$0.07-0.10</span></div>
              <div class="cost-row"><span>LLM</span><span>$0.03-0.08</span></div>
              <div class="cost-row"><span>STT</span><span>$0.01-0.02</span></div>
              <div class="cost-row"><span>TTS</span><span>$0.02-0.05</span></div>
              <div class="cost-row"><span>Telephony</span><span>$0.01-0.02</span></div>
              <div class="cost-row cost-total"><span>Per minute</span><span>$0.14-0.27</span></div>
              <div class="cost-row cost-retell"><span>20-min call</span><span>$2.80-5.40</span></div>
            </div>
          </div>

          <!-- Self-Hosted (LiveKit) -->
          <div class="cost-option cost-option-recommended">
            <div class="cost-option-header">
              <h4 style="margin:0">Self-Hosted (LiveKit)</h4>
              <span class="cost-badge-recommended">Recommended</span>
            </div>
            <div class="cost-grid">
              <div class="cost-row"><span>Telnyx SIP</span><span>$0.005</span></div>
              <div class="cost-row"><span>Deepgram STT</span><span>$0.004</span></div>
              <div class="cost-row"><span>GPT-4o-mini</span><span>$0.0002</span></div>
              <div class="cost-row"><span>TTS (self-hosted)</span><span>$0.003</span></div>
              <div class="cost-row"><span>GPU infra</span><span>$0.006</span></div>
              <div class="cost-row cost-total"><span>Per minute</span><span>~$0.017</span></div>
              <div class="cost-row cost-highlight"><span>20-min call</span><span>~$0.34</span></div>
            </div>
          </div>
        </div>

        <div class="savings-banner" style="margin-top: 20px">
          <span class="savings-amount">Save 88-94%</span>
          <span class="text-sm">Self-hosted: ~$170/mo for 10K minutes vs Retell: ~$2,000/mo</span>
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
        <h3 class="card-title" style="margin-bottom: 16px">Book Appointment</h3>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useToast } from '@/composables/useToast'
import voiceAgentApi from '@/api/voiceAgent'

const props = defineProps({ websiteId: String })
const appStore = useAppStore()
const toast = useToast()

const wid = computed(() => props.websiteId || appStore.activeWebsite?.id)

const activeTab = ref('calls')
const tabs = computed(() => [
  { id: 'calls', label: 'Call Log' },
  { id: 'todos', label: 'Todos', badge: todoStats.value.open || null },
  { id: 'calendar', label: 'Calendar', badge: events.value.length || null },
  { id: 'reminders', label: 'Reminders', badge: reminders.value.length || null },
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

// Loading states
const loading = reactive({ calls: false, events: false, reminders: false, todos: false })
const saving = ref(false)
const activating = ref(false)
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

onMounted(() => {
  loadConfig()
  loadStats()
  loadCalls()
  loadEvents()
  loadReminders()
  loadTodos()
  loadTodoStats()
})

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

async function toggleAgent() {
  activating.value = true
  const action = config.is_active ? 'deactivate' : 'activate'
  try {
    const data = await voiceAgentApi.activate(wid.value, action)
    Object.assign(config, data)
    toast.success(`Voice agent ${action}d.`)
  } catch (e) {
    toast.error(`Failed to ${action} agent.`)
  } finally { activating.value = false }
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
</style>
