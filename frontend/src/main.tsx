import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './presentation/app/App'
import './presentation/shared/theme.css'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('#root element not found')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
