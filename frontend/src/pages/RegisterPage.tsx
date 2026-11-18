import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@/lib/zodResolver'
import * as z from 'zod'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { FileText, AlertCircle, Lock, Mail, User as UserIcon, ArrowRight } from 'lucide-react'

const registerSchema = z
  .object({
    email: z.string().email('Please enter a valid email address'),
    fullName: z.string().min(2, 'Name must be at least 2 characters'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  })

type RegisterFormValues = z.infer<typeof registerSchema>

export function RegisterPage() {
  const { register: registerAuth } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (values: RegisterFormValues) => {
    setServerError(null)
    try {
      await registerAuth({
        email: values.email,
        password: values.password,
        full_name: values.fullName,
      })
      navigate('/dashboard')
    } catch (err: any) {
      setServerError(err.message || 'Registration failed. An account with this email may already exist.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50/50 dark:bg-gray-950">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center space-x-2.5">
            <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <FileText className="h-5 w-5" />
            </div>
            <span className="font-bold text-xl tracking-tight text-foreground">
              DocAssistant
            </span>
          </Link>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-foreground">
            Create your researcher account
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Secure, tenant-isolated document indexing and citation grounding
          </p>
        </div>

        <Card className="shadow-lg border-gray-200 dark:border-gray-800">
          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="pt-6 space-y-4">
              {serverError && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 flex items-start space-x-2 text-xs text-red-700 dark:text-red-300">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{serverError}</span>
                </div>
              )}

              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground flex items-center space-x-1">
                  <UserIcon className="h-3.5 w-3.5 text-gray-400" />
                  <span>Full name</span>
                </label>
                <Input
                  placeholder="Dr. Elena Rostova"
                  {...register('fullName')}
                  error={errors.fullName?.message}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground flex items-center space-x-1">
                  <Mail className="h-3.5 w-3.5 text-gray-400" />
                  <span>Email address</span>
                </label>
                <Input
                  type="email"
                  placeholder="name@institution.edu"
                  {...register('email')}
                  error={errors.email?.message}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground flex items-center space-x-1">
                  <Lock className="h-3.5 w-3.5 text-gray-400" />
                  <span>Password</span>
                </label>
                <Input
                  type="password"
                  placeholder="••••••••"
                  {...register('password')}
                  error={errors.password?.message}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground flex items-center space-x-1">
                  <Lock className="h-3.5 w-3.5 text-gray-400" />
                  <span>Confirm password</span>
                </label>
                <Input
                  type="password"
                  placeholder="••••••••"
                  {...register('confirmPassword')}
                  error={errors.confirmPassword?.message}
                />
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium"
                  isLoading={isSubmitting}
                >
                  <span>Create Account</span>
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </form>

          <CardFooter className="border-t border-gray-100 dark:border-gray-800/60 justify-center py-4 text-xs text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="ml-1 text-blue-600 hover:underline font-medium">
              Sign In
            </Link>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
