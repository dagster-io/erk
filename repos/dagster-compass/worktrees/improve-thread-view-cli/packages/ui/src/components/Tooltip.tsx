import {useState, useRef, useEffect} from 'react';
import {createPortal} from 'react-dom';

interface TooltipProps {
  content: string;
  children: React.ReactNode;
}

export function Tooltip({content, children}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({top: 0, left: 0});
  const triggerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (isVisible && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition({
        top: rect.top - 8,
        left: rect.left + rect.width / 2,
      });
    }
  }, [isVisible]);

  return (
    <>
      <span
        ref={triggerRef}
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        className="cursor-help"
      >
        {children}
      </span>

      {isVisible &&
        createPortal(
          <div
            className="fixed z-[9999] px-2 py-1 text-sm text-white bg-gray-900 rounded shadow-lg whitespace-nowrap pointer-events-none"
            style={{
              top: `${position.top}px`,
              left: `${position.left}px`,
              transform: 'translate(-50%, -100%)',
            }}
          >
            {content}
            <div
              className="absolute left-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"
              style={{
                top: '100%',
                transform: 'translateX(-50%)',
              }}
            />
          </div>,
          document.body,
        )}
    </>
  );
}
