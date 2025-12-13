import {useState, useEffect, useRef} from 'react';
import {Chart, ChartConfiguration, registerables} from 'chart.js';
import {fetchWithAuth} from './utils/authErrors';
import {ErrorMessage} from './components/ErrorMessage';

// Register Chart.js components
Chart.register(...registerables);

// Stripe types
interface StripeCardElement {
  mount: (selector: string) => void;
  unmount: () => void;
  destroy: () => void;
  on: (event: string, handler: (event: {error?: {message: string}}) => void) => void;
}

interface StripeElements {
  create: (type: string, options?: unknown) => StripeCardElement;
}

interface StripeInstance {
  elements: (options?: unknown) => StripeElements;
  confirmCardSetup: (
    clientSecret: string,
    data: {payment_method: {card: StripeCardElement}},
  ) => Promise<{
    setupIntent?: {id: string; payment_method: string};
    error?: {message: string};
  }>;
}

interface StripeConstructor {
  (publishableKey: string): StripeInstance;
}

declare global {
  interface Window {
    Stripe: StripeConstructor;
    pendingPlanSelection?: string;
    isUpdateMode?: boolean;
    currentClientSecret?: string;
  }
}

interface PlanData {
  name: string;
  description: string;
  formatted_price: string;
  features: string[];
  color_scheme: string;
  product_id: string | null;
}

interface UsageData {
  total_answers: number;
  total_answers_no_bonus: number;
  bonus_answers_this_month: number;
  total_unique_users: number;
  bot_count: number;
  current_month_name: string;
  bonus_answers_remaining: number;
  bonus_answers_earned: number;
  bonus_answers_used: number;
  plan_limit: number | null;
  has_overage_available: boolean;
  bot_details: Array<{
    channel_name: string;
    bot_id: string;
    answer_count: number;
    unique_users_this_month: number;
    last_updated: string;
  }>;
}

interface PaymentMethod {
  id: string;
  card: {
    brand: string;
    last4: string;
    exp_month: number;
    exp_year: number;
  };
}

interface PaymentMethodInfo {
  has_payment_method: boolean;
  payment_methods: PaymentMethod[];
}

interface BillingDetails {
  email: string | null;
}

interface BillingData {
  plan_pricing_data: PlanData[];
  current_plan: string | null;
  usage_data: UsageData | null;
  has_subscription: boolean;
  payment_method_info: PaymentMethodInfo | null;
  billing_details: BillingDetails | null;
  no_bot_available: boolean;
  has_stripe_client: boolean;
  stripe_publishable_key: string | null;
}

interface UsageHistoryData {
  months: Array<{
    month: string;
    answer_count: number;
  }>;
  plan_limit: number | null;
}

