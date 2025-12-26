import { useState } from 'react'
import { copyToClipboard } from '../utils/format'

interface CopyButtonProps {
  text: string
  label?: string
  className?: string
}

export function CopyButton({ text, label, className = '' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await copyToClipboard(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  return (
    <button
      onClick={handleCopy}
      className={`text-sm text-blue-600 hover:text-blue-800 transition-colors ${className}`}
      title={`Copy ${label || 'text'}`}
    >
      {copied ? '✓ Copied!' : label || 'Copy'}
    </button>
  )
}
