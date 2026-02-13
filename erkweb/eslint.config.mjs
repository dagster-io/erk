import prettierConfig from 'eslint-config-prettier';
import importPlugin from 'eslint-plugin-import';
import prettierPlugin from 'eslint-plugin-prettier';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import unusedImportsPlugin from 'eslint-plugin-unused-imports';
import tseslint from 'typescript-eslint';

export default [
  {ignores: ['dist/**']},

  // TypeScript recommended
  ...tseslint.configs.recommended,

  // React recommended + JSX runtime (React 17+)
  reactPlugin.configs.flat.recommended,
  reactPlugin.configs.flat['jsx-runtime'],

  // Main rules
  {
    plugins: {
      '@typescript-eslint': tseslint.plugin,
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
      import: importPlugin,
      'unused-imports': unusedImportsPlugin,
    },

    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: 2018,
        sourceType: 'module',
        ecmaFeatures: {jsx: true},
      },
    },

    settings: {
      react: {version: 'detect'},
    },

    rules: {
      // General
      curly: 'error',
      eqeqeq: ['error', 'always', {null: 'ignore'}],
      'object-shorthand': ['error', 'always'],

      // Imports
      'import/no-cycle': ['error', {ignoreExternal: true}],
      'import/no-default-export': 'off',
      'import/no-duplicates': 'error',
      'import/order': [
        'error',
        {
          groups: ['builtin', 'external', 'internal', ['sibling', 'parent'], 'index', 'unknown'],
          alphabetize: {order: 'asc', caseInsensitive: false},
          'newlines-between': 'always',
        },
      ],
      'sort-imports': [
        'error',
        {
          ignoreCase: false,
          ignoreDeclarationSort: true,
          ignoreMemberSort: false,
          allowSeparatedGroups: true,
        },
      ],

      // Unused imports
      'no-unused-vars': 'off',
      'unused-imports/no-unused-imports': 'error',
      'unused-imports/no-unused-vars': [
        'error',
        {vars: 'all', varsIgnorePattern: '^_', args: 'after-used', argsIgnorePattern: '^_'},
      ],

      // React
      'react/jsx-curly-brace-presence': 'error',
      'react/jsx-no-target-blank': 'error',
      'react/jsx-uses-react': 'off',
      'react/prefer-stateless-function': 'error',
      'react/prop-types': 'off',
      'react/display-name': 'off',
      'react/react-in-jsx-scope': 'off',

      // React Hooks
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',

      // TypeScript
      '@typescript-eslint/no-unused-vars': 'off',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-empty-function': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/no-empty-object-type': [
        'error',
        {allowInterfaces: 'with-single-extends'},
      ],
    },
  },

  // Prettier must be last
  prettierConfig,
  {
    plugins: {prettier: prettierPlugin},
    rules: {
      'prettier/prettier': 'error',
      // Re-enable curly after eslint-config-prettier disables it
      curly: 'error',
    },
  },
];
