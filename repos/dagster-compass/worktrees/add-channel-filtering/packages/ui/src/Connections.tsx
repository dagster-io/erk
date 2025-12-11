import {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  useCallback,
  ReactNode,
} from 'react';
import {useSearchParams, useLocation, useNavigate} from 'react-router-dom';
import DynamicWarehouseForm from './connections/DynamicWarehouseForm';
import Stepper from './connections/Stepper';
import SetupRequirements from './connections/SetupRequirements';
import WizardLayout from './connections/WizardLayout';
import WizardHeader from './connections/WizardHeader';
import {ChannelNameInput} from './connections/SharedComponents';
import {PageHeader} from './components/PageHeader';
import {HelpFooter} from './components/HelpFooter';
import {TruncatedName} from './components/TruncatedName';
import warehouseSchemas from './warehouse-schemas.json';
import type {WarehouseSchema} from './types/warehouse-schema';
import {OnboardingComplete} from './components/OnboardingComplete';

// Types
export type WarehouseType =
  | 'snowflake'
  | 'bigquery'
  | 'athena'
  | 'redshift'
  | 'postgres'
  | 'motherduck'
  | 'databricks';

// Setup requirements data for each warehouse type (loaded from JSON schema)
function getSetupRequirements(warehouseType: WarehouseType) {
  const schema = warehouseSchemas.warehouses[warehouseType] as WarehouseSchema;
  const helpInfo = schema.help_info;

  // Transform network_info from snake_case (JSON) to camelCase (React component)
  const networkInfo = helpInfo.network_info
    ? {
        connectionMethod: helpInfo.network_info.connection_method,
        port: helpInfo.network_info.port,
        ipAddresses: helpInfo.network_info.ip_addresses,
        additionalInfo: helpInfo.network_info.additional_info,
      }
    : undefined;

  return {
    setupInstructions: helpInfo.setup_instructions,
    connectionPermissions: helpInfo.connection_permissions,
    networkInfo,
  };
}

// Schema discovery permissions for each warehouse type (loaded from JSON schema)
function getSchemaPermissions(warehouseType: WarehouseType) {
  const schema = warehouseSchemas.warehouses[warehouseType] as WarehouseSchema;
  return schema.help_info.schema_permissions;
}

export type WizardStep =
  | 'warehouse-selection'
  | 'credentials'
  | 'schema-discovery'
  | 'table-selection'
  | 'channel-assignment'
  | 'prospector-channels'
  | 'success';

export interface CredentialsMap {
  snowflake: {
    account_id: string;
    username: string;
    password: string;
    warehouse: string;
    role: string;
    region: string;
  };
  bigquery: {
    location: string;
    service_account_json_string: string;
  };
  athena: {
    region: string;
    s3_staging_dir: string;
    aws_access_key_id: string;
    aws_secret_access_key: string;
    query_engine: string;
  };
  redshift: {
    host: string;
    port: string;
    database: string;
    username: string;
    password: string;
  };
  postgres: {
    host: string;
    port: string;
    database: string;
    username: string;
    password: string;
  };
  motherduck: {
    database_name: string;
    access_token: string;
  };
  databricks: {
    server_hostname: string;
    http_path: string;
    credential_type: string;
    personal_access_token: string;
    client_id: string;
    client_secret: string;
  };
}

export interface TableInfo {
  name: string;
  description: string;
  recommended?: boolean;
}

export interface ChannelInfo {
  id: string;
  name: string;
}

interface WizardState {
  currentStep: WizardStep;
  warehouseType: WarehouseType | null;
  credentials: Partial<CredentialsMap[WarehouseType]>;
  connectionToken: string | null;
  connectionName: string | null;
  schemas: string[];
  selectedSchemas: string[];
  tables: TableInfo[];
  selectedTables: TableInfo[];
  channels: ChannelInfo[];
  selectedChannelId: string | null;
  error: string | null;
  isLoading: boolean;
}

interface WizardContextType {
  state: WizardState;
  setWarehouseType: (type: WarehouseType) => void;
  setCredentials: (credentials: Partial<CredentialsMap[WarehouseType]>) => void;
  setConnectionToken: (token: string) => void;
  setConnectionName: (name: string) => void;
  setSchemas: (schemas: string[]) => void;
  setSelectedSchemas: (schemas: string[]) => void;
  setTables: (tables: TableInfo[]) => void;
  setSelectedTables: (tables: TableInfo[]) => void;
  setChannels: (channels: ChannelInfo[]) => void;
  setSelectedChannelId: (channelId: string) => void;
  setError: (error: string | null) => void;
  setLoading: (loading: boolean) => void;
  goToStep: (step: WizardStep) => void;
  reset: () => void;
}

const WizardContext = createContext<WizardContextType | null>(null);

// eslint-disable-next-line react-refresh/only-export-components
export function useWizard() {
  const context = useContext(WizardContext);
  if (!context) {
    throw new Error('useWizard must be used within WizardProvider');
  }
  return context;
}

const initialState: WizardState = {
  currentStep: 'warehouse-selection',
  warehouseType: null,
  credentials: {},
  connectionToken: null,
  connectionName: null,
  schemas: [],
  selectedSchemas: [],
  tables: [],
  selectedTables: [],
  channels: [],
  selectedChannelId: null,
  error: null,
  isLoading: false,
};

const SESSIONSTORAGE_KEY = 'compass_wizard_state';

