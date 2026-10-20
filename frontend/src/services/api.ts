import {
  DepartmentSummarySchema,
  EmployeeInputSchema,
  EmployeeListSchema,
  EmployeeSchema,
  type Department,
  type DepartmentSummary,
  type Employee,
  type EmployeeInput,
} from '../lib/employee'
import { z } from 'zod'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const RuntimeConfigurationSchema = z.object({
  provider: z.string(),
  provider_label: z.string(),
  model: z.string(),
})

class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, schema: { parse: (value: unknown) => T }, init?: RequestInit): Promise<T> {
  const { headers, ...requestInit } = init ?? {}
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...requestInit,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
  const payload: unknown = response.status === 204 ? undefined : await response.json()
  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? String(payload.detail)
        : 'The request could not be completed.'
    throw new ApiError(detail, response.status)
  }
  return schema.parse(payload)
}

export const employeeApi = {
  runtimeConfiguration: () => request('/api/runtime/config', RuntimeConfigurationSchema),
  list: (query: string, department: Department | 'All') => {
    const params = new URLSearchParams()
    if (query.trim()) params.set('query', query.trim())
    if (department !== 'All') params.set('department', department)
    const suffix = params.size ? `?${params.toString()}` : ''
    return request(`/api/employees${suffix}`, EmployeeListSchema)
  },
  summary: () => request('/api/departments/summary', {
    parse: (value: unknown) => DepartmentSummarySchema.array().parse(value),
  }),
  create: (employee: EmployeeInput, confirmationToken: string): Promise<Employee> => {
    const validated = EmployeeInputSchema.parse(employee)
    return request('/api/employees', EmployeeSchema, {
      method: 'POST',
      headers: { 'X-Confirmation-Token': confirmationToken },
      body: JSON.stringify(validated),
    })
  },
  get: (employeeId: number) => request(`/api/employees/${employeeId}`, EmployeeSchema),
  issueApproval: (
    action: 'create' | 'update' | 'delete',
    payload: Record<string, unknown>,
    employeeId?: number,
  ) =>
    request('/api/approvals', z.object({ confirmation_token: z.string() }), {
      method: 'POST',
      body: JSON.stringify({ action, employee_id: employeeId, payload }),
    }),
}

export type RuntimeConfiguration = z.infer<typeof RuntimeConfigurationSchema>
export type { ApiError, DepartmentSummary }
