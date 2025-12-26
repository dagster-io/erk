import type {ValidationResult, PrivateKeyValidation} from '../types/warehouse-schema';

export function validateBigQueryJson(value: string): ValidationResult {
  if (!value.trim()) {
    return {
      isValid: false,
      message: 'Paste your Google Cloud service account JSON key',
      level: undefined,
    };
  }

  try {
    const parsed = JSON.parse(value);
    if (parsed.type === 'service_account' && parsed.project_id && parsed.client_email) {
      return {
        isValid: true,
        message: '✓ Valid service account JSON',
        level: 'success',
      };
    } else {
      return {
        isValid: false,
        message: '⚠ JSON is valid but may not be a service account key',
        level: 'warning',
      };
    }
  } catch {
    return {
      isValid: false,
      message: '✗ Invalid JSON format',
      level: 'error',
    };
  }
}

export function validateSnowflakePrivateKey(content: string): PrivateKeyValidation {
  if (!content.trim()) {
    return {isValid: false, isEncrypted: false, message: ''};
  }

  const upper = content.trim().toUpperCase();

  const formats = [
    {header: 'BEGIN PRIVATE KEY', footer: 'END PRIVATE KEY', encrypted: false},
    {
      header: 'BEGIN ENCRYPTED PRIVATE KEY',
      footer: 'END ENCRYPTED PRIVATE KEY',
      encrypted: true,
    },
  ];

  for (const format of formats) {
    if (
      upper.includes(`-----${format.header}-----`) &&
      upper.includes(`-----${format.footer}-----`)
    ) {
      return {
        isValid: true,
        isEncrypted: format.encrypted,
        message: `✓ Valid ${format.encrypted ? 'encrypted ' : ''}private key`,
        level: 'success',
      };
    }
  }

  return {
    isValid: false,
    isEncrypted: false,
    message: '✗ Invalid private key format',
    level: 'error',
  };
}
