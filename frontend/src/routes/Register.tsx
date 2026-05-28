import { useNavigate, Link } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Logo } from "@/components/Logo"
import { login, register } from "@/lib/api/auth"
import { ApiError } from "@/lib/api/client"

const schema = z
  .object({
    username: z.string().min(1, "Required"),
    email: z.string().email("Must be a valid email"),
    password1: z.string().min(6, "At least 6 characters"),
    password2: z.string().min(1, "Required"),
  })
  .refine((v) => v.password1 === v.password2, {
    path: ["password2"],
    message: "Passwords do not match",
  })

type FormValues = z.infer<typeof schema>

export default function Register() {
  const navigate = useNavigate()
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { username: "", email: "", password1: "", password2: "" },
  })

  async function onSubmit(values: FormValues) {
    try {
      await register({
        username: values.username,
        email: values.email,
        password1: values.password1,
        password2: values.password2,
        role: null,
      })
      // Auto-login after register.
      await login(values.username, values.password1)
      toast.success("Welcome aboard")
      navigate("/", { replace: true })
    } catch (err) {
      console.error("[register] failed:", err)
      if (err instanceof ApiError) {
        toast.error(err.message)
      } else {
        toast.error("Could not create account")
      }
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-4">
          <Logo />
          <div>
            <CardTitle>Create account</CardTitle>
            <CardDescription>School Bell admin console</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="flex flex-col gap-4"
            >
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Username</FormLabel>
                    <FormControl>
                      <Input autoFocus {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password1"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password2"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm password</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button
                type="submit"
                disabled={form.formState.isSubmitting}
                className="w-full"
              >
                {form.formState.isSubmitting ? "Creating..." : "Create account"}
              </Button>
            </form>
          </Form>
        </CardContent>
        <CardFooter className="flex justify-center">
          <Link
            to="/login"
            className="text-sm text-muted-foreground hover:underline"
          >
            Already have an account? Sign in
          </Link>
        </CardFooter>
      </Card>
    </div>
  )
}
