import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { LanguageProvider } from './i18n/LanguageContext'
import { CaseProvider } from './context/CaseContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LanguageProvider>
      <CaseProvider>
        <App />
      </CaseProvider>
    </LanguageProvider>
  </StrictMode>,
)

