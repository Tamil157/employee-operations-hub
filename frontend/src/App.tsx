import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { CopilotSidebar, useFrontendTool } from '@copilotkit/react-core/v2'
import { z } from 'zod'
import {
  departments,
  EmployeeInputSchema,
  emptyEmployee,
  type Department,
  type DepartmentSummary,
  type Employee,
  type EmployeeInput,
} from './lib/employee'
import { employeeApi, type RuntimeConfiguration } from './services/api'
import './App.css'

type AgentApproval = {
  employee: EmployeeInput
  resolve: (result: { approved: boolean; confirmation_token?: string; message: string }) => void
}

const summaryFor = (summary: DepartmentSummary[], department: Department) =>
  summary.find((item) => item.department === department)?.count ?? 0

const initialsFor = (name: string) => name.split(' ').map((part) => part[0]).join('').slice(0, 2)

function App() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [summary, setSummary] = useState<DepartmentSummary[]>([])
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState<Department | 'All'>('All')
  const [form, setForm] = useState<EmployeeInput>(emptyEmployee)
  const [pendingEmployee, setPendingEmployee] = useState<EmployeeInput | null>(null)
  const [agentApproval, setAgentApproval] = useState<AgentApproval | null>(null)
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null)
  const [agentSummary, setAgentSummary] = useState<DepartmentSummary[] | null>(null)
  const [runtimeConfiguration, setRuntimeConfiguration] = useState<RuntimeConfiguration | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const totalEmployees = useMemo(
    () => summary.reduce((total, item) => total + item.count, 0),
    [summary],
  )

  async function loadData(nextQuery = query, nextDepartment = department) {
    try {
      const [list, nextSummary] = await Promise.all([
        employeeApi.list(nextQuery, nextDepartment),
        employeeApi.summary(),
      ])
      setError(null)
      setEmployees(list.items)
      setSummary(nextSummary)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load employees.')
    } finally {
      setLoading(false)
    }
  }

  // Synchronize the filter state with the remote SQLite-backed directory.
  useEffect(() => {
    const requestId = window.setTimeout(() => {
      void loadData(query, department)
    }, 0)
    return () => window.clearTimeout(requestId)
  }, [query, department])

  useEffect(() => {
    void employeeApi.runtimeConfiguration()
      .then(setRuntimeConfiguration)
      .catch(() => setRuntimeConfiguration(null))
  }, [])

  function requestAgentApproval(candidate: unknown) {
    const validated = EmployeeInputSchema.safeParse(candidate)
    if (!validated.success) {
      return Promise.resolve({
        approved: false,
        message: `The proposed employee details were rejected: ${validated.error.issues[0]?.message ?? 'invalid fields'}. Reissue the tool call with only the five requested employee values.`,
      })
    }
    return new Promise<{ approved: boolean; confirmation_token?: string; message: string }>((resolve) => {
      setAgentApproval({ employee: validated.data, resolve })
    })
  }

  useEmployeeAssistant({
    setForm,
    setQuery,
    setDepartment,
    setSelectedEmployee,
    setAgentSummary,
    requestAgentApproval,
    refreshDirectory: () => loadData(query, department),
  })

  function updateForm(field: keyof EmployeeInput, value: string) {
    setForm((current) => ({ ...current, [field]: value }) as EmployeeInput)
  }

  function openEmployeeForm() {
    document.getElementById('employee-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  function clearDirectoryFilters() {
    setQuery('')
    setDepartment('All')
    document.getElementById('directory')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function showCurrentSummary() {
    setAgentSummary(summary)
    document.getElementById('department-summary')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  function stageEmployee(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice(null)
    const result = EmployeeInputSchema.safeParse(form)
    if (!result.success) {
      setError(result.error.issues[0]?.message ?? 'Review the employee details.')
      return
    }
    setError(null)
    setPendingEmployee(result.data)
  }

  async function createAfterConfirmation(employee: EmployeeInput) {
    const approval = await employeeApi.issueApproval('create', employee)
    return employeeApi.create(employee, approval.confirmation_token)
  }

  async function confirmManualCreate() {
    if (!pendingEmployee) return
    setSaving(true)
    setError(null)
    try {
      const created = await createAfterConfirmation(pendingEmployee)
      setPendingEmployee(null)
      setForm(emptyEmployee)
      setNotice(`${created.name} was added to the employee directory.`)
      await loadData(query, department)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to create employee.')
    } finally {
      setSaving(false)
    }
  }

  async function resolveAgentApproval(approved: boolean) {
    if (!agentApproval) return
    const request = agentApproval
    setSaving(true)
    try {
      if (!approved) {
        request.resolve({ approved: false, message: 'User declined employee creation.' })
        return
      }
      const approval = await employeeApi.issueApproval('create', request.employee)
      request.resolve({
        approved: true,
        confirmation_token: approval.confirmation_token,
        message: 'User approved this one employee creation.',
      })
      setNotice(`${request.employee.name} was approved for one-time creation.`)
    } catch (caught) {
      request.resolve({
        approved: false,
        message: caught instanceof Error ? caught.message : 'Approval could not be issued.',
      })
      setError(caught instanceof Error ? caught.message : 'Approval could not be issued.')
    } finally {
      setAgentApproval(null)
      setSaving(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="hero" id="dashboard">
        <div className="hero-copy">
          <p className="eyebrow">Employee Operations Hub</p>
          <h1>Make employee operations feel effortless.</h1>
          <p>Manage your directory, prepare records, and use the assistant for focused actions.</p>
        </div>
        <div className="hero-status">
          <div className="status-pill"><span /> System ready</div>
          <section className="runtime-card" aria-label="Assistant model configuration">
            <span>Assistant model</span>
            <strong>{runtimeConfiguration?.provider_label ?? 'Connecting...'}</strong>
            <small>{runtimeConfiguration?.model ?? 'Checking configuration'}</small>
          </section>
        </div>
      </header>

      <main>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {notice && <div className="alert alert-success" role="status">{notice}</div>}

        <section className="metrics" aria-label="Employee statistics">
          <article className="metric total"><span>Team overview</span><strong>{totalEmployees}</strong><small>Employees in the directory</small></article>
          {departments.map((item) => (
            <article className="metric" key={item}>
              <span>{item}</span><strong>{summaryFor(summary, item)}</strong><small>Active team members</small>
            </article>
          ))}
        </section>

        <section className="content-grid">
          <article className="panel directory-panel" id="directory">
            <div className="panel-heading">
              <div><p className="eyebrow">Directory</p><h2>Employees <span className="count-badge">{employees.length}</span></h2></div>
              <button className="button button-secondary" type="button" onClick={() => void loadData()}>Refresh</button>
            </div>
            <div className="filters">
              <input aria-label="Search employees" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, email, or role" />
              <select aria-label="Filter by department" value={department} onChange={(event) => setDepartment(event.target.value as Department | 'All')}>
                <option value="All">All departments</option>
                {departments.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              <button className="button" type="button" onClick={() => void loadData()}>Apply filters</button>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Employee</th><th>Department</th><th>Designation</th><th>Joined</th></tr></thead>
                <tbody>
                  {loading && <tr><td colSpan={4} className="empty">Loading directory...</td></tr>}
                  {!loading && employees.length === 0 && <tr><td colSpan={4} className="empty">No employees match these filters.</td></tr>}
                  {!loading && employees.map((employee) => (
                    <tr key={employee.id} className="clickable-row" onClick={() => setSelectedEmployee(employee)}>
                      <td><div className="employee-cell"><span className="avatar">{initialsFor(employee.name)}</span><div><strong>{employee.name}</strong><span>{employee.email}</span></div></div></td>
                      <td><span className="tag">{employee.department}</span></td>
                      <td>{employee.designation}</td>
                      <td>{employee.joining_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <aside className="sidebar">
            <section className="panel employee-form" id="employee-form">
              <div className="panel-heading"><div><p className="eyebrow">New record</p><h2>Add employee</h2></div><span className="form-step">Step 1 of 2</span></div>
              <form onSubmit={stageEmployee}>
                <label>Name<input value={form.name} onChange={(event) => updateForm('name', event.target.value)} placeholder="Arun Kumar" /></label>
                <label>Email<input type="email" value={form.email} onChange={(event) => updateForm('email', event.target.value)} placeholder="arun@example.com" /></label>
                <label>Department<select value={form.department} onChange={(event) => updateForm('department', event.target.value)}>{departments.map((item) => <option key={item}>{item}</option>)}</select></label>
                <label>Designation<input value={form.designation} onChange={(event) => updateForm('designation', event.target.value)} placeholder="Software Engineer" /></label>
                <label>Joining date<input type="date" value={form.joining_date} onChange={(event) => updateForm('joining_date', event.target.value)} /></label>
                <button className="button button-full" type="submit">Review before adding</button>
              </form>
            </section>

            <section className="assistant-placeholder">
              <p className="eyebrow">Workspace shortcuts</p>
              <h2>Keep work moving</h2>
              <p>Use the assistant for guided actions, or jump straight to a common task.</p>
              <div className="quick-actions">
                <button type="button" onClick={openEmployeeForm}>Open registration form</button>
                <button type="button" onClick={clearDirectoryFilters}>Clear directory filters</button>
                <button type="button" onClick={showCurrentSummary}>View department summary</button>
              </div>
            </section>
          </aside>
        </section>

        {agentSummary && (
          <section className="panel generated-summary" id="department-summary">
            <div className="panel-heading"><div><p className="eyebrow">Validated dynamic UI</p><h2>Department distribution</h2></div><button className="button button-secondary" type="button" onClick={() => setAgentSummary(null)}>Close</button></div>
            {agentSummary.map((item) => <div className="bar-row" key={item.department}><span>{item.department}</span><div><i style={{ width: `${Math.max(8, item.count * 20)}%` }} /></div><strong>{item.count}</strong></div>)}
          </section>
        )}
      </main>

      {pendingEmployee && (
        <EmployeeConfirmationDialog
          employee={pendingEmployee}
          saving={saving}
          title={`Add ${pendingEmployee.name}?`}
          onCancel={() => setPendingEmployee(null)}
          onApprove={() => void confirmManualCreate()}
        />
      )}
      {agentApproval && (
        <EmployeeConfirmationDialog
          employee={agentApproval.employee}
          saving={saving}
          title={`Approve creation of ${agentApproval.employee.name}?`}
          onCancel={() => void resolveAgentApproval(false)}
          onApprove={() => void resolveAgentApproval(true)}
        />
      )}
      {selectedEmployee && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="details-title">
            <p className="eyebrow">Employee details</p><h2 id="details-title">{selectedEmployee.name}</h2>
            <dl><dt>Email</dt><dd>{selectedEmployee.email}</dd><dt>Team</dt><dd>{selectedEmployee.department}</dd><dt>Role</dt><dd>{selectedEmployee.designation}</dd><dt>Joining</dt><dd>{selectedEmployee.joining_date}</dd></dl>
            <div className="dialog-actions"><button className="button" type="button" onClick={() => setSelectedEmployee(null)}>Close</button></div>
          </section>
        </div>
      )}
      <CopilotSidebar
        defaultOpen
        labels={{
          modalHeaderTitle: 'Employee Operations Hub',
          welcomeMessageText: 'How can I help with employee operations today?',
          chatInputPlaceholder: 'Ask about employees...',
          chatDisclaimerText: 'Review important information before taking action.',
        }}
      />
    </div>
  )
}

function EmployeeConfirmationDialog({ employee, saving, title, onCancel, onApprove }: {
  employee: EmployeeInput
  saving: boolean
  title: string
  onCancel: () => void
  onApprove: () => void
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <p className="eyebrow">Confirmation required</p><h2 id="confirm-title">{title}</h2>
        <p>Review the proposed employee record. The backend permits one matching write only after you approve.</p>
        <dl><dt>Email</dt><dd>{employee.email}</dd><dt>Team</dt><dd>{employee.department}</dd><dt>Role</dt><dd>{employee.designation}</dd><dt>Joining</dt><dd>{employee.joining_date}</dd></dl>
        <div className="dialog-actions"><button className="button button-secondary" type="button" disabled={saving} onClick={onCancel}>Cancel</button><button className="button" type="button" disabled={saving} onClick={onApprove}>{saving ? 'Processing...' : 'Approve and continue'}</button></div>
      </section>
    </div>
  )
}

function useEmployeeAssistant({ setForm, setQuery, setDepartment, setSelectedEmployee, setAgentSummary, requestAgentApproval, refreshDirectory }: {
  setForm: (employee: EmployeeInput) => void
  setQuery: (query: string) => void
  setDepartment: (department: Department | 'All') => void
  setSelectedEmployee: (employee: Employee) => void
  setAgentSummary: (summary: DepartmentSummary[]) => void
  requestAgentApproval: (employee: unknown) => Promise<{ approved: boolean; confirmation_token?: string; message: string }>
  refreshDirectory: () => Promise<void>
}) {
  useFrontendTool({
    name: 'open_employee_form',
    description: 'Open and focus the employee registration form in the browser.',
    parameters: z.object({}),
    handler: async () => {
      document.getElementById('employee-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return { message: 'Employee form is visible.' }
    },
  })
  useFrontendTool({
    name: 'fill_employee_form',
    description: 'Populate the employee registration form without saving it.',
    parameters: EmployeeInputSchema,
    handler: async (args) => {
      setForm(args)
      document.getElementById('employee-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return { message: 'Form populated. No employee was created.' }
    },
  })
  useFrontendTool({
    name: 'filter_employee_table',
    description: 'Update the visible employee directory filters by a query and/or department. Use clear_employee_filters when the user asks to clear all filters.',
    parameters: z.object({ query: z.string().optional(), department: z.enum([...departments, 'All'] as const).optional() }),
    handler: async ({ query: nextQuery, department: nextDepartment }) => {
      if (nextQuery === undefined && nextDepartment === undefined) {
        setQuery('')
        setDepartment('All')
        document.getElementById('directory')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        return { message: 'Employee directory filters cleared. The full directory is now displayed.' }
      }
      if (nextQuery !== undefined) setQuery(nextQuery)
      if (nextDepartment) setDepartment(nextDepartment)
      document.getElementById('directory')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return { message: 'Directory filters updated.' }
    },
  })
  useFrontendTool({
    name: 'clear_employee_filters',
    description: 'Clear both employee-directory filters and show the full directory.',
    parameters: z.object({}),
    handler: async () => {
      setQuery('')
      setDepartment('All')
      document.getElementById('directory')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return { message: 'Employee directory filters cleared. The full directory is now displayed.' }
    },
  })
  useFrontendTool({
    name: 'show_employee_details',
    description: 'Show the details for one employee ID.',
    parameters: z.object({ employee_id: z.number().int().positive() }),
    handler: async ({ employee_id }) => {
      const employee = await employeeApi.get(employee_id)
      setSelectedEmployee(employee)
      return { message: `Showing ${employee.name}.`, employee_id }
    },
  })
  useFrontendTool({
    name: 'navigate_to_page',
    description: 'Navigate to an approved application section.',
    parameters: z.object({ page: z.enum(['dashboard', 'directory', 'employee-form']) }),
    handler: async ({ page }) => {
      document.getElementById(page)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return { message: `Navigated to ${page}.`, page }
    },
  })
  useFrontendTool({
    name: 'request_employee_confirmation',
    description: 'Ask the user to approve one employee record before the backend may create it.',
    parameters: EmployeeInputSchema,
    handler: requestAgentApproval,
  })
  useFrontendTool({
    name: 'refresh_employee_directory',
    description: 'Refresh the employee dashboard after a successful server-side change.',
    parameters: z.object({}),
    handler: async () => {
      await refreshDirectory()
      return { message: 'Employee directory refreshed from the database.' }
    },
  })
  useFrontendTool({
    name: 'render_department_summary',
    description: 'Render a validated department summary card and bar chart using authoritative backend data.',
    parameters: z.object({}),
    handler: async () => {
      const summary = await employeeApi.summary()
      setAgentSummary(summary)
      return { message: 'Rendered department summary from the current employee database.' }
    },
  })
}

export default App
