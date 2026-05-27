import { useEffect } from "react"

const SUFFIX = "School Bell"

export function useDocumentTitle(title?: string) {
  useEffect(() => {
    const prev = document.title
    document.title = title ? `${title} · ${SUFFIX}` : SUFFIX
    return () => {
      document.title = prev
    }
  }, [title])
}
