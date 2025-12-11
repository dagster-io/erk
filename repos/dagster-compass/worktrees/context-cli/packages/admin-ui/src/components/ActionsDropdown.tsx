import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'

interface Action {
  label: string
  onClick?: () => void
  href?: string
  variant?: 'default' | 'danger'
}

interface ActionsDropdownProps {
  actions: Action[]
}

export function ActionsDropdown({ actions }: ActionsDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 })

  // Calculate dropdown position when opened
  useEffect(() => {
    if (isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect()
      setDropdownPosition({
        top: rect.bottom + window.scrollY,
        left: rect.right - 224 + window.scrollX, // 224px = w-56 (14rem * 16px)
      })
    }
  }, [isOpen])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  return (
    <div className="dropdown">
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className="btn btn-secondary text-sm"
      >
        Actions ▼
      </button>

      {isOpen &&
        createPortal(
          <div
            ref={dropdownRef}
            className="dropdown-menu"
            style={{
              position: 'absolute',
              top: `${dropdownPosition.top}px`,
              left: `${dropdownPosition.left}px`,
            }}
          >
            <div className="py-1">
              {actions.map((action, index) =>
                action.href ? (
                  <a
                    key={index}
                    href={action.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => setIsOpen(false)}
                    className={
                      action.variant === 'danger'
                        ? 'dropdown-item text-red-600 hover:bg-red-50'
                        : 'dropdown-item'
                    }
                  >
                    {action.label}
                  </a>
                ) : (
                  <button
                    key={index}
                    onClick={() => {
                      action.onClick?.()
                      setIsOpen(false)
                    }}
                    className={
                      action.variant === 'danger'
                        ? 'dropdown-item text-red-600 hover:bg-red-50'
                        : 'dropdown-item'
                    }
                  >
                    {action.label}
                  </button>
                )
              )}
            </div>
          </div>,
          document.body
        )}
    </div>
  )
}
