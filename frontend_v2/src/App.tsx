import { Button } from "@/components/ui/button"

export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="flex flex-col items-center gap-4">
        <h1 className="text-3xl font-semibold">School Bell — frontend_v2</h1>
        <p className="text-muted-foreground">
          Scaffold smoke test. Tailwind + shadcn working.
        </p>
        <Button onClick={() => alert("ok")}>Click me</Button>
      </div>
    </div>
  )
}
