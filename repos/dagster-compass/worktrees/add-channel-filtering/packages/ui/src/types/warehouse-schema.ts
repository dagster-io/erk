// TypeScript types for warehouse-schemas.json
// This file provides type safety when consuming the generated JSON schema

export interface FieldConditional {
  field: string; // The field name to check
  value: string | string[]; // Value(s) that make this field visible
}

export interface FieldGroup {
  label: string;
  fields: string[]; // Field names in this group
}

export interface FieldSchema {
  name: string;
  type: 'string' | 'integer' | 'boolean' | 'union';
  required: boolean;
  title?: string;
  description?: string;
  examples?: string[];
  widget?: 'password' | 'textarea' | 'radio' | 'select'; // Widget type for rendering
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  default?: any;
  options?: string[]; // For radio/select fields
  conditional?: FieldConditional; // For conditional visibility
  validator?: 'bigquery_json' | 'snowflake_private_key'; // Named validators
  rows?: number; // For textarea fields
  placeholder?: string;
}

export interface NetworkInfo {
  connection_method: string;
  port?: string;
  ip_addresses?: string[];
  additional_info?: string;
}

export interface PermissionInfo {
  header: string;
  permissions: string[];
}

export interface HelpInfo {
  setup_instructions?: string[];
  network_info?: NetworkInfo;
  connection_permissions?: PermissionInfo;
  schema_permissions?: PermissionInfo;
}

export interface WarehouseSchema {
  type: string;
  groups?: FieldGroup[]; // Optional field grouping
  fields: Record<string, FieldSchema>;
  help_info: HelpInfo;
}

export interface WarehouseSchemas {
  version: string;
  generated_from: string;
  warehouses: Record<string, WarehouseSchema>;
}

// Validation result types
export interface ValidationResult {
  isValid: boolean;
  message: string;
  level?: 'success' | 'warning' | 'error';
}

export interface PrivateKeyValidation extends ValidationResult {
  isEncrypted: boolean;
}