// Helper functions for sessionStorage
function saveStateToStorage(state: WizardState) {
  try {
    sessionStorage.setItem(SESSIONSTORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error('Failed to save wizard state to sessionStorage:', error);
  }
}

function loadStateFromStorage(): WizardState | null {
  try {
    const stored = sessionStorage.getItem(SESSIONSTORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Failed to load wizard state from sessionStorage:', error);
  }
  return null;
}

function clearStoredState() {
  try {
    sessionStorage.removeItem(SESSIONSTORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear wizard state from sessionStorage:', error);
  }
}

export function WizardProvider({children}: {children: ReactNode}) {
  // Initialize state from sessionStorage if available
  const [state, setState] = useState<WizardState>(() => {
    const stored = loadStateFromStorage();
    return stored || initialState;
  });

  // Persist state to sessionStorage whenever it changes
  useEffect(() => {
    saveStateToStorage(state);
  }, [state]);

  // Memoize setter functions to prevent unnecessary re-renders
  const setWarehouseType = useCallback((type: WarehouseType) => {
    setState((prev) => ({
      ...prev,
      warehouseType: type,
      credentials: {},
      error: null,
    }));
  }, []);

  const setCredentials = useCallback((credentials: Partial<CredentialsMap[WarehouseType]>) => {
    setState((prev) => ({
      ...prev,
      credentials,
      error: null,
    }));
  }, []);

  const setConnectionToken = useCallback((token: string) => {
    setState((prev) => ({
      ...prev,
      connectionToken: token,
      error: null,
    }));
  }, []);

  const setConnectionName = useCallback((name: string) => {
    setState((prev) => ({
      ...prev,
      connectionName: name,
      error: null,
    }));
  }, []);

  const setSchemas = useCallback((schemas: string[]) => {
    setState((prev) => ({
      ...prev,
      schemas,
      error: null,
    }));
  }, []);

  const setSelectedSchemas = useCallback((schemas: string[]) => {
    setState((prev) => ({
      ...prev,
      selectedSchemas: schemas,
      error: null,
    }));
  }, []);

  const setTables = useCallback((tables: TableInfo[]) => {
    setState((prev) => ({
      ...prev,
      tables,
      error: null,
    }));
  }, []);

  const setSelectedTables = useCallback((tables: TableInfo[]) => {
    setState((prev) => ({
      ...prev,
      selectedTables: tables,
      error: null,
    }));
  }, []);

  const setChannels = useCallback((channels: ChannelInfo[]) => {
    setState((prev) => ({
      ...prev,
      channels,
      error: null,
    }));
  }, []);

  const setSelectedChannelId = useCallback((channelId: string) => {
    setState((prev) => ({
      ...prev,
      selectedChannelId: channelId,
      error: null,
    }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState((prev) => ({...prev, error, isLoading: false}));
  }, []);

  const setLoading = useCallback((isLoading: boolean) => {
    setState((prev) => ({...prev, isLoading}));
  }, []);

  const goToStep = useCallback((step: WizardStep) => {
    setState((prev) => ({...prev, currentStep: step}));
  }, []);

  const reset = useCallback(() => {
    clearStoredState();
    setState(initialState);
  }, []);

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo<WizardContextType>(
    () => ({
      state,
      setWarehouseType,
      setCredentials,
      setConnectionToken,
      setConnectionName,
      setSchemas,
      setSelectedSchemas,
      setTables,
      setSelectedTables,
      setChannels,
      setSelectedChannelId,
      setError,
      setLoading,
      goToStep,
      reset,
    }),
    [
      state,
      setWarehouseType,
      setCredentials,
      setConnectionToken,
      setConnectionName,
      setSchemas,
      setSelectedSchemas,
      setTables,
      setSelectedTables,
      setChannels,
      setSelectedChannelId,
      setError,
      setLoading,
      goToStep,
      reset,
    ],
  );

  return <WizardContext.Provider value={contextValue}>{children}</WizardContext.Provider>;
}

// Main wizard component that renders the appropriate step
export default function ConnectionsWizard() {
  const [searchParams] = useSearchParams();
  const source = searchParams.get('source') as WarehouseType | null;

  return (
    <WizardProvider>
      <WizardRouter source={source} />
    </WizardProvider>
  );
}

function WizardRouter({source}: {source: WarehouseType | null}) {
  const {state, setWarehouseType, goToStep} = useWizard();
  const location = useLocation();
  const isAddConnectionFlow = location.pathname === '/connections/add-connection';

  // Handle direct link via source parameter (e.g., ?source=snowflake)
  // This allows tests and deep links to skip warehouse selection
  useEffect(() => {
    if (source && !state.warehouseType && state.currentStep === 'warehouse-selection') {
      setWarehouseType(source);
      goToStep('credentials');
    }
  }, [source, state.warehouseType, state.currentStep, setWarehouseType, goToStep]);

  // If source is provided in URL, it's a direct link to a specific warehouse
  // Otherwise, show warehouse selection
  if (!source && state.currentStep === 'warehouse-selection') {
    return <WarehouseSelection isAddConnectionFlow={isAddConnectionFlow} />;
  }

  // Prospector flow doesn't require warehouse type
  if (state.currentStep === 'prospector-channels') {
    return <ProspectorChannelSelection />;
  }

  if (!state.warehouseType) {
    return <WarehouseSelection isAddConnectionFlow={isAddConnectionFlow} />;
  }

  switch (state.currentStep) {
    case 'warehouse-selection':
      return <WarehouseSelection isAddConnectionFlow={isAddConnectionFlow} />;
    case 'credentials':
      return <CredentialsForm />;
    case 'schema-discovery':
      return <SchemaDiscovery />;
    case 'table-selection':
      return <TableSelection />;
    case 'channel-assignment':
      return <ChannelAssignment />;
    case 'success':
      return <ConnectionSuccess />;
    default:
      return <WarehouseSelection isAddConnectionFlow={isAddConnectionFlow} />;
  }
}

// Warehouse Selection - Homepage with data source cards
function WarehouseSelection({isAddConnectionFlow}: {isAddConnectionFlow: boolean}) {
  const {setWarehouseType, goToStep} = useWizard();
  const [activeTab, setActiveTab] = useState<'warehouse' | 'prospector'>('warehouse');
  const [isVideoExpanded, setIsVideoExpanded] = useState(false);

  const warehouses: Array<{type: WarehouseType; name: string; icon: string}> = [
    {type: 'snowflake', name: 'Snowflake', icon: '/static/snowflake.svg'},
    {type: 'bigquery', name: 'BigQuery', icon: '/static/bigquery.svg'},
    {type: 'athena', name: 'AWS Athena', icon: '/static/Athena.svg'},
    {type: 'redshift', name: 'AWS Redshift', icon: '/static/redshift.svg'},
    {type: 'postgres', name: 'PostgreSQL', icon: '/static/postgresql.svg'},
    {type: 'motherduck', name: 'MotherDuck', icon: '/static/motherduck.svg'},
    {type: 'databricks', name: 'Databricks', icon: '/static/databricks.svg'},
  ];

  const handleWarehouseSelect = (type: WarehouseType) => {
    setWarehouseType(type);
    goToStep('credentials');
  };

  const handleProspectorSelect = () => {
    // Navigate to prospector channel selection step
    goToStep('prospector-channels');
  };

  return (
    <div className="flex flex-col items-center py-8 px-4 sm:px-6 lg:px-8">
      <div className="mt-16 w-full max-w-4xl flex flex-col items-center">
        <PageHeader
          logo={<img src="/static/compass-logo.svg" alt="Compass" className="h-7" />}
          title="Choose Your Data Source"
          subtitle="Connect to your data warehouse to get started with Compass"
          size="large"
        />

        {/* Collapsible video card */}
        <div className="w-full max-w-4xl mx-auto mb-8">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <button
              onClick={() => setIsVideoExpanded(!isVideoExpanded)}
              className="w-full flex items-center justify-center p-4 hover:bg-gray-50 transition-colors relative"
            >
              <span className="text-base font-medium text-gray-900 text-center">
                🎬 Watch a video to get started
              </span>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform absolute right-4 ${isVideoExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            {isVideoExpanded && (
              <div className="px-4 pb-4">
                <div style={{position: 'relative', paddingBottom: '64.74820143884892%', height: 0}}>
                  <iframe
                    src="https://www.loom.com/embed/b354c4475e5d4714b9351b2a1230b785"
                    frameBorder="0"
                    allowFullScreen
                    style={{position: 'absolute', top: 0, left: 0, width: '100%', height: '100%'}}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Split Button Tabs - only show in add-connection flow */}
        {isAddConnectionFlow && (
          <div className="w-full max-w-4xl mb-8">
            <div className="inline-flex rounded-lg border border-gray-300 bg-gray-50 p-1 w-full">
              <button
                onClick={() => setActiveTab('warehouse')}
                className={`flex-1 px-6 py-3 text-sm font-semibold rounded-md transition-all ${
                  activeTab === 'warehouse'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Your Warehouse
              </button>
              <button
                onClick={() => setActiveTab('prospector')}
                className={`flex-1 px-6 py-3 text-sm font-semibold rounded-md transition-all ${
                  activeTab === 'prospector'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Curated Data
              </button>
            </div>
          </div>
        )}

        {/* White card wrapper around grid */}
        <div className="w-full max-w-4xl mx-auto bg-white rounded-2xl border border-gray-200 shadow-xl p-8 sm:p-6 transition-all duration-300 hover:shadow-2xl">
          {isAddConnectionFlow && activeTab === 'prospector' ? (
            <>
              {/* Curated Data - Prospector Tile (Full Width) */}
              <div className="mb-6">
                <button
                  onClick={handleProspectorSelect}
                  className="group w-full bg-white border-2 border-gray-200 rounded-xl p-8 hover:border-[#3C39EE] hover:shadow-lg transition-all duration-200 cursor-pointer text-left"
                >
                  <div className="flex items-start">
                    <div className="w-16 h-16 mr-4 flex items-center justify-center bg-[#468AFC]/10 rounded-lg group-hover:bg-[#3C39EE]/10 flex-shrink-0">
                      <img
                        src="/static/compass-logo-mark.svg"
                        alt="Prospecting Data"
                        className="h-10 w-10"
                      />
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-gray-950 mb-1">Prospecting Data</h3>
                      <p className="text-sm text-gray-600">
                        Ready-to-use datasets for sales, recruiting, or investing.
                      </p>
                    </div>
                  </div>
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Warehouse Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {warehouses.map((warehouse) => (
                  <button
                    key={warehouse.type}
                    onClick={() => handleWarehouseSelect(warehouse.type)}
                    className="group bg-white border-2 border-gray-200 rounded-xl p-8 hover:border-[#3C39EE] hover:shadow-lg transition-all duration-200 cursor-pointer text-left"
                  >
                    <div className="flex items-center">
                      <div className="w-16 h-16 mr-4 flex items-center justify-center bg-[#468AFC]/10 rounded-lg group-hover:bg-[#3C39EE]/10">
                        <img src={warehouse.icon} alt={warehouse.name} className="h-12 w-12" />
                      </div>
                      <h3 className="text-xl font-semibold text-gray-950">{warehouse.name}</h3>
                    </div>
                  </button>
                ))}

                {/* CSV Upload - Coming Soon */}
                <div className="bg-white border-2 border-gray-100 rounded-xl p-8 opacity-80 cursor-not-allowed">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="w-16 h-16 mr-4 flex items-center justify-center bg-gray-50 rounded-lg">
                        <i className="fas fa-file-csv text-4xl text-gray-400"></i>
                      </div>
                      <h3 className="text-xl font-semibold text-gray-500">CSV Upload</h3>
                    </div>
                    <span className="px-3 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded-full">
                      Coming Soon
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
        {/* End white card wrapper */}

        {/* Footer Help Text */}
        <HelpFooter />
      </div>
    </div>
  );
}

// Prospector Channel Selection - Separate step for selecting channels for prospector data
function ProspectorChannelSelection() {
  const {goToStep} = useWizard();
  const [isLoading, setIsLoading] = useState(true);
  const [channels, setChannels] = useState<ChannelInfo[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<Set<string>>(new Set());
  const [newChannelName, setNewChannelName] = useState('');
  const [channelOption, setChannelOption] = useState<'create' | 'existing' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [canCreateChannel, setCanCreateChannel] = useState(true);
  const [planLimitMessage, setPlanLimitMessage] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    const loadChannels = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('/api/onboarding/connections/fetch-channels');
        const result = await response.json();

        if (cancelled) return;

        if (result.can_create_channel !== undefined) {
          setCanCreateChannel(result.can_create_channel);
        }
        if (result.plan_limit_message) {
          setPlanLimitMessage(result.plan_limit_message);
        }

        if (result.success && result.channels) {
          setChannels(result.channels);
        } else {
          setError(result.error || 'Failed to load channels');
        }
      } catch {
        if (!cancelled) {
          setError('Failed to load Slack channels');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadChannels();

    return () => {
      cancelled = true;
    };
  }, []);

  const toggleChannel = (channelId: string) => {
    const newSelected = new Set(selectedChannels);
    if (newSelected.has(channelId)) {
      newSelected.delete(channelId);
    } else {
      newSelected.add(channelId);
    }
    setSelectedChannels(newSelected);
  };

  const isValid = () => {
    if (channelOption === 'create') {
      return newChannelName.trim().length > 0;
    } else if (channelOption === 'existing') {
      return selectedChannels.size > 0;
    }
    return false;
  };

  const handleSubmit = async () => {
    if (!isValid()) {
      return;
    }

    if (channelOption === 'create') {
      const channelName = newChannelName.trim();
      const channelNameRegex = /^[a-z0-9-_]+$/;
      if (!channelNameRegex.test(channelName)) {
        setError(
          'Channel name can only contain lowercase letters, numbers, hyphens, and underscores.',
        );
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const channelSelection = {
        type: channelOption,
        channels:
          channelOption === 'create'
            ? [newChannelName.trim()]
            : Array.from(selectedChannels).map(
                (id) => channels.find((c) => c.id === id)?.name || '',
              ),
      };

      const response = await fetch('/api/connections/prospector/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          channelSelection: channelSelection,
        }),
      });

      const result = await response.json();

      if (result.success) {
        navigate('/connections?prospector_added=true');
      } else {
        setError(result.error || 'Failed to add prospector connection');
        setIsSubmitting(false);
      }
    } catch (err) {
      setError('Failed to add prospector connection');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col items-center py-8 px-4 sm:px-6 lg:px-8">
      <div className="mt-16 w-full max-w-4xl flex flex-col items-center">
        <PageHeader
          logo={<img src="/static/compass-logo.svg" alt="Compass" className="h-7" />}
          title="Add Prospecting Data"
          subtitle="Select which channel(s) to add prospector data to"
          size="large"
        />

        <div className="w-full max-w-4xl mx-auto bg-white rounded-2xl border border-gray-200 shadow-xl p-8 sm:p-6 transition-all duration-300 hover:shadow-2xl">
          {/* Back button */}
          <div className="mb-4">
            <button
              onClick={() => goToStep('warehouse-selection')}
              className="inline-flex items-center text-sm text-slate-500 hover:text-slate-700"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M15 19l-7-7 7-7"
                />
              </svg>
              Back to Data Sources
            </button>
          </div>

          {/* Header with Icon */}
          <div className="mb-8">
            <div className="flex items-center gap-1 mb-2">
              <div className="w-9 h-9 flex-shrink-0 flex items-center justify-center">
                <img
                  src="/static/compass-logo-mark.svg"
                  alt="Prospecting Data"
                  className="h-8 w-8"
                />
              </div>
              <h1 className="text-xl font-semibold text-slate-900">Add Prospecting Data</h1>
            </div>
            <p className="text-sm text-slate-600">
              Ready-to-use datasets for sales, recruiting, or investing
            </p>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-gray-600">Loading channels...</div>
            </div>
          ) : error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <p className="text-red-800">{error}</p>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900">
                  Select where to add Prospector data:
                </h4>

                <div className="space-y-3">
                  {/* Create new channel option */}
                  {canCreateChannel && (
                    <div
                      onClick={() => setChannelOption('create')}
                      className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                        channelOption === 'create'
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <label className="flex items-start cursor-pointer">
                        <input
                          type="radio"
                          checked={channelOption === 'create'}
                          onChange={() => setChannelOption('create')}
                          className="mt-1 mr-3"
                        />
                        <div className="flex-1">
                          <span className="font-medium text-gray-900">Create new channel</span>
                          {channelOption === 'create' && (
                            <div className="mt-3">
                              <ChannelNameInput
                                value={newChannelName}
                                onChange={setNewChannelName}
                                placeholder="prospector-data"
                              />
                              <p className="text-xs text-gray-500 mt-2">
                                Only lowercase letters, numbers, hyphens, and underscores allowed
                              </p>
                            </div>
                          )}
                        </div>
                      </label>
                    </div>
                  )}

                  {/* Plan limit message */}
                  {!canCreateChannel && planLimitMessage && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                      <p className="text-sm text-amber-800">{planLimitMessage}</p>
                    </div>
                  )}

                  {/* Add to existing channels option */}
                  {channels.length > 0 && (
                    <div
                      onClick={() => setChannelOption('existing')}
                      className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                        channelOption === 'existing'
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <label className="flex items-start cursor-pointer">
                        <input
                          type="radio"
                          checked={channelOption === 'existing'}
                          onChange={() => setChannelOption('existing')}
                          className="mt-1 mr-3"
                        />
                        <div className="flex-1">
                          <span className="font-medium text-gray-900">
                            Add to existing channel{channels.length > 1 ? 's' : ''}
                          </span>
                          {channelOption === 'existing' && (
                            <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
                              {channels.map((channel) => (
                                <label
                                  key={channel.id}
                                  className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedChannels.has(channel.id)}
                                    onChange={() => toggleChannel(channel.id)}
                                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                                  />
                                  <span className="text-sm text-gray-900">#{channel.name}</span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                      </label>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-end pt-4 border-t">
                <button
                  onClick={handleSubmit}
                  disabled={!isValid() || isSubmitting}
                  className="px-6 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Adding...' : 'Add Prospector Data'}
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer Help Text */}
        <HelpFooter />
      </div>
    </div>
  );
}

// Credentials Form - Warehouse-specific connection forms
function CredentialsForm() {
  const {state, setCredentials, goToStep} = useWizard();

  // Local state - only used within this component
  const [localCredentials, setLocalCredentials] = useState<Partial<CredentialsMap[WarehouseType]>>(
    state.credentials,
  );
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [testMessage, setTestMessage] = useState<string>('Not tested yet');
  const [testLogs, setTestLogs] = useState<string[]>([]);
  const [formValid, setFormValid] = useState(false);

  if (!state.warehouseType) {
    return null;
  }

  const handleFormChange = (credentials: Partial<CredentialsMap[WarehouseType]>) => {
    setLocalCredentials(credentials);
    setTestStatus('idle');
    setTestMessage('Not tested yet');
    setTestLogs([]);
  };

  // Helper to format logs with rich styling like Jinja template
  const formatLog = (log: string, index: number, isSuccess: boolean) => {
    const isFirst = index === 0;

    // First log gets special treatment (✅ or ❌ with bold)
    if (isFirst) {
      const emoji = isSuccess ? '✅' : '❌';
      return (
        <div
          key={index}
          className={`text-sm py-1 font-medium ${isSuccess ? 'text-green-600' : 'text-red-600'}`}
        >
          {emoji} {log}
        </div>
      );
    }

    // SQL queries get blue color with arrow
    if (log.startsWith('SQL:')) {
      return (
        <div key={index} className="text-sm py-1 text-blue-600">
          → {log}
        </div>
      );
    }

    // Success messages or lines with Success/✅
    if (log.includes('Success') || log.includes('✅')) {
      return (
        <div key={index} className="text-sm py-1 text-green-600">
          ✅ {log}
        </div>
      );
    }

    // Regular log entries with bullet
    return (
      <div key={index} className="text-sm py-1 text-gray-700">
        • {log}
      </div>
    );
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setTestStatus('testing');
    setTestMessage('Testing connection...');
    setTestLogs([]);

    try {
      const response = await fetch(
        `/api/onboarding/connections/${state.warehouseType}/test-connection`,
        {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(localCredentials),
        },
      );

      const result = await response.json();

      if (result.success) {
        setTestStatus('success');
        setTestMessage('Connection successful');
        if (result.logs) {
          setTestLogs(result.logs);
        }
      } else {
        setTestStatus('error');
        setTestMessage(result.error || 'Connection failed');
        if (result.logs) {
          setTestLogs(result.logs);
        }
      }
    } catch {
      setTestStatus('error');
      setTestMessage('Connection failed: Unable to connect to warehouse');
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (testStatus === 'success') {
      // Propagate local state to global state
      setCredentials(localCredentials);
      goToStep('schema-discovery');
    }
  };

  const getWarehouseDisplayName = () => {
    const names: Record<WarehouseType, string> = {
      snowflake: 'Snowflake',
      bigquery: 'BigQuery',
      athena: 'AWS Athena',
      redshift: 'AWS Redshift',
      postgres: 'PostgreSQL',
      motherduck: 'MotherDuck',
      databricks: 'Databricks',
    };
    return state.warehouseType ? names[state.warehouseType] : '';
  };

  const warehouseIcons: Record<WarehouseType, string> = {
    snowflake: '/static/snowflake.svg',
    bigquery: '/static/bigquery.svg',
    athena: '/static/Athena.svg',
    redshift: '/static/redshift.svg',
    postgres: '/static/postgresql.svg',
    motherduck: '/static/motherduck.svg',
    databricks: '/static/databricks.svg',
  };

  return (
    <div className="min-h-screen bg-gray-50 px-4 sm:px-6 lg:px-8 py-8 pb-12 md:pb-16 lg:pb-24">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
          {/* Stepper Column */}
          <div className="md:col-span-3">
            <Stepper currentStep={1} />
          </div>

          {/* Form Column */}
          <div className="md:col-span-9">
            {/* Back Button */}
            <div className="mb-4">
              <button
                onClick={() => goToStep('warehouse-selection')}
                className="inline-flex items-center text-sm text-slate-500 hover:text-slate-700"
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
                Back to Data Sources
              </button>
            </div>

            {/* Header with Icon */}
            <div className="mb-8">
              <div className="flex items-center gap-1 mb-2">
                <div className="w-9 h-9 flex-shrink-0 flex items-center justify-center">
                  {state.warehouseType && (
                    <img
                      src={warehouseIcons[state.warehouseType]}
                      alt={getWarehouseDisplayName()}
                      className="h-8 w-8"
                    />
                  )}
                </div>
                <h1 className="text-xl font-semibold text-slate-900">
                  Connect to {getWarehouseDisplayName()}
                </h1>
              </div>
              <p className="text-sm text-slate-600">
                Configure your {getWarehouseDisplayName()} data warehouse connection
              </p>
            </div>

            {/* Setup Requirements for all warehouse types */}
            {state.warehouseType && (
              <SetupRequirements {...getSetupRequirements(state.warehouseType)} />
            )}

            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Dynamic warehouse form - renders based on JSON schema */}
              {state.warehouseType && (
                <DynamicWarehouseForm
                  warehouseType={state.warehouseType}
                  credentials={localCredentials}
                  onChange={handleFormChange}
                  onValidChange={setFormValid}
                />
              )}

              {/* Test Connection Section */}
              <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                <div className="flex items-center gap-3 mb-4">
                  <h3 className="text-lg font-medium text-gray-900">Test Connection</h3>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      testStatus === 'success'
                        ? 'bg-green-100 text-green-700'
                        : testStatus === 'error'
                          ? 'bg-red-100 text-red-700'
                          : testStatus === 'testing'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {testMessage}
                  </span>
                </div>

                <div className="bg-white rounded border p-4 max-h-40 overflow-y-auto text-sm mb-4">
                  {testLogs.length === 0 ? (
                    <div className="text-gray-500 text-sm">👉 No tests run yet</div>
                  ) : (
                    <div className="space-y-1">
                      {testLogs.map((log, index) =>
                        formatLog(log, index, testStatus === 'success'),
                      )}
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={!formValid || isTestingConnection}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-[#3C39EE] hover:bg-[#3C39EE]/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#3C39EE] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isTestingConnection && (
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                  )}
                  Test Connection
                </button>
              </div>

              {/* Submit Button */}
              <div className="flex justify-center">
                <button
                  type="submit"
                  disabled={testStatus !== 'success'}
                  className="bg-[#3C39EE] text-white px-8 py-3 rounded-md font-medium hover:bg-[#3C39EE]/90 focus:outline-none focus:ring-2 focus:ring-[#3C39EE] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue to Schema Selection
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function SchemaDiscovery() {
  const {state, setSchemas, setSelectedSchemas, goToStep, setError} = useWizard();
  const [isLoading, setIsLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [discoveryStatus, setDiscoveryStatus] = useState<'loading' | 'success' | 'error'>(
    'loading',
  );
  const [localSchemas, setLocalSchemas] = useState<string[]>(state.schemas || []);
  const [selected, setSelected] = useState<Set<string>>(new Set(state.selectedSchemas || []));
  const [filterText, setFilterText] = useState('');
  const [selectAll, setSelectAll] = useState(false);

  const warehouseIcons: Record<WarehouseType, string> = {
    snowflake: '/static/snowflake.svg',
    bigquery: '/static/bigquery.svg',
    athena: '/static/Athena.svg',
    redshift: '/static/redshift.svg',
    postgres: '/static/postgresql.svg',
    motherduck: '/static/motherduck.svg',
    databricks: '/static/databricks.svg',
  };

  const getWarehouseDisplayName = () => {
    const names: Record<WarehouseType, string> = {
      snowflake: 'Snowflake',
      bigquery: 'BigQuery',
      athena: 'AWS Athena',
      redshift: 'AWS Redshift',
      postgres: 'PostgreSQL',
      motherduck: 'MotherDuck',
      databricks: 'Databricks',
    };
    return state.warehouseType ? names[state.warehouseType] : '';
  };

  useEffect(() => {
    const loadSchemas = async () => {
      setIsLoading(true);
      setDiscoveryStatus('loading');
      setProgress(30);

      setTimeout(() => setProgress(60), 500);
      setTimeout(() => setProgress(85), 1200);

      try {
        const response = await fetch(
          `/api/onboarding/connections/${state.warehouseType}/discover-schemas`,
          {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(state.credentials),
          },
        );

        const result = await response.json();

        if (result.success && result.schemas) {
          setLocalSchemas(result.schemas);
          setDiscoveryStatus('success');
          setProgress(100);
        } else {
          setDiscoveryStatus('error');
          setError(result.error || 'Failed to discover schemas');
        }
      } catch {
        setDiscoveryStatus('error');
        setError('Failed to load schemas');
      } finally {
        setIsLoading(false);
      }
    };

    loadSchemas();
  }, [state.warehouseType, state.credentials, setError]);

  const filteredSchemas = localSchemas.filter((schema) =>
    schema.toLowerCase().includes(filterText.toLowerCase()),
  );

  const handleToggle = (schemaName: string) => {
    const newSelected = new Set(selected);
    if (newSelected.has(schemaName)) {
      newSelected.delete(schemaName);
    } else {
      newSelected.add(schemaName);
    }
    setSelected(newSelected);
    setSelectAll(newSelected.size === filteredSchemas.length && filteredSchemas.length > 0);
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelected(new Set());
      setSelectAll(false);
    } else {
      const allSchemaNames = new Set(filteredSchemas);
      setSelected(allSchemaNames);
      setSelectAll(true);
    }
  };

  const handleClearFilter = () => {
    setFilterText('');
  };

  const handleContinue = () => {
    setSchemas(localSchemas);
    setSelectedSchemas(Array.from(selected));
    goToStep('table-selection');
  };

  return (
    <WizardLayout currentStep={2}>
      <WizardHeader
        onBack={() => goToStep('credentials')}
        backText="Back to Connection Setup"
        icon={state.warehouseType ? warehouseIcons[state.warehouseType] : undefined}
        title={`Select ${getWarehouseDisplayName()} Schemas`}
        subtitle="Choose which schemas/databases to discover tables from"
      />

      {/* Error Banner */}
      {state.error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-red-400 mr-2 flex-shrink-0"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-red-600">{state.error}</p>
          </div>
        </div>
      )}

      {/* Schema Discovery Permissions */}
      {state.warehouseType && (
        <SetupRequirements connectionPermissions={getSchemaPermissions(state.warehouseType)} />
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden mb-8">
        <div className="p-4 bg-gray-50 border-b border-gray-200">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-medium text-gray-900">Available Schemas</h3>
            <div className="flex items-center space-x-4">
              {/* Discovery Status and Progress */}
              <div className="flex items-center space-x-2">
                {isLoading ? (
                  <>
                    <div className="flex items-center justify-center space-x-1">
                      <div className="animate-spin h-4 w-4 border-2 border-[#3C39EE] border-t-transparent rounded-full" />
                      <span className="text-sm font-medium text-gray-600">Discovering schemas</span>
                    </div>
                    <div className="w-32 bg-gray-300 rounded-full h-1 overflow-hidden">
                      <div
                        className="h-1 rounded-full transition-all duration-500 ease-out"
                        style={{
                          width: `${progress}%`,
                          background:
                            'linear-gradient(90deg, #3C39EE 0%, #5B58FF 50%, #3C39EE 100%)',
                          backgroundSize: '200% 100%',
                          animation: 'shimmer 2s infinite',
                        }}
                      />
                    </div>
                    <style>{`
                      @keyframes shimmer {
                        0% { background-position: 200% 0; }
                        100% { background-position: -200% 0; }
                      }
                    `}</style>
                  </>
                ) : discoveryStatus === 'success' ? (
                  <>
                    <div className="flex items-center justify-center space-x-1">
                      <svg
                        className="w-4 h-4 text-green-600"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <span className="text-sm font-medium text-green-600">Complete</span>
                    </div>
                    <div className="w-32 bg-gray-300 rounded-full h-1 overflow-hidden">
                      <div className="bg-green-500 h-1 rounded-full" style={{width: '100%'}} />
                    </div>
                  </>
                ) : null}
              </div>
              {!isLoading && (
                <span className="text-sm text-gray-500">{localSchemas.length} schemas</span>
              )}
            </div>
          </div>

          {/* Filter Input */}
          {!isLoading && (
            <div className="relative mb-4">
              <input
                type="text"
                placeholder="Filter schemas..."
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                className="w-full px-3 py-2 pl-10 pr-8 border border-gray-300 rounded-md focus:ring-[#3C39EE] focus:border-[#3C39EE] text-sm"
              />
              <div className="absolute left-3 top-2.5">
                <svg
                  className="w-4 h-4 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              {filterText && (
                <button
                  onClick={handleClearFilter}
                  className="absolute right-2 top-2 p-1 text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
            </div>
          )}

          {/* Select All */}
          {!isLoading && localSchemas.length > 0 && (
            <div className="flex items-center">
              <input
                type="checkbox"
                id="select-all-schemas"
                checked={selectAll}
                onChange={handleSelectAll}
                className="mr-2 h-4 w-4 text-[#3C39EE] focus:ring-[#3C39EE] border-gray-300 rounded"
              />
              <label htmlFor="select-all-schemas" className="text-sm text-gray-600 cursor-pointer">
                Select All
              </label>
              {selected.size > 0 && (
                <span className="text-sm text-gray-500 ml-3">{selected.size} selected</span>
              )}
            </div>
          )}
        </div>

        <div className="divide-y divide-gray-200 max-h-[40vh] overflow-y-auto min-h-[200px]">
          {isLoading ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin h-8 w-8 border-4 border-[#3C39EE] border-t-transparent rounded-full mb-4" />
              <p className="text-gray-600">Discovering schemas...</p>
            </div>
          ) : filteredSchemas.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              {filterText ? 'No schemas match your filter' : 'No schemas found'}
            </div>
          ) : (
            filteredSchemas.map((schema) => (
              <label
                key={schema}
                className="px-4 py-3 flex items-center space-x-3 hover:bg-gray-50 transition-colors cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.has(schema)}
                  onChange={() => handleToggle(schema)}
                  className="h-4 w-4 text-[#3C39EE] focus:ring-[#3C39EE] border-gray-300 rounded"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900 text-base">
                    <TruncatedName name={schema} maxLength={40} />
                  </div>
                </div>
              </label>
            ))
          )}
        </div>
      </div>

      {/* Continue Button */}
      <div className="flex justify-center">
        <button
          onClick={handleContinue}
          disabled={selected.size === 0}
          className="bg-[#3C39EE] text-white px-6 py-2 rounded-md font-medium hover:bg-[#3C39EE]/90 focus:outline-none focus:ring-2 focus:ring-[#3C39EE] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue to Table Selection
        </button>
      </div>
    </WizardLayout>
  );
}

function TableSelection() {
  const {state, setTables, setSelectedTables, setConnectionToken, goToStep, setError} = useWizard();
  const [isLoading, setIsLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [discoveryStatus, setDiscoveryStatus] = useState<'loading' | 'success' | 'error'>(
    'loading',
  );
  const [localTables, setLocalTables] = useState<TableInfo[]>(state.tables || []);
  const [selected, setSelected] = useState<Set<string>>(
    new Set(state.selectedTables?.map((t) => t.name) || []),
  );
  const [filterText, setFilterText] = useState('');
  const [sortBy, setSortBy] = useState<'recommended' | 'alphabetical'>('recommended');
  const [selectAll, setSelectAll] = useState(false);
  const [tableTestResults, setTableTestResults] = useState<
    Map<string, {success: boolean; error?: string; logs?: string[]}>
  >(new Map());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [logsModalData, setLogsModalData] = useState<{tableName: string; logs: string[]}>({
    tableName: '',
    logs: [],
  });
  const [schemaWarnings, setSchemaWarnings] = useState<Array<{schema: string; error: string}>>([]);

  const TABLE_SELECTION_LIMIT = 25;
  const warehouseIcons: Record<WarehouseType, string> = {
    snowflake: '/static/snowflake.svg',
    bigquery: '/static/bigquery.svg',
    athena: '/static/Athena.svg',
    redshift: '/static/redshift.svg',
    postgres: '/static/postgresql.svg',
    motherduck: '/static/motherduck.svg',
    databricks: '/static/databricks.svg',
  };

  const getWarehouseDisplayName = () => {
    const names: Record<WarehouseType, string> = {
      snowflake: 'Snowflake',
      bigquery: 'BigQuery',
      athena: 'AWS Athena',
      redshift: 'AWS Redshift',
      postgres: 'PostgreSQL',
      motherduck: 'MotherDuck',
      databricks: 'Databricks',
    };
    return state.warehouseType ? names[state.warehouseType] : '';
  };

  const startTableTest = useCallback(
    async (table: TableInfo) => {
      try {
        const response = await fetch(
          `/api/onboarding/connections/${state.warehouseType}/test-table`,
          {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              ...state.credentials,
              table_name: table.name,
            }),
          },
        );

        const result = await response.json();
        setTableTestResults((prev) => new Map(prev).set(table.name, result));
      } catch {
        setTableTestResults((prev) =>
          new Map(prev).set(table.name, {
            success: false,
            error: 'Network error',
            logs: [],
          }),
        );
      }
    },
    [state.warehouseType, state.credentials],
  );

  useEffect(() => {
    const loadTables = async () => {
      setIsLoading(true);
      setDiscoveryStatus('loading');
      setProgress(30);

      setTimeout(() => setProgress(60), 500);
      setTimeout(() => setProgress(85), 1200);

      try {
        const response = await fetch(
          `/api/onboarding/connections/${state.warehouseType}/discover-tables`,
          {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              ...state.credentials,
              selected_schemas: state.selectedSchemas,
            }),
          },
        );

        const result = await response.json();

        if (result.success && result.tables) {
          const tablesWithRecommended = result.tables.map((t: TableInfo) => ({
            ...t,
            recommended: t.recommended || false,
          }));
          setLocalTables(tablesWithRecommended);
          setDiscoveryStatus('success');
          setProgress(100);

          // Capture schema warnings if any
          if (result.schema_warnings && result.schema_warnings.length > 0) {
            setSchemaWarnings(result.schema_warnings);
          }

          // Auto-select recommended tables
          const recommendedKeys = tablesWithRecommended
            .filter((t: TableInfo & {recommended?: boolean}) => t.recommended)
            .map((t: TableInfo) => t.name);
          setSelected(new Set(recommendedKeys));

          // Start testing recommended tables
          recommendedKeys.forEach((key: string) => {
            const table = tablesWithRecommended.find((t: TableInfo) => t.name === key);
            if (table) {
              startTableTest(table);
            }
          });
        } else {
          setDiscoveryStatus('error');
          setError(result.error || 'Failed to discover tables');
        }
      } catch {
        setDiscoveryStatus('error');
        setError('Failed to load tables');
      } finally {
        setIsLoading(false);
      }
    };

    loadTables();
  }, [state.warehouseType, state.credentials, state.selectedSchemas, setError, startTableTest]);

  const sortedTables = [...localTables].sort((a, b) => {
    if (sortBy === 'recommended') {
      if (a.recommended && !b.recommended) {
        return -1;
      }
      if (!a.recommended && b.recommended) {
        return 1;
      }
    }
    return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  });

  const filteredTables = sortedTables.filter((table) =>
    table.name.toLowerCase().includes(filterText.toLowerCase()),
  );

  const hasRecommendedTables = localTables.some((t) => t.recommended);

  const handleToggle = (table: TableInfo) => {
    const newSelected = new Set(selected);

    // Check if at limit when trying to add
    if (!newSelected.has(table.name) && newSelected.size >= TABLE_SELECTION_LIMIT) {
      return;
    }

    if (newSelected.has(table.name)) {
      newSelected.delete(table.name);
      // Clear test result when deselecting
      setTableTestResults((prev) => {
        const updated = new Map(prev);
        updated.delete(table.name);
        return updated;
      });
    } else {
      newSelected.add(table.name);
      // Start testing when selecting
      startTableTest(table);
    }

    setSelected(newSelected);
    setSelectAll(newSelected.size === filteredTables.length && filteredTables.length > 0);
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelected(new Set());
      setSelectAll(false);
      setTableTestResults(new Map());
    } else {
      const allTables = new Set(filteredTables.map((t) => t.name));
      setSelected(allTables);
      setSelectAll(true);
      // Start testing all
      filteredTables.forEach((table) => startTableTest(table));
    }
  };

  const handleClearSelections = () => {
    setSelected(new Set());
    setTableTestResults(new Map());
  };

  const handleClearFilter = () => {
    setFilterText('');
  };

  const showLogs = (tableName: string) => {
    const result = tableTestResults.get(tableName);
    if (result && result.logs) {
      setLogsModalData({tableName, logs: result.logs});
      setLogsModalOpen(true);
    }
  };

  const allSelectedTestsPassed = () => {
    if (selected.size === 0) {
      return false;
    }
    for (const key of selected) {
      const result = tableTestResults.get(key);
      if (!result || !result.success) {
        return false;
      }
    }
    return true;
  };

  const handleContinue = async () => {
    if (!allSelectedTestsPassed()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const selectedTableList = localTables.filter((t) => selected.has(t.name));

      // Propagate to global state
      setTables(localTables);
      setSelectedTables(selectedTableList);

      // Call save endpoint to get connection token
      const response = await fetch(`/api/onboarding/connections/${state.warehouseType}/save`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          ...state.credentials,
          table_names: selectedTableList.map((t) => t.name),
        }),
      });

      const result = await response.json();

      if (result.success && result.connection_token) {
        setConnectionToken(result.connection_token);
        goToStep('channel-assignment');
      } else {
        setError(result.error || 'Failed to save connection configuration');
      }
    } catch {
      setError('Failed to save connection configuration');
    } finally {
      setIsSubmitting(false);
    }
  };

  const atLimit = selected.size >= TABLE_SELECTION_LIMIT;

  return (
    <WizardLayout currentStep={3}>
      <WizardHeader
        onBack={() => goToStep('schema-discovery')}
        backText="Back to Schema Selection"
        icon={state.warehouseType ? warehouseIcons[state.warehouseType] : undefined}
        title={`Select ${getWarehouseDisplayName()} Tables`}
        subtitle="Choose specific tables from your selected schemas to include in your connection"
      />

      {/* Error Banner */}
      {state.error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-red-400 mr-2 flex-shrink-0"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-red-600">{state.error}</p>
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg mb-8">
        <div className="p-4 bg-gray-50 border-b border-gray-200">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-medium text-gray-900">Available Tables</h3>
            <div className="flex items-center space-x-4">
              {/* Discovery Status */}
              <div className="flex items-center space-x-2">
                {isLoading ? (
                  <>
                    <div className="flex items-center justify-center space-x-1">
                      <div className="animate-spin h-4 w-4 border-2 border-[#3C39EE] border-t-transparent rounded-full" />
                      <span className="text-sm font-medium text-gray-600">Discovering tables</span>
                    </div>
                    <div className="w-32 bg-gray-300 rounded-full h-1 overflow-hidden">
                      <div
                        className="h-1 rounded-full transition-all duration-500 ease-out"
                        style={{
                          width: `${progress}%`,
                          background:
                            'linear-gradient(90deg, #3C39EE 0%, #5B58FF 50%, #3C39EE 100%)',
                          backgroundSize: '200% 100%',
                          animation: 'shimmer 2s infinite',
                        }}
                      />
                    </div>
                  </>
                ) : discoveryStatus === 'success' ? (
                  <>
                    <div className="flex items-center justify-center space-x-1">
                      <svg
                        className="w-4 h-4 text-green-600"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <span className="text-sm font-medium text-green-600">Complete</span>
                    </div>
                    <div className="w-32 bg-gray-300 rounded-full h-1 overflow-hidden">
                      <div className="bg-green-500 h-1 rounded-full" style={{width: '100%'}} />
                    </div>
                  </>
                ) : null}
              </div>
              {!isLoading && (
                <span className="text-sm text-gray-500">{localTables.length} tables</span>
              )}
            </div>
          </div>

          {/* Recommended Explanation */}
          {!isLoading && hasRecommendedTables && (
            <div className="mb-3">
              <p className="text-xs text-gray-500 leading-relaxed">
                Recommended tables are common datasets that help you get started faster (e.g. sales,
                support, usage, marketing).
              </p>
            </div>
          )}

          {/* Schema Permission Warnings */}
          {schemaWarnings.length > 0 && (
            <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-md">
              <div className="flex items-start">
                <svg
                  className="w-5 h-5 text-amber-600 mr-2 mt-0.5 flex-shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="flex-1">
                  <p className="text-sm text-amber-800 font-medium">Schema permission errors</p>
                  <p className="text-sm text-amber-700 mt-1">
                    Some schemas could not be accessed. You may need additional permissions for:
                  </p>
                  <ul className="mt-2 space-y-1">
                    {schemaWarnings.map((warning, index) => (
                      <li key={index} className="text-sm text-amber-700">
                        <div>
                          <span className="font-mono font-medium">{warning.schema}</span>
                          <div className="text-amber-600 mt-0.5">{warning.error}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Filter Input */}
          {!isLoading && (
            <div className="relative mb-4">
              <input
                type="text"
                placeholder="Filter tables..."
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                className="w-full px-3 py-2 pl-10 pr-8 border border-gray-300 rounded-md focus:ring-[#3C39EE] focus:border-[#3C39EE] text-sm"
              />
              <div className="absolute left-3 top-2.5">
                <svg
                  className="w-4 h-4 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              {filterText && (
                <button
                  onClick={handleClearFilter}
                  className="absolute right-2 top-2 p-1 text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
            </div>
          )}

          {/* Controls Section */}
          {!isLoading && localTables.length > 0 && (
            <div className="flex justify-between items-center">
              {/* Select All or Clear Selections */}
              {localTables.length < TABLE_SELECTION_LIMIT ? (
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="select-all-tables"
                    checked={selectAll}
                    onChange={handleSelectAll}
                    className="mr-2 h-4 w-4 text-[#3C39EE] focus:ring-[#3C39EE] border-gray-300 rounded"
                  />
                  <label
                    htmlFor="select-all-tables"
                    className="text-sm text-gray-600 cursor-pointer"
                  >
                    Select All
                  </label>
                  {selected.size > 0 && (
                    <span className="text-sm text-gray-500 ml-3">{selected.size} selected</span>
                  )}
                </div>
              ) : (
                <div className="flex items-center">
                  <span className="text-sm text-gray-500">{selected.size} selected</span>
                  <button
                    onClick={handleClearSelections}
                    disabled={selected.size === 0}
                    className="ml-4 text-sm text-gray-500 hover:underline hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed disabled:no-underline"
                  >
                    Clear selections
                  </button>
                </div>
              )}

              {/* Sort Dropdown */}
              {hasRecommendedTables && (
                <div className="relative">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as 'recommended' | 'alphabetical')}
                    className="text-sm border border-gray-300 rounded-md pl-3 pr-8 py-2 text-gray-600 appearance-none bg-white"
                  >
                    <option value="recommended">Recommended</option>
                    <option value="alphabetical">Alphabetical</option>
                  </select>
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-400">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Table Limit Warning */}
          {atLimit && (
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-md">
              <div className="flex items-start">
                <svg
                  className="w-5 h-5 text-amber-600 mr-2 mt-0.5 flex-shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                <div>
                  <p className="text-sm text-amber-800 font-medium">Table limit reached</p>
                  <p className="text-sm text-amber-700 mt-1">
                    You've reached the initial limit of {TABLE_SELECTION_LIMIT} tables for setup.
                    You can add more tables after initial setup.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Tables List */}
        <div className="divide-y divide-gray-200 max-h-[40vh] overflow-y-auto min-h-[200px]">
          {isLoading ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin h-8 w-8 border-4 border-[#3C39EE] border-t-transparent rounded-full mb-4" />
              <p className="text-gray-600">Discovering tables...</p>
            </div>
          ) : filteredTables.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              {filterText ? 'No tables match your filter' : 'No tables found'}
            </div>
          ) : (
            filteredTables.map((table) => {
              const isSelected = selected.has(table.name);
              const testResult = tableTestResults.get(table.name);
              const isDisabled = !isSelected && atLimit;

              return (
                <div
                  key={table.name}
                  className="px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <label className="flex items-start space-x-3 cursor-pointer flex-1">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleToggle(table)}
                      disabled={isDisabled}
                      className="h-4 w-4 text-[#3C39EE] focus:ring-[#3C39EE] border-gray-300 rounded mt-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 text-base mb-0.5">
                        <TruncatedName name={table.name} maxLength={50} />
                      </div>
                      <div className="flex items-center gap-1.5">
                        {table.recommended && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-blue-50 text-blue-600 border border-blue-200">
                            Recommended
                          </span>
                        )}
                      </div>
                    </div>
                  </label>

                  {/* Test Status */}
                  {isSelected && testResult && (
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-2">
                        {testResult.success ? (
                          <>
                            <div className="flex items-center justify-center w-6 h-6 bg-green-100 rounded-full">
                              <svg
                                className="w-4 h-4 text-green-600"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            </div>
                            <span className="text-sm text-green-700 font-medium">Available</span>
                          </>
                        ) : (
                          <>
                            <div className="flex items-center justify-center w-6 h-6 bg-red-100 rounded-full">
                              <svg
                                className="w-4 h-4 text-red-600"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M6 18L18 6M6 6l12 12"
                                />
                              </svg>
                            </div>
                            <span className="text-sm text-red-700 font-medium">Failed</span>
                          </>
                        )}
                      </div>
                      {testResult.logs && testResult.logs.length > 0 && (
                        <button
                          onClick={() => showLogs(table.name)}
                          className="text-gray-400 hover:text-gray-600 p-1"
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                          </svg>
                        </button>
                      )}
                    </div>
                  )}
                  {isSelected && !testResult && (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin h-4 w-4 border-2 border-[#3C39EE] border-t-transparent rounded-full" />
                      <span className="text-sm text-gray-600">Testing...</span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Continue Button */}
      <div className="flex justify-center">
        <button
          onClick={handleContinue}
          disabled={!allSelectedTestsPassed() || isSubmitting}
          className="bg-[#3C39EE] text-white px-6 py-2 rounded-md font-medium hover:bg-[#3C39EE]/90 focus:outline-none focus:ring-2 focus:ring-[#3C39EE] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div className="flex items-center justify-center">
            {isSubmitting && (
              <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" />
            )}
            <span>{isSubmitting ? 'Connecting data...' : 'Connect Data & Continue'}</span>
          </div>
        </button>
      </div>

      {/* Logs Modal */}
      {logsModalOpen && (
        <div
          className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => setLogsModalOpen(false)}
        >
          <div
            className="bg-white rounded-lg max-w-2xl w-full max-h-96 flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center p-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                Connection Test Logs: {logsModalData.tableName}
              </h3>
              <button
                onClick={() => setLogsModalOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <div className="px-4 py-6 overflow-y-auto flex-1">
              <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                {logsModalData.logs.join('\n')}
              </pre>
            </div>
          </div>
        </div>
      )}
    </WizardLayout>
  );
}

function ChannelAssignment() {
  const {state, setChannels, setSelectedChannelId, setConnectionName, goToStep, setError} =
    useWizard();
  const [searchParams] = useSearchParams();
  const [isLoading, setIsLoading] = useState(true);
  const [localChannels, setLocalChannels] = useState<ChannelInfo[]>(state.channels || []);
  const [channelOption, setChannelOption] = useState<'create' | 'existing' | null>(null);
  const [newChannelName, setNewChannelName] = useState('');
  const [selectedExistingChannels, setSelectedExistingChannels] = useState<Set<string>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [organizationName, setOrganizationName] = useState('org');
  const [isFirstConnection, setIsFirstConnection] = useState(false);
  const [autoSelectedChannel, setAutoSelectedChannel] = useState<string | null>(null);
  const [canCreateChannel, setCanCreateChannel] = useState(true);
  const [planLimitMessage, setPlanLimitMessage] = useState<string | null>(null);

  // Check for test mode
  const isTestMode = searchParams.get('test_mode') === 'true';

  const warehouseIcons: Record<WarehouseType, string> = {
    snowflake: '/static/snowflake.svg',
    bigquery: '/static/bigquery.svg',
    athena: '/static/Athena.svg',
    redshift: '/static/redshift.svg',
    postgres: '/static/postgresql.svg',
    motherduck: '/static/motherduck.svg',
    databricks: '/static/databricks.svg',
  };

  const getWarehouseDisplayName = () => {
    const names: Record<WarehouseType, string> = {
      snowflake: 'Snowflake',
      bigquery: 'BigQuery',
      athena: 'AWS Athena',
      redshift: 'AWS Redshift',
      postgres: 'PostgreSQL',
      motherduck: 'MotherDuck',
      databricks: 'Databricks',
    };
    return state.warehouseType ? names[state.warehouseType] : '';
  };

  // Auto-submit for first connection
  useEffect(() => {
    let cancelled = false;

    const autoSubmitFirstConnection = async (channelName: string) => {
      if (cancelled) return;

      setIsSubmitting(true);
      try {
        const response = await fetch('/api/onboarding/connections/complete', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            connection_name: 'from_token', // Validated but unused; actual name comes from JWT
            connection_token: state.connectionToken,
            channelSelection: {
              type: 'create',
              channels: [channelName],
            },
          }),
        });

        const result = await response.json();

        if (cancelled) return;

        if (result.success) {
          // Add the created channel to state so it displays correctly on success page
          setChannels([{id: channelName, name: channelName}]);
          setSelectedChannelId(channelName);
          // Store connection name for dataset sync polling
          if (result.connection_name) {
            setConnectionName(result.connection_name);
          }
          goToStep('success');
        } else {
          setError(result.error || 'Failed to create channel');
          setIsSubmitting(false);
        }
      } catch {
        if (!cancelled) {
          setError('Failed to create channel');
          setIsSubmitting(false);
        }
      }
    };

    const loadChannels = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('/api/onboarding/connections/fetch-channels');
        const result = await response.json();

        if (cancelled) return;

        // Store plan limit information
        if (result.can_create_channel !== undefined) {
          setCanCreateChannel(result.can_create_channel);
        }
        if (result.plan_limit_message) {
          setPlanLimitMessage(result.plan_limit_message);
        }

        // Check if this is the first connection
        if (result.success && result.is_first_connection && result.auto_selected_channel) {
          setIsFirstConnection(true);
          setAutoSelectedChannel(result.auto_selected_channel);
          setIsLoading(false);
          // Auto-submit immediately for first connection
          await autoSubmitFirstConnection(result.auto_selected_channel);
          return;
        }

        // Regular flow for returning users
        if (result.success && result.channels) {
          setLocalChannels(result.channels);
          if (result.organization_name) {
            setOrganizationName(result.organization_name);
          }
        } else {
          setError(result.error || 'Failed to load channels');
        }
      } catch {
        if (!cancelled) {
          setError('Failed to load Slack channels');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadChannels();

    return () => {
      cancelled = true;
    };
  }, [
    goToStep,
    setChannels,
    setConnectionName,
    setError,
    setSelectedChannelId,
    state.connectionToken,
  ]);

  const toggleExistingChannel = (channelId: string) => {
    const newSelected = new Set(selectedExistingChannels);
    if (newSelected.has(channelId)) {
      newSelected.delete(channelId);
    } else {
      newSelected.add(channelId);
    }
    setSelectedExistingChannels(newSelected);
  };

  const isValid = () => {
    if (channelOption === 'create') {
      return newChannelName.trim().length > 0;
    } else if (channelOption === 'existing') {
      return selectedExistingChannels.size > 0;
    }
    return false;
  };

  const handleSubmit = async () => {
    if (!isValid()) {
      return;
    }

    // Validate channel name format for new channels
    if (channelOption === 'create') {
      const channelName = newChannelName.trim();
      const channelNameRegex = /^[a-z0-9-_]+$/;
      if (!channelNameRegex.test(channelName)) {
        setError(
          'Channel name can only contain lowercase letters, numbers, hyphens, and underscores.',
        );
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const channelSelection = {
        type: channelOption,
        channels:
          channelOption === 'create'
            ? [`${organizationName}-compass-${newChannelName.trim()}`]
            : Array.from(selectedExistingChannels).map(
                (id) => localChannels.find((c) => c.id === id)?.name || '',
              ),
      };

      const response = await fetch('/api/onboarding/connections/complete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          connection_name: 'from_token', // Validated but unused; actual name comes from JWT
          connection_token: state.connectionToken,
          channelSelection: channelSelection,
        }),
      });

      const result = await response.json();

      if (result.success) {
        // Propagate to global state
        setChannels(localChannels);

        // Store first channel for success page
        if (channelSelection.channels.length > 0) {
          const firstChannel = localChannels.find(
            (c) => c.id === Array.from(selectedExistingChannels)[0],
          );
          if (firstChannel) {
            setSelectedChannelId(firstChannel.id);
          }
        }
        // Store connection name for dataset sync polling
        if (result.connection_name) {
          setConnectionName(result.connection_name);
        }
        goToStep('success');
      } else {
        setError(result.error || 'Failed to complete connection setup');
      }
    } catch {
      setError('Failed to submit connection');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <WizardLayout currentStep={4}>
      <WizardHeader
        onBack={() => goToStep('table-selection')}
        backText="Back to Table Selection"
        icon={state.warehouseType ? warehouseIcons[state.warehouseType] : undefined}
        title={`Connect ${getWarehouseDisplayName()} to Channels`}
        subtitle="Choose where your data will be available in Slack"
      />

      {/* Test Mode Banner */}
      {isTestMode && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-sm font-medium text-blue-800">
              🧪 Test Mode Active - This is a test connection
            </span>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {state.error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-red-400 mr-2 flex-shrink-0"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-red-600">{state.error}</p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading || isFirstConnection ? (
        <div className="text-center py-12">
          <div className="inline-flex flex-col items-center">
            <div className="animate-spin h-10 w-10 border-4 border-[#3C39EE] border-t-transparent rounded-full mb-4" />
            <p className="text-lg font-medium text-gray-700">
              {isFirstConnection && autoSelectedChannel
                ? `Creating #${autoSelectedChannel}...`
                : 'Connecting to channels...'}
            </p>
            <p className="text-sm text-gray-500 mt-2">Setting up your workspace</p>
          </div>
        </div>
      ) : (
        <>
          {/* Channel Selection Options */}
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden mb-8">
            <div className="p-6">
              {/* Option A: Create new channel */}
              <div className="mb-6">
                <label
                  className={`flex items-start ${canCreateChannel ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'} group`}
                >
                  <input
                    type="radio"
                    name="channel-option"
                    value="create"
                    checked={channelOption === 'create'}
                    onChange={() => {
                      if (canCreateChannel) {
                        setChannelOption('create');
                        setError(null); // Clear error when switching options
                      }
                    }}
                    disabled={!canCreateChannel}
                    className="w-4 h-4 mt-1 text-[#3C39EE] border-gray-300 focus:ring-[#3C39EE] focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <div className="ml-3 flex-1">
                    <span className="block text-base font-medium text-gray-900 group-hover:text-gray-700">
                      Create a new channel
                    </span>
                    <span className="block text-sm text-gray-500 mt-1">
                      {canCreateChannel
                        ? "We'll create this channel for your data."
                        : 'Channel limit reached for your plan.'}
                    </span>

                    {/* Plan limit message */}
                    {!canCreateChannel && planLimitMessage && (
                      <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
                        {planLimitMessage}
                      </div>
                    )}

                    {/* New channel input */}
                    {channelOption === 'create' && (
                      <div className="mt-3">
                        <ChannelNameInput
                          value={newChannelName}
                          onChange={setNewChannelName}
                          placeholder="company-data"
                        />
                        <p className="text-xs text-gray-500 mt-2">
                          Only lowercase letters, numbers, hyphens, and underscores allowed
                        </p>
                      </div>
                    )}
                  </div>
                </label>
              </div>

              <div className="border-t border-gray-200 my-6" />

              {/* Option B: Add to existing channels */}
              <div>
                <label className="flex items-start cursor-pointer group">
                  <input
                    type="radio"
                    name="channel-option"
                    value="existing"
                    checked={channelOption === 'existing'}
                    onChange={() => {
                      setChannelOption('existing');
                      setError(null); // Clear error when switching options
                    }}
                    className="w-4 h-4 mt-1 text-[#3C39EE] border-gray-300 focus:ring-[#3C39EE] focus:ring-2"
                  />
                  <div className="ml-3 flex-1">
                    <span className="block text-base font-medium text-gray-900 group-hover:text-gray-700">
                      Add to existing Compass channels
                    </span>
                    <span className="block text-sm text-gray-500 mt-1">
                      Pick one or more channels where Compass should post updates.
                    </span>

                    {/* Existing channels select */}
                    {channelOption === 'existing' && (
                      <div className="mt-3">
                        <div className="bg-gray-50 border border-gray-200 rounded-md p-2">
                          <div className="space-y-2 max-h-48 overflow-y-auto">
                            {localChannels.length === 0 ? (
                              <div className="p-4 text-center text-sm text-gray-500">
                                No existing Compass channels found
                              </div>
                            ) : (
                              localChannels.map((channel) => (
                                <label
                                  key={channel.id}
                                  className="flex items-center p-2 hover:bg-white rounded cursor-pointer"
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedExistingChannels.has(channel.id)}
                                    onChange={() => toggleExistingChannel(channel.id)}
                                    className="h-4 w-4 text-[#3C39EE] border-gray-300 rounded focus:ring-[#3C39EE]"
                                  />
                                  <span className="ml-2 text-sm text-gray-700">
                                    #{channel.name}
                                  </span>
                                </label>
                              ))
                            )}
                          </div>
                        </div>
                        <p className="mt-2 text-xs text-gray-500">Select one or more channels</p>
                      </div>
                    )}
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Continue Button */}
          <div className="flex justify-center">
            <button
              onClick={handleSubmit}
              disabled={!isValid() || isSubmitting}
              className="bg-[#3C39EE] text-white px-6 py-2 rounded-md font-medium hover:bg-[#3C39EE]/90 focus:outline-none focus:ring-2 focus:ring-[#3C39EE] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center justify-center">
                {isSubmitting && (
                  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                )}
                <span>{isSubmitting ? 'Connecting...' : 'Connect to Channels'}</span>
              </div>
            </button>
          </div>
        </>
      )}
    </WizardLayout>
  );
}

interface DatasetSyncDataset {
  table_name: string;
  status: 'processing' | 'completed' | 'failed';
  message: string;
}

interface DatasetSyncDetails {
  workflow_id: string;
  connection_name: string;
  status: 'in_progress' | 'completed' | 'failed';
  datasets: DatasetSyncDataset[];
  pr_url?: string;
}

function ConnectionSuccess() {
  const {state} = useWizard();
  const location = useLocation();
  const navigate = useNavigate();
  const [datasetSyncDetails, setDatasetSyncDetails] = useState<DatasetSyncDetails | null>(null);

  const channelName =
    state.channels.find((c) => c.id === state.selectedChannelId)?.name || 'your channel';

  // Detect if we're in onboarding flow
  const isOnboarding = location.pathname.startsWith('/onboarding');

  // For non-onboarding flows, redirect to standalone progress page
  // Wait briefly to ensure the workflow has started before redirecting
  useEffect(() => {
    if (!isOnboarding && state.connectionName) {
      const progressUrl = `/dataset-sync?connection=${encodeURIComponent(state.connectionName)}`;

      // Delay redirect by 2 seconds to allow workflow to start
      const redirectTimer = setTimeout(() => {
        navigate(progressUrl);
      }, 2000);

      return () => clearTimeout(redirectTimer);
    }
  }, [isOnboarding, state.connectionName, navigate]);

  // Poll for dataset sync status (only for onboarding flow)
  useEffect(() => {
    if (!isOnboarding) {
      // Skip polling for non-onboarding flows since we redirect
      return;
    }

    if (!state.connectionName) {
      return;
    }

    const connName = state.connectionName;
    // eslint-disable-next-line prefer-const
    let pollInterval: ReturnType<typeof setInterval>;

    const pollDatasetSync = async () => {
      try {
        const response = await fetch(
          `/api/dataset-sync/details?connection_name=${encodeURIComponent(connName)}`,
        );

        if (!response.ok) {
          if (response.status === 404) {
            // Sync not started yet or not found - this is normal at first
            return;
          }
          throw new Error('Failed to fetch dataset sync status');
        }

        const data: DatasetSyncDetails = await response.json();
        setDatasetSyncDetails(data);

        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Dataset sync polling error:', err);
      }
    };

    // Start polling immediately
    pollDatasetSync();

    // Continue polling every 3 seconds
    pollInterval = setInterval(pollDatasetSync, 3000);

    // Stop polling after 10 minutes
    const timeout = setTimeout(() => {
      clearInterval(pollInterval);
    }, 600000);

    return () => {
      clearInterval(pollInterval);
      clearTimeout(timeout);
    };
  }, [isOnboarding, state.connectionName]);

  const syncComplete = datasetSyncDetails?.status === 'completed';

  // Show redirecting message for non-onboarding flows
  if (!isOnboarding) {
    return (
      <WizardLayout currentStep={6}>
        <div className="max-w-2xl mx-auto">
          <h1 className="text-center text-2xl font-semibold text-gray-900 mb-6">
            Connection Added Successfully
          </h1>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-6">
            <div className="flex items-center justify-center gap-2">
              <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
              <p className="text-base text-gray-700 font-medium">Redirecting to progress page...</p>
            </div>
          </div>
        </div>
      </WizardLayout>
    );
  }

  return (
    <WizardLayout currentStep={6}>
      <div className="max-w-2xl mx-auto">
        {!syncComplete ? (
          <>
            {/* Syncing In Progress */}
            <h1 className="text-center text-2xl font-semibold text-gray-900 mb-6">
              {"We're getting things ready…"}
            </h1>

            {/* Status Banner */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-6">
              <div className="flex items-center justify-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                <p className="text-base text-gray-700 font-medium">
                  {datasetSyncDetails ? 'Analyzing your datasets...' : 'Processing...'}
                </p>
              </div>
            </div>

            {/* Dataset Sync Progress */}
            {datasetSyncDetails && datasetSyncDetails.datasets.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Dataset Analysis</h3>
                <p className="text-sm text-gray-600 mb-4">
                  We'll invite you to Slack when your datasets are ready.
                </p>

                <div className="space-y-2">
                  {datasetSyncDetails.datasets.map((dataset) => (
                    <div
                      key={dataset.table_name}
                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-md"
                    >
                      {dataset.status === 'processing' && (
                        <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full flex-shrink-0"></div>
                      )}
                      {dataset.status === 'completed' && (
                        <svg
                          className="w-4 h-4 text-green-600 flex-shrink-0"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z" />
                        </svg>
                      )}
                      {dataset.status === 'failed' && (
                        <svg
                          className="w-4 h-4 text-red-600 flex-shrink-0"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                        </svg>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">
                          <TruncatedName name={dataset.table_name} maxLength={50} />
                        </p>
                        {dataset.message && (
                          <p className="text-xs text-gray-500">{dataset.message}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="max-w-2xl w-full">
            <OnboardingComplete channelName={channelName} />
          </div>
        )}

        {/* Compass Logo */}
        <div className="text-center pt-4 pb-6">
          <img
            src="/static/compass-logo-mark.svg"
            alt="Compass Logo"
            className="mx-auto"
            style={{width: '40px'}}
          />
        </div>
      </div>
    </WizardLayout>
  );
}