export default function Billing() {
  const [billing, setBilling] = useState<BillingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [editingBillingDetails, setEditingBillingDetails] = useState(false);
  const [billingEmail, setBillingEmail] = useState('');

  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstanceRef = useRef<Chart | null>(null);
  const stripeRef = useRef<StripeInstance | null>(null);
  const cardElementRef = useRef<StripeCardElement | null>(null);
  const elementsRef = useRef<StripeElements | null>(null);

  useEffect(() => {
    fetchBillingData();

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
    };
  }, []);

  useEffect(() => {
    if (billing && chartRef.current) {
      initializeUsageChart();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [billing]);

  useEffect(() => {
    if (billing?.has_stripe_client && billing?.stripe_publishable_key && !stripeRef.current) {
      const script = document.createElement('script');
      script.src = 'https://js.stripe.com/v3/';
      script.async = true;
      script.onload = () => {
        if (billing.stripe_publishable_key) {
          stripeRef.current = window.Stripe(billing.stripe_publishable_key);
        }
      };
      document.body.appendChild(script);
    }
  }, [billing]);

  const fetchBillingData = async () => {
    try {
      const response = await fetchWithAuth('/api/billing/data');
      const data = await response.json();
      setBilling(data);
      if (data.billing_details?.email) {
        setBillingEmail(data.billing_details.email);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const initializeUsageChart = async () => {
    try {
      const response = await fetch('/api/billing/usage-history');
      if (!response.ok) {
        console.error('Failed to load usage history');
        return;
      }

      const data: UsageHistoryData = await response.json();
      if (data.months && chartRef.current) {
        renderUsageChart(data.months, data.plan_limit);
      }
    } catch (error) {
      console.error('Failed to load usage history:', error);
    }
  };

  const renderUsageChart = (
    monthsData: Array<{month: string; answer_count: number}>,
    planLimit: number | null,
  ) => {
    if (!chartRef.current) {
      return;
    }

    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
    }

    const ctx = chartRef.current.getContext('2d');
    if (!ctx) {
      return;
    }

    const labels = monthsData.map((month) => month.month);
    const data = monthsData.map((month) => month.answer_count);

    const datasets: ChartConfiguration<'line'>['data']['datasets'] = [
      {
        label: 'Answers',
        data: data,
        borderColor: 'rgba(79, 70, 229, 1)',
        backgroundColor: 'rgba(79, 70, 229, 0.1)',
        pointBackgroundColor: 'rgba(79, 70, 229, 0.6)',
        pointBorderColor: 'rgba(79, 70, 229, 1)',
        pointRadius: 6,
        pointHoverRadius: 8,
        borderWidth: 2,
        fill: true,
        tension: 0.2,
      },
    ];

    if (planLimit && planLimit > 0) {
      const limitData = new Array(labels.length).fill(planLimit);
      datasets.push({
        label: 'Monthly Limit',
        data: limitData,
        borderColor: 'rgba(239, 68, 68, 0.8)',
        backgroundColor: 'transparent',
        pointRadius: 0,
        pointHoverRadius: 0,
        borderWidth: 2,
        borderDash: [8, 4],
        fill: false,
        tension: 0,
      });
    }

    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels: labels,
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: !!(planLimit && planLimit > 0),
            position: 'top',
            align: 'end',
            labels: {
              usePointStyle: true,
              pointStyle: 'line',
              padding: 15,
              filter: (item) => item.text === 'Monthly Limit',
            },
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const value = context.parsed.y ?? 0;
                if (context.dataset.label === 'Monthly Limit') {
                  return `Monthly Limit: ${value.toLocaleString()}`;
                }
                return `Answers: ${value.toLocaleString()}`;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => value.toLocaleString(),
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.1)',
            },
          },
          x: {
            grid: {
              display: false,
            },
          },
        },
      },
    };

    chartInstanceRef.current = new Chart(ctx, config);
  };

  const handlePlanClick = async (planName: string) => {
    const planNameLower = planName.toLowerCase();

    // Special handling for Pro plan
    if (planNameLower === 'pro') {
      window.location.href = 'mailto:compass-support@dagsterlabs.com';
      return;
    }

    const hasPaymentMethod = billing?.payment_method_info?.has_payment_method || false;

    if (!hasPaymentMethod && planNameLower !== 'free') {
      // No payment method and not free plan - open payment method modal first
      window.pendingPlanSelection = planName;
      openPaymentMethodModal('add');
    } else {
      // Has payment method or selecting free plan - allow direct plan switching
      await switchPlan(planName);
    }
  };

  const switchPlan = async (planName: string) => {
    try {
      const response = await fetch('/api/billing/switch-plan', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({plan_name: planName}),
      });

      const data = await response.json();

      if (data.success) {
        showMessage(data.message || 'Plan switched successfully!', 'success');
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        showMessage(data.error || 'Failed to switch plan', 'error');
      }
    } catch (err) {
      console.error('Plan switch error:', err);
      showMessage('Network error while switching plans', 'error');
    }
  };

  const showMessage = (message: string, type: 'success' | 'error') => {
    const messageDiv = document.createElement('div');
    messageDiv.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-md ${
      type === 'success'
        ? 'bg-green-100 border border-green-400 text-green-700'
        : 'bg-red-100 border border-red-400 text-red-700'
    }`;
    messageDiv.innerHTML = `<div class="flex items-center"><span>${message}</span><button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-lg leading-none">&times;</button></div>`;

    document.body.appendChild(messageDiv);

    setTimeout(() => {
      if (messageDiv.parentElement) {
        messageDiv.remove();
      }
    }, 5000);
  };

  const openPaymentMethodModal = async (mode: 'add' | 'update') => {
    if (!stripeRef.current) {
      showMessage('Stripe is not loaded', 'error');
      return;
    }

    window.isUpdateMode = mode === 'update';
    setShowPaymentModal(true);

    try {
      const response = await fetch('/api/billing/create-setup-intent', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
      });

      const data = await response.json();

      if (data.success && data.client_secret) {
        window.currentClientSecret = data.client_secret;

        elementsRef.current = stripeRef.current.elements();
        cardElementRef.current = elementsRef.current.create('card', {
          style: {
            base: {
              fontSize: '16px',
              color: '#424770',
              '::placeholder': {
                color: '#aab7c4',
              },
            },
          },
        });

        setTimeout(() => {
          const cardElement = document.getElementById('card-element');
          if (cardElement && cardElementRef.current) {
            cardElementRef.current.mount('#card-element');

            cardElementRef.current.on('change', (event: {error?: {message: string}}) => {
              const displayError = document.getElementById('card-errors');
              if (displayError) {
                displayError.textContent = event.error ? event.error.message : '';
              }
            });
          }
        }, 100);
      } else {
        showMessage(data.error || 'Failed to initialize payment method setup', 'error');
        setShowPaymentModal(false);
      }
    } catch (error) {
      console.error('Setup intent error:', error);
      showMessage('Network error while setting up payment method', 'error');
      setShowPaymentModal(false);
    }
  };

  const closePaymentMethodModal = () => {
    setShowPaymentModal(false);

    if (cardElementRef.current) {
      cardElementRef.current.destroy();
      cardElementRef.current = null;
    }
    if (elementsRef.current) {
      elementsRef.current = null;
    }

    const displayError = document.getElementById('card-errors');
    if (displayError) {
      displayError.textContent = '';
    }

    window.isUpdateMode = false;
    window.pendingPlanSelection = undefined;
  };

  const handleAddPaymentMethod = async () => {
    if (!cardElementRef.current || !window.currentClientSecret || !stripeRef.current) {
      showMessage('Payment setup not initialized properly', 'error');
      return;
    }

    try {
      const result = await stripeRef.current.confirmCardSetup(window.currentClientSecret, {
        payment_method: {
          card: cardElementRef.current,
        },
      });

      if (result.error) {
        const displayError = document.getElementById('card-errors');
        if (displayError) {
          displayError.textContent = result.error.message;
        }
      } else if (result.setupIntent) {
        const setupIntentId = result.setupIntent.id;

        const currentPaymentMethodId =
          billing?.payment_method_info?.payment_methods?.[0]?.id || null;

        const response = await fetch('/api/billing/confirm-payment-method', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            setup_intent_id: setupIntentId,
            old_payment_method_id: window.isUpdateMode ? currentPaymentMethodId : null,
          }),
        });

        const data = await response.json();

        if (data.success) {
          const message = window.isUpdateMode
            ? 'Payment method updated successfully!'
            : 'Payment method added successfully!';
          showMessage(message, 'success');
          closePaymentMethodModal();
          handlePostPaymentMethodSuccess();
        } else {
          showMessage(data.error || 'Failed to confirm payment method', 'error');
        }
      } else {
        showMessage('Payment setup failed: No setup intent returned', 'error');
      }
    } catch (error) {
      console.error('Payment method confirmation error:', error);
      showMessage('Network error while confirming payment method', 'error');
    }
  };

  const handlePostPaymentMethodSuccess = () => {
    if (window.pendingPlanSelection) {
      const pendingPlan = window.pendingPlanSelection;
      window.pendingPlanSelection = undefined;

      showMessage(`Switching to ${pendingPlan} plan...`, 'success');

      setTimeout(() => {
        switchPlan(pendingPlan);
      }, 1000);
    } else {
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    }
  };

  const deletePaymentMethod = async (paymentMethodId: string) => {
    if (!confirm('Are you sure you want to remove this payment method?')) {
      return;
    }

    try {
      const response = await fetch(`/api/billing/payment-method/${paymentMethodId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.success) {
        showMessage(data.message || 'Payment method removed successfully', 'success');
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        showMessage(data.error || 'Failed to remove payment method', 'error');
      }
    } catch (error) {
      console.error('Delete payment method error:', error);
      showMessage('Network error while removing payment method', 'error');
    }
  };

  const saveBillingDetails = async () => {
    try {
      const response = await fetch('/api/billing/customer-details', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email: billingEmail.trim()}),
      });

      const data = await response.json();

      if (data.success) {
        showMessage(data.message || 'Billing details updated successfully', 'success');
        setEditingBillingDetails(false);
        fetchBillingData();
      } else {
        showMessage(data.error || 'Failed to update billing details', 'error');
      }
    } catch (error) {
      console.error('Update billing details error:', error);
      showMessage('Network error while updating billing details', 'error');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-gray-600">Loading billing data...</div>
      </div>
    );
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  if (!billing) {
    return <div />;
  }

  if (billing.no_bot_available) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <p className="text-yellow-800">
            No bot instances are currently available to retrieve usage data.
          </p>
        </div>
      </div>
    );
  }

  const usage = billing.usage_data;
  const planPricingData = billing.plan_pricing_data || [];
  const currentPlanLower = billing.current_plan?.toLowerCase();
  const planNamesLower = planPricingData.map((p) => p.name.toLowerCase());
  const planNotFound = currentPlanLower && !planNamesLower.includes(currentPlanLower);
  const proIsCurrent = currentPlanLower === 'pro' || planNotFound;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {billing.has_subscription && planPricingData.length > 0 && (
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">Plans and pricing</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {planPricingData.map((plan) => {
              const isCurrentPlan =
                currentPlanLower && plan.name.toLowerCase() === currentPlanLower;
              const isRecommendedPlan = !billing.current_plan && plan.name === 'Starter';
              const isFallbackPro = planNotFound && plan.name === 'Pro';
              const isFocused = isCurrentPlan || isRecommendedPlan || isFallbackPro;

              return (
                <div
                  key={plan.name}
                  className={`bg-white rounded-lg p-6 flex flex-col h-full relative ${
                    isFocused ? 'shadow-lg border-2 border-blue-500' : 'shadow-md'
                  }`}
                >
                  {(isCurrentPlan || isFallbackPro) && (
                    <div className="absolute top-0 right-0 bg-blue-500 text-white text-xs font-bold px-2 py-1 rounded-bl-md">
                      Current
                    </div>
                  )}
                  {isRecommendedPlan && (
                    <div className="absolute top-0 right-0 bg-blue-500 text-white text-xs font-bold px-2 py-1 rounded-bl-md">
                      Recommended
                    </div>
                  )}

                  <div className="flex-1">
                    <div
                      className={`text-3xl font-bold mt-2 text-gray-700 ${isFocused ? 'text-gray-900' : ''}`}
                    >
                      {plan.name}
                    </div>
                    <h3 className="text-lg font-semibold text-gray-700 mb-4">
                      {plan.formatted_price}
                    </h3>
                    <p className="text-gray-600 text-sm mb-6 min-h-16">{plan.description}</p>

                    {plan.features && plan.features.length > 0 && (
                      <ul className="text-sm text-gray-600 mb-6 space-y-2">
                        {plan.features.map((feature, idx) => (
                          <li key={idx} className="flex items-start">
                            <svg
                              className="w-4 h-4 text-green-500 mt-0.5 mr-2 flex-shrink-0"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fillRule="evenodd"
                                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                clipRule="evenodd"
                              />
                            </svg>
                            <span>{feature}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="text-center">
                    {isCurrentPlan || isFallbackPro ? (
                      <button
                        disabled
                        className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg cursor-not-allowed"
                      >
                        Current Plan
                      </button>
                    ) : proIsCurrent && plan.name !== 'Pro' ? null : isRecommendedPlan ? (
                      <button
                        onClick={() => handlePlanClick(plan.name)}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg"
                      >
                        Choose {plan.name}
                      </button>
                    ) : (
                      <button
                        onClick={() => handlePlanClick(plan.name)}
                        className="w-full border border-gray-600 hover:bg-gray-200 text-gray-600 hover:text-gray-800 font-medium py-2 px-4 rounded-lg"
                      >
                        {plan.name === 'Pro' ? 'Contact Us' : `Choose ${plan.name}`}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="mb-6">
        <h2 className="text-3xl font-bold text-gray-900 mb-6">Usage and payments</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {usage && (
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Usage in {usage.current_month_name}
            </h2>
            <div className="space-y-4">
              <div className="py-2 border-b border-gray-100">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">Total answers</span>
                  <span className="text-3xl font-bold text-blue-600">
                    {usage.total_answers.toLocaleString()}
                  </span>
                </div>
                <div className="ml-4 space-y-1">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-500">Bonus answers used</span>
                    <span className="text-gray-700 font-medium">
                      {usage.bonus_answers_this_month.toLocaleString()}
                    </span>
                  </div>
                  {usage.has_overage_available && (
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-500">Overage answers</span>
                      <span className="text-gray-700 font-medium">
                        {usage.plan_limit && usage.plan_limit > 0
                          ? Math.max(
                              0,
                              usage.total_answers -
                                usage.bonus_answers_this_month -
                                usage.plan_limit,
                            ).toLocaleString()
                          : '0'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-gray-600">Users who asked questions</span>
                <span className="text-2xl font-bold text-blue-brand">
                  {usage.total_unique_users.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-gray-600">Active bots</span>
                <span className="text-2xl font-bold text-gray-900">{usage.bot_count}</span>
              </div>
              <div className="text-sm text-gray-600 mt-4">
                <p className="mb-2">Answer counts show cumulative totals for all bots.</p>
                <p>Users counted only if they asked questions this month.</p>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Plan details</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-gray-600">Monthly answer limit</span>
              <span className="text-2xl font-bold text-blue-600">
                {usage?.plan_limit ? usage.plan_limit.toLocaleString() : 'N/A'}
              </span>
            </div>
            <div className="py-2 border-b border-gray-100">
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-600">Bonus answers</span>
                <span className="text-xl font-semibold text-green-600">
                  {usage?.bonus_answers_remaining.toLocaleString() || '0'}
                </span>
              </div>
              <div className="ml-4 space-y-1">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-500">Lifetime total earned</span>
                  <span className="text-gray-700 font-medium">
                    {usage?.bonus_answers_earned.toLocaleString() || '0'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-500">Lifetime total used</span>
                  <span className="text-gray-700 font-medium">
                    {usage?.bonus_answers_used.toLocaleString() || '0'}
                  </span>
                </div>
              </div>
            </div>
            <div className="text-sm text-gray-600 mt-4">
              {usage?.plan_limit &&
                usage.plan_limit > 0 &&
                (usage.has_overage_available ? (
                  <p className="mb-2">
                    When your monthly limit is reached, bonus answers will be consumed first before
                    any overage charges apply. Answers above the limit will be charged overage fees.
                  </p>
                ) : (
                  <p className="mb-2">
                    When your monthly limit is reached, bonus answers will be consumed. Upgrade plan
                    to get more answers when limit is reached.
                  </p>
                ))}
            </div>
          </div>
        </div>
      </div>

      {usage && (
        <>
          <div className="mt-8 bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Usage History</h2>
            <div className="relative" style={{height: '300px'}}>
              <canvas ref={chartRef} className="w-full h-full"></canvas>
            </div>
            <div className="text-sm text-gray-600 mt-2">
              <p>Monthly answer totals for all bots combined</p>
            </div>
          </div>

          <div className="mt-8 bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Bot Usage Details</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-gray-200">
                  <tr>
                    <th className="text-left py-2 text-sm font-semibold text-gray-700">
                      Bot channel
                    </th>
                    <th className="text-right py-2 text-sm font-semibold text-gray-700">Answers</th>
                    <th className="text-right py-2 text-sm font-semibold text-gray-700">
                      Active users
                    </th>
                    <th className="text-right py-2 text-sm font-semibold text-gray-700">
                      Last updated
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {usage.bot_details.map((bot) => (
                    <tr key={bot.bot_id} className="border-b border-gray-100">
                      <td className="py-2 text-sm text-gray-800">{bot.channel_name}</td>
                      <td className="py-2 text-right text-sm font-semibold">
                        {bot.answer_count.toLocaleString()}
                      </td>
                      <td className="py-2 text-right text-sm font-semibold text-blue-600">
                        {bot.unique_users_this_month.toLocaleString()}
                      </td>
                      <td className="py-2 text-right text-xs text-gray-500">{bot.last_updated}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {billing.has_subscription && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Payment Method</h2>
              {billing.payment_method_info?.has_payment_method ? (
                <button
                  onClick={() => openPaymentMethodModal('update')}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Update Payment Method
                </button>
              ) : (
                <button
                  onClick={() => openPaymentMethodModal('add')}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Add Payment Method
                </button>
              )}
            </div>
            <div className="space-y-4">
              {billing.payment_method_info === null ? (
                <p className="text-gray-500">Payment information not available</p>
              ) : billing.payment_method_info.has_payment_method ? (
                <>
                  <div className="flex items-center space-x-2 mb-4">
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    <span className="text-green-700 font-medium">Payment method configured</span>
                  </div>
                  {billing.payment_method_info.payment_methods &&
                    billing.payment_method_info.payment_methods.length > 0 && (
                      <div className="p-3 bg-gray-50 rounded-lg">
                        {billing.payment_method_info.payment_methods.map((method) => (
                          <div key={method.id} className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <div className="flex items-center space-x-2">
                                <div className="text-sm font-medium text-gray-700">
                                  {method.card.brand
                                    ? method.card.brand.charAt(0).toUpperCase() +
                                      method.card.brand.slice(1)
                                    : 'Unknown'}
                                </div>
                                <div className="text-sm text-gray-600">
                                  •••• •••• •••• {method.card.last4 || '****'}
                                </div>
                              </div>
                              <div className="text-xs text-gray-500">
                                {String(method.card.exp_month).padStart(2, '0')}/
                                {String(method.card.exp_year % 100).padStart(2, '0')}
                              </div>
                            </div>
                            <button
                              onClick={() => deletePaymentMethod(method.id)}
                              className="text-red-600 hover:text-red-800 text-xs font-medium py-1 px-2 rounded transition-colors"
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                </>
              ) : (
                <>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                    <span className="text-orange-700 font-medium">No payment method</span>
                  </div>
                  <p className="text-sm text-gray-600">
                    Add a payment method to enable plan upgrades and avoid service interruption
                  </p>
                </>
              )}
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Billing Details</h2>
              {!editingBillingDetails && (
                <button
                  onClick={() => setEditingBillingDetails(true)}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium py-1 px-2 rounded transition-colors"
                >
                  Edit
                </button>
              )}
            </div>
            <div className="space-y-4">
              {billing.billing_details === null ? (
                <p className="text-gray-500">Billing details not available</p>
              ) : editingBillingDetails ? (
                <div className="space-y-3">
                  <div>
                    <label
                      htmlFor="edit-email"
                      className="block text-sm font-medium text-gray-700 mb-1"
                    >
                      Contact Email
                    </label>
                    <input
                      type="email"
                      id="edit-email"
                      value={billingEmail}
                      onChange={(e) => setBillingEmail(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={saveBillingDetails}
                      className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setEditingBillingDetails(false);
                        setBillingEmail(billing.billing_details?.email || '');
                      }}
                      className="bg-gray-300 hover:bg-gray-400 text-gray-700 text-sm font-medium py-2 px-4 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Contact Email: </span>
                  <span>{billing.billing_details.email || 'Not provided'}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {showPaymentModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50">
          <div className="flex items-center justify-center min-h-screen p-4">
            <div className="bg-white rounded-lg shadow-lg max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  {window.isUpdateMode ? 'Update Payment Method' : 'Add Payment Method'}
                </h3>
                <button
                  onClick={closePaymentMethodModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M6 18L18 6M6 6l12 12"
                    ></path>
                  </svg>
                </button>
              </div>
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-4">
                  {window.isUpdateMode
                    ? 'Enter new card details to replace your current payment method.'
                    : window.pendingPlanSelection
                      ? `Add a payment method to continue with the ${window.pendingPlanSelection} plan.`
                      : 'Enter your card details to add a new payment method.'}
                </p>
                <div id="card-element" className="p-3 border border-gray-300 rounded-lg"></div>
                <div id="card-errors" className="mt-2 text-red-600 text-sm" role="alert"></div>
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={handleAddPaymentMethod}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  {window.isUpdateMode
                    ? 'Update Payment Method'
                    : window.pendingPlanSelection
                      ? `Add Payment Method & Select ${window.pendingPlanSelection}`
                      : 'Add Payment Method'}
                </button>
                <button
                  onClick={closePaymentMethodModal}
                  className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
