import type {FieldSchema} from '../../types/warehouse-schema';

interface RadioFieldProps {
  field: FieldSchema;
  value: string;
  onChange: (value: string) => void;
  required: boolean;
}

export default function RadioField({field, value, onChange, required}: RadioFieldProps) {
  if (!field.options || field.options.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {field.options.map((option) => (
        <label key={option} className="flex items-center">
          <input
            type="radio"
            name={field.name}
            value={option}
            checked={value === option}
            onChange={(e) => onChange(e.target.value)}
            required={required}
            className="h-4 w-4 text-[#3C39EE] focus:ring-[#3C39EE] border-gray-300"
          />
          <span className="ml-2 text-sm text-gray-700">{option}</span>
        </label>
      ))}
    </div>
  );
}
