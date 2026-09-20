import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Dark mode handling
const applyDarkMode = (useDark: boolean) => {
  if (useDark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// Check for saved user preference or use system preference
const getDarkModePreference = () => {
  const savedPreference = localStorage.getItem('bis-compass-dark-mode')
  if (savedPreference !== null) {
    return savedPreference === 'true'
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

// Apply dark mode on initial load
applyDarkMode(getDarkModePreference())

// Listen for changes in system preference
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  // Only change if user hasn't explicitly set a preference
  if (localStorage.getItem('bis-compass-dark-mode') === null) {
    applyDarkMode(e.matches)
  }
})

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)