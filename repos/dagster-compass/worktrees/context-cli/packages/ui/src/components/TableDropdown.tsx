import {useRef, useEffect} from 'react';

interface TableDropdownProps {
  suggestions: string[];
  selectedIndex: number;
  position: {top: number; left: number; width: number};
  onSelect: (table: string) => void;
  onHoverIndex: (index: number) => void;
}

export function TableDropdown({
  suggestions,
  selectedIndex,
  position,
  onSelect,
  onHoverIndex,
}: TableDropdownProps) {
  const suggestionRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (selectedIndex >= 0 && suggestionRefs.current[selectedIndex]) {
      suggestionRefs.current[selectedIndex]?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [selectedIndex]);

  if (suggestions.length === 0) {
    return (
      <div
        className="fixed z-[100] mt-1 bg-white border border-gray-300 rounded-lg shadow-lg"
        style={{
          top: `${position.top}px`,
          left: `${position.left}px`,
          width: `${position.width}px`,
        }}
      >
        <div className="px-3 py-2 text-sm text-gray-500">No matching tables found</div>
      </div>
    );
  }

  return (
    <div
      className="fixed z-[100] mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`,
        width: `${position.width}px`,
      }}
    >
      {suggestions.map((table, index) => (
        <button
          key={table}
          ref={(el) => (suggestionRefs.current[index] = el)}
          type="button"
          onMouseDown={(e) => {
            e.preventDefault();
            onSelect(table);
          }}
          onMouseEnter={() => onHoverIndex(index)}
          className={`w-full text-left px-3 py-2 text-sm focus:outline-none border-b border-gray-100 last:border-b-0 ${
            index === selectedIndex ? 'bg-blue-100 text-blue-900' : 'hover:bg-blue-50'
          }`}
        >
          <span className="font-mono text-xs">{table}</span>
        </button>
      ))}
    </div>
  );
}
