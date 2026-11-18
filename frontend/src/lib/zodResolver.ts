import type { FieldErrors, Resolver } from 'react-hook-form'
import { toNestErrors } from '@hookform/resolvers'
import type { ZodType } from 'zod'

/**
 * Universal Zod resolver compatible with both Zod v3 and Zod v4.
 * Converts issues into react-hook-form nested field errors and guarantees
 * that errors are never thrown as uncaught Promise rejections.
 */
export function zodResolver<T extends Record<string, any>>(schema: ZodType<any, any, any>): Resolver<T> {
  return async (values, _context, options) => {
    try {
      const result = await schema.safeParseAsync(values)
      if (result.success) {
        return {
          values: result.data,
          errors: {},
        }
      }

      // Zod 4 uses `issues`, Zod 3 uses `errors`
      const issues = (result.error as any).issues || (result.error as any).errors || []
      const flatErrors: Record<string, { type: string; message: string }> = {}

      for (const issue of issues) {
        const path = Array.isArray(issue.path) ? issue.path.join('.') : String(issue.path || '')
        if (path && !flatErrors[path]) {
          flatErrors[path] = {
            type: issue.code || 'validation',
            message: issue.message || 'Invalid value',
          }
        }
      }

      return {
        values: {},
        errors: toNestErrors(flatErrors, options) as FieldErrors<T>,
      }
    } catch (err: any) {
      return {
        values: {},
        errors: {
          root: {
            type: 'validation',
            message: err?.message || 'Validation failed',
          },
        } as unknown as FieldErrors<T>,
      }
    }
  }
}
