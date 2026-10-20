import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CopilotKitProvider } from '@copilotkit/react-core/v2'
import '@copilotkit/react-core/v2/styles.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CopilotKitProvider runtimeUrl={import.meta.env.VITE_AGENT_RUNTIME_URL ?? 'http://localhost:8200/api/employee-operations'} agentId="employee_operations">
      <App />
    </CopilotKitProvider>
  </StrictMode>,
)
