import {useState, useEffect, useCallback} from 'react';
import type {WarehouseType, CredentialsMap} from '../Connections';
import warehouseSchemas from '../warehouse-schemas.json';
import type {
  WarehouseSchema,
  FieldSchema,
  ValidationResult,
  PrivateKeyValidation,
} from '../types/warehouse-schema';
import RadioField from './fields/RadioField';
import SelectField from './fields/SelectField';
import {validateBigQueryJson, validateSnowflakePrivateKey} from './validator';

interface DynamicWarehouseFormProps {
  warehouseType: WarehouseType;
  credentials: Partial<CredentialsMap[WarehouseType]>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onChange: (creds: any) => void;
  onValidChange: (valid: boolean) => void;
}

export default function DynamicWarehouseForm({
  warehouseType,
  credentials,
  onChange,
  onValidChange,
}: DynamicWarehouseFormProps) {
  const schema = warehouseSchemas.warehouses[warehouseType] as WarehouseSchema;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [formData, setFormData] = useState<Record<string, any>>(() => {
    // Initialize form data with defaults from schema
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const initialData: Record<string, any> = {};
    Object.entries(schema.fields).forEach(([fieldName, field]) => {
      if (field.default !== undefined) {
        initialData[fieldName] = field.default;
      } else {
        initialData[fieldName] = '';
      }
    });
    return {...initialData, ...credentials};
  });

  // Helper to check if field should be visible based on conditional
  const isFieldVisible = useCallback(
    (field: FieldSchema): boolean => {
      if (!field.conditional) {
        return true;
      }

      const {field: dependentField, value: requiredValue} = field.conditional;
      const dependentFieldValue = formData[dependentField];

      if (Array.isArray(requiredValue)) {
        return requiredValue.includes(dependentFieldValue);
      }
      return dependentFieldValue === requiredValue;
    },
    [formData],
  );

  useEffect(() => {
    // Validate form on data change - only check visible required fields
    const isValid = Object.entries(schema.fields).every(([fieldName, field]) => {
      // Skip hidden fields
      if (!isFieldVisible(field)) {
        return true;
      }
      // Skip optional fields
      if (!field.required) {
        return true;
      }
      // Check if field has value
      const value = formData[fieldName];
      return value !== null && value !== undefined && String(value).trim() !== '';
    });
    onValidChange(isValid);
  }, [formData, schema.fields, onValidChange, isFieldVisible]);

  const handleChange = (fieldName: string, value: string) => {
    const newData = {...formData, [fieldName]: value};
    setFormData(newData);
    onChange(newData);
  };

  const renderField = (fieldName: string, field: FieldSchema) => {
    if (!field) {
      return null;
    }

    // Check if field should be visible
    if (!isFieldVisible(field)) {
      return null;
    }

    const value = formData[fieldName] ?? '';

    // Apply field-specific validators
    let validation: ValidationResult | PrivateKeyValidation | null = null;
    if (field.validator === 'bigquery_json') {
      validation = validateBigQueryJson(value);
    } else if (field.validator === 'snowflake_private_key') {
      validation = validateSnowflakePrivateKey(value);
    }

    // Determine if this field is required (considering conditional visibility)
    const isRequired = field.required && isFieldVisible(field);

    // Determine widget type for rendering
    const widget = field.widget;
    const placeholder = field.placeholder || field.examples?.[0] || '';

    return (
      <div key={fieldName}>
        <label htmlFor={fieldName} className="block text-sm font-medium text-gray-700 mb-2">
          {field.title || fieldName} {isRequired && <span className="text-red-500">*</span>}
        </label>

        {/* Radio buttons */}
        {widget === 'radio' && (
          <RadioField
            field={field}
            value={value}
            onChange={(v) => handleChange(fieldName, v)}
            required={isRequired}
          />
        )}

        {/* Select dropdown */}
        {widget === 'select' && (
          <SelectField
            field={field}
            value={value}
            onChange={(v) => handleChange(fieldName, v)}
            required={isRequired}
          />
        )}

        {/* Textarea */}
        {widget === 'textarea' && (
          <textarea
            id={fieldName}
            name={fieldName}
            value={value}
            onChange={(e) => handleChange(fieldName, e.target.value)}
            placeholder={placeholder}
            rows={field.rows || 6}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#3C39EE] focus:border-[#3C39EE] font-mono text-sm"
            required={isRequired}
          />
        )}

        {/* Password field */}
        {widget === 'password' && (
          <input
            type="password"
            id={fieldName}
            name={fieldName}
            value={value}
            onChange={(e) => handleChange(fieldName, e.target.value)}
            placeholder={placeholder}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#3C39EE] focus:border-[#3C39EE]"
            required={isRequired}
          />
        )}

        {/* Text/Number input (default) */}
        {!widget && (
          <input
            type={field.type === 'integer' ? 'number' : 'text'}
            id={fieldName}
            name={fieldName}
            value={value}
            onChange={(e) => handleChange(fieldName, e.target.value)}
            placeholder={placeholder}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#3C39EE] focus:border-[#3C39EE]"
            required={isRequired}
          />
        )}

        {/* Field description */}
        {field.description && !validation?.message && (
          <p className="mt-2 text-sm text-gray-500">{field.description}</p>
        )}

        {/* Validation feedback */}
        {validation?.message && (
          <p
            className={`mt-2 text-sm ${
              validation.level === 'success'
                ? 'text-green-600'
                : validation.level === 'error'
                  ? 'text-red-600'
                  : 'text-yellow-600'
            }`}
          >
            {validation.message}
          </p>
        )}
      </div>
    );
  };

  // Render with groups if schema has groups defined
  if (schema.groups && schema.groups.length > 0) {
    return (
      <div className="space-y-8">
        {schema.groups.map((group, index) => (
          <div key={index} className="space-y-6">
            <h3 className="text-lg font-medium text-gray-900">{group.label}</h3>
            {group.fields.map((fieldName) => {
              const field = schema.fields[fieldName];
              if (!field) {
                return null;
              }
              return renderField(fieldName, field);
            })}
          </div>
        ))}
      </div>
    );
  }

  // Fallback to flat rendering without groups
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">Connection Details</h3>
      {Object.keys(schema.fields).map((fieldName) => {
        const field = schema.fields[fieldName];
        if (!field) {
          return null;
        }
        return renderField(fieldName, field);
      })}
    </div>
  );
}
