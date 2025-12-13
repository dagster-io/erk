import type {FieldSchema} from '../../types/warehouse-schema';

interface SelectFieldProps {
  field: FieldSchema;
  value: string;
  onChange: (value: string) => void;
  required: boolean;
}

export default function SelectField({field, value, onChange, required}: SelectFieldProps) {
  if (!field.options || field.options.length === 0) {
    return null;
  }

  return (
    <select
      id={field.name}
      name={field.name}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      required={required}
      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#3C39EE] focus:border-[#3C39EE]"
    >
      <option value="">Choose an option...</option>
      {field.options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}
