import { config } from 'dotenv'
import { createServer } from 'node:http'
import { HttpAgent } from '@ag-ui/client'
import { CopilotRuntime } from '@copilotkit/runtime/v2'
import { createCopilotNodeListener } from '@copilotkit/runtime/v2/node'

config({ path: new URL('../.env', import.meta.url) })

const runtime = new CopilotRuntime({
  agents: { employee_operations: new HttpAgent({ url: process.env.AGENT_BACKEND_URL ?? 'http://127.0.0.1:8000/agent' }) },
})

createServer(createCopilotNodeListener({ runtime, basePath: '/api/employee-operations', cors: true })).listen(8200, () => {
  console.log('Employee Operations runtime: http://127.0.0.1:8200/api/employee-operations')
})
