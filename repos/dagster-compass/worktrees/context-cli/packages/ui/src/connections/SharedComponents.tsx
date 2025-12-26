/**
 * Shared components used across the connections wizard
 */

/**
 * Channel name input component with # prefix
 * Used in channel selection flows
 */
export function ChannelNameInput({
  value,
  onChange,
  placeholder = 'prospector-data',
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-lg text-gray-600">#</span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        autoFocus
      />
    </div>
  );
}
