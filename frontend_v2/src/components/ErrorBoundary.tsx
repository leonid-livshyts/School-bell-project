import { Component, type ReactNode } from "react"
import { Button } from "@/components/ui/button"

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: { componentStack?: string | null }) {
    console.error("ErrorBoundary:", error, info)
  }

  reset = () => this.setState({ error: null })

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen grid place-items-center p-4 bg-background">
          <div className="max-w-md w-full text-center flex flex-col gap-4">
            <h1 className="text-2xl font-semibold">Something broke</h1>
            <p className="text-muted-foreground">
              An unexpected error happened in the UI. The console has the
              details.
            </p>
            <details className="text-left text-xs bg-muted/40 rounded-md p-3">
              <summary className="cursor-pointer">Show error</summary>
              <pre className="mt-2 whitespace-pre-wrap break-words">
                {this.state.error.message}
              </pre>
            </details>
            <Button onClick={this.reset}>Try again</Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
