export type ThemeChoice = 'system' | 'light' | 'dark'
const KEY = 'rag-theme'

function read(): ThemeChoice {
  try {
    const value = localStorage.getItem(KEY)
    return value === 'light' || value === 'dark' ? value : 'system'
  } catch {
    return 'system'
  }
}

export function currentTheme() {
  return read()
}

export function applyTheme(choice: ThemeChoice = read()) {
  const dark = choice === 'dark' || (choice === 'system' && window.matchMedia?.('(prefers-color-scheme: dark)').matches)
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
}

export function setTheme(choice: ThemeChoice) {
  try {
    localStorage.setItem(KEY, choice)
  } catch {
    // The choice still applies to this page view.
  }
  applyTheme(choice)
}
