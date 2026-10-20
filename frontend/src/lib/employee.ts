import { z } from 'zod'

export const departments = ['Engineering', 'HR', 'Finance', 'Sales'] as const

export const EmployeeInputSchema = z.object({
  name: z.string().trim().min(1, 'Name is required').max(120).regex(/^[\p{L}][\p{L} .'’-]*$/u, 'Name can contain only letters, spaces, apostrophes, and hyphens').describe('Employee full name: letters, spaces, apostrophes, and hyphens only. Never XML, tool syntax, or prose.'),
  email: z.string().trim().email('Enter a valid email address'),
  department: z.enum(departments),
  designation: z.string().trim().min(1, 'Designation is required').max(120).regex(/^[\p{L}\d][\p{L}\d .,&()/-]*$/u, 'Designation contains unsupported characters').describe('Job title only. Never XML, tool syntax, or prose.'),
  joining_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Choose a joining date'),
})

export const EmployeeSchema = EmployeeInputSchema.extend({
  id: z.number().int().positive(),
})

export const EmployeeListSchema = z.object({
  items: z.array(EmployeeSchema),
  total: z.number().int().nonnegative(),
})

export const DepartmentSummarySchema = z.object({
  department: z.enum(departments),
  count: z.number().int().nonnegative(),
})

export type Department = (typeof departments)[number]
export type Employee = z.infer<typeof EmployeeSchema>
export type EmployeeInput = z.infer<typeof EmployeeInputSchema>
export type DepartmentSummary = z.infer<typeof DepartmentSummarySchema>

export const emptyEmployee: EmployeeInput = {
  name: '',
  email: '',
  department: 'Engineering',
  designation: '',
  joining_date: '',
}
