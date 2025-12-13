export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  )
}

export function LoadingText({ text = 'Loading...' }: { text?: string }) {
  return <div className="text-center py-8 text-gray-500">{text}</div>
}
