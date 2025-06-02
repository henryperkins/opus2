/**
 * Format a date into a readable string
 * @param {Date|string} date - The date to format
 * @returns {string} Formatted date string
 */
export function formatDate(date) {
  try {
    const d = new Date(date)
    if (isNaN(d.getTime())) {
      return 'Invalid Date'
    }
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return 'Invalid Date'
  }
}

/**
 * Format file size in bytes to human readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size
 */
export function formatFileSize(bytes) {
  if (bytes <= 0) return '0 B'
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  // For bytes, don't show decimal places
  const value = bytes / Math.pow(k, i)
  const formatted = i === 0 ? Math.floor(value) : value.toFixed(1)
  
  return `${formatted} ${units[i]}`
}

/**
 * Format time difference as "X time ago"
 * @param {Date|string} date - The past date
 * @returns {string} Formatted time ago string
 */
export function formatTimeAgo(date) {
  try {
    const d = new Date(date)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    
    if (diffMs < 0) return 'just now'
    
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffDays > 0) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    } else if (diffMinutes > 0) {
      return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`
    } else {
      return 'just now'
    }
  } catch {
    return 'just now'
  }
}