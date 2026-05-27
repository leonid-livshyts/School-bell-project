import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export default function NotFound() {
  return (
    <div className="min-h-screen grid place-items-center bg-background p-4">
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="text-sm text-muted-foreground">404</p>
        <h1 className="text-2xl font-semibold">Page not found</h1>
        <p className="text-muted-foreground max-w-sm">
          The page you're looking for doesn't exist or was moved.
        </p>
        <Button asChild>
          <Link to="/">Go home</Link>
        </Button>
      </div>
    </div>
  )
}
