import {useState, useRef, useEffect, useMemo} from 'react';
import {TableDropdown} from './TableDropdown';

interface TableInputWithAutocompleteProps {
  selectedTables: string[];
  availableTables: string[];
  loadingTables: boolean;
  disabled: boolean;
  onAddTable: (tableName: string) => void;
  onRemoveTable: (tableName: string) => void;
}

export function TableInputWithAutocomplete({
  selectedTables,
  availableTables,
  loadingTables,
  disabled,
  onAddTable,
  onRemoveTable,
}: TableInputWithAutocompleteProps) {
  const [inputValue, setInputValue] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);
  const [dropdownPosition, setDropdownPosition] = useState({top: 0, left: 0, width: 0});
  const inputRef = useRef<HTMLInputElement>(null);

  // Memoize filtered suggestions to avoid redundant filtering on every render
  const filteredSuggestions = useMemo(() => {
    const unselectedTables = availableTables.filter((table) => !selectedTables.includes(table));

    if (!inputValue.trim()) {
      return unselectedTables;
    }
    const searchTerm = inputValue.toLowerCase();
    return unselectedTables.filter((table) => table.toLowerCase().includes(searchTerm));
  }, [availableTables, selectedTables, inputValue]);

  useEffect(() => {
    const updatePosition = () => {
      if (inputRef.current && showSuggestions) {
        const rect = inputRef.current.getBoundingClientRect();
        setDropdownPosition({
          top: rect.bottom + window.scrollY,
          left: rect.left + window.scrollX,
          width: rect.width,
        });
      }
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);

    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
    };
  }, [showSuggestions]);

  const addTable = (tableName: string) => {
    const trimmedName = tableName.trim();
    if (trimmedName && !selectedTables.includes(trimmedName)) {
      onAddTable(trimmedName);
      setInputValue('');
      setShowSuggestions(false);
      setSelectedSuggestionIndex(-1);
    }
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    setInputValue(newValue);
    const shouldShow = availableTables.length > 0;
    setShowSuggestions(shouldShow);
    setSelectedSuggestionIndex(-1);
  };

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (!showSuggestions && availableTables.length > 0) {
        setShowSuggestions(true);
        setSelectedSuggestionIndex(0);
      } else if (filteredSuggestions.length > 0) {
        setSelectedSuggestionIndex((prev) =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : prev,
        );
      }
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (selectedSuggestionIndex > 0) {
        setSelectedSuggestionIndex((prev) => prev - 1);
      } else if (selectedSuggestionIndex === 0) {
        setSelectedSuggestionIndex(-1);
      }
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (selectedSuggestionIndex >= 0 && filteredSuggestions[selectedSuggestionIndex]) {
        addTable(filteredSuggestions[selectedSuggestionIndex]);
      } else {
        const trimmedInput = inputValue.trim();
        if (trimmedInput) {
          addTable(trimmedInput);
        }
      }
    } else if (event.key === 'Escape') {
      setShowSuggestions(false);
      setSelectedSuggestionIndex(-1);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    addTable(suggestion);
  };

  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Tables to add or update
      </label>
      {selectedTables.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200 max-h-48 overflow-y-auto">
          {selectedTables.map((table) => (
            <span
              key={table}
              className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 px-2.5 py-0.5 rounded-md text-xs font-medium"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 12 12"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M10.6667 8V6.66667H1.33333V8H10.6667ZM10.6667 5.33333V4H1.33333V5.33333H10.6667ZM10.6667 2.66667V1.33333H1.33333V2.66667H10.6667ZM1.33333 12C0.966667 12 0.652778 11.8694 0.391667 11.6083C0.130556 11.3472 0 11.0333 0 10.6667V1.33333C0 0.966667 0.130556 0.652778 0.391667 0.391667C0.652778 0.130556 0.966667 0 1.33333 0H10.6667C11.0333 0 11.3472 0.130556 11.6083 0.391667C11.8694 0.652778 12 0.966667 12 1.33333V10.6667C12 11.0333 11.8694 11.3472 11.6083 11.6083C11.3472 11.8894 11.0333 12 10.6667 12H1.33333ZM10.6667 10.6667V9.33333H1.33333V10.6667H10.6667Z"
                  fill="#1E40AF"
                />
              </svg>
              <span>{table}</span>
              <button
                type="button"
                onClick={() => onRemoveTable(table)}
                disabled={disabled}
                className="ml-1 hover:text-blue-900 focus:outline-none disabled:opacity-50"
                aria-label={`Remove ${table}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleInputKeyDown}
          onFocus={() => setShowSuggestions(availableTables.length > 0)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          placeholder="Type table name and press Enter (e.g., mydb.schema.table1)"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={disabled}
          autoFocus
        />
        {showSuggestions && !loadingTables && (
          <TableDropdown
            suggestions={filteredSuggestions}
            selectedIndex={selectedSuggestionIndex}
            position={dropdownPosition}
            onSelect={handleSuggestionClick}
            onHoverIndex={setSelectedSuggestionIndex}
          />
        )}
        {loadingTables && (
          <div className="absolute right-3 top-2">
            <div
              className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"
              title="Loading tables from warehouse..."
            ></div>
          </div>
        )}
      </div>
      <p className="mt-2 text-xs text-gray-500">
        {loadingTables
          ? 'Loading tables from warehouse... You can still type table names manually.'
          : availableTables.length > 0
            ? `${availableTables.length} tables available. Type to search and press Enter or click to add.`
            : 'Type fully-qualified table names and press Enter to add them.'}
      </p>
    </div>
  );
}
