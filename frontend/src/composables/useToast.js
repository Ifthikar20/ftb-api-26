import { ref } from 'vue'

/**
 * Global toast notification system.
 * Shows calming, user-friendly messages — never raw errors.
 *
 * Usage:
 *   import { useToast } from '@/composables/useToast'
 *   const toast = useToast()
 *   toast.error('Something went wrong')
 *   toast.success('Action completed')
 */

const toasts = ref([])
let _id = 0

const TOAST_TYPES = {
    success: { icon: '✓', duration: 4000 },
    error: { icon: '!', duration: 6000 },
    warning: { icon: '⚠', duration: 5000 },
    info: { icon: 'ℹ', duration: 4000 },
}

function addToast(type, message) {
    const id = ++_id
    const config = TOAST_TYPES[type] || TOAST_TYPES.info

    toasts.value.push({ id, type, message, icon: config.icon, leaving: false })

    // Auto-remove after duration
    setTimeout(() => {
        removeToast(id)
    }, config.duration)

    // Max 5 visible toasts
    if (toasts.value.length > 5) {
        removeToast(toasts.value[0].id)
    }
}

function removeToast(id) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) {
        toasts.value[idx].leaving = true
        setTimeout(() => {
            toasts.value = toasts.value.filter(t => t.id !== id)
        }, 300)
    }
}

export function useToast() {
    return {
        toasts,
        success: (msg) => addToast('success', msg),
        error: (msg) => addToast('error', msg || 'Something went wrong. Please try again.'),
        warning: (msg) => addToast('warning', msg),
        info: (msg) => addToast('info', msg),
        remove: removeToast,
    }
}
