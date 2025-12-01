import { useState, useEffect, useRef } from 'react';
import { Calendar, Mail, Shield, Zap, Users, Clock, ArrowRight, AlertTriangle, RefreshCw, BarChart3, Link2, CheckCircle2, DollarSign, Headphones } from 'lucide-react';
import { authAPI } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const LoginPage = ({ onLoginSuccess, onConnectionsUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [backendStatus, setBackendStatus] = useState('checking');

  // Check backend status on component mount
  useEffect(() => {
    checkBackendStatus();
  }, []);

  const featuresRef = useRef(null);
  const pricingRef = useRef(null);
  const supportRef = useRef(null);

  const scrollToSection = (ref) => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const checkBackendStatus = async () => {
    try {
      const response = await fetch('http://localhost:5000/health');
      const data = await response.json();
      console.log('Backend health check:', data);
      setBackendStatus('healthy');
    } catch (error) {
      console.error('Backend health check failed:', error);
      setBackendStatus('unhealthy');
      setError('Backend server is not responding. Please ensure the backend is running.');
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await authAPI.googleLogin();
      window.location.href = response.data.auth_url;
    } catch (error) {
      setError('Failed to initiate Google login. Please try again.');
      console.error('Google login error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMicrosoftLogin = async () => {
    setLoading(true);
    setError('');
    
    try {
      console.log('Initiating Microsoft login...');
      const response = await authAPI.microsoftLogin();
      console.log('Microsoft login response:', response.data);
      
      if (response.data.auth_url) {
        window.location.href = response.data.auth_url;
      } else {
        throw new Error('No auth URL received from server');
      }
    } catch (error) {
      console.error('Microsoft login error:', error);
      const errorMessage = error.response?.data?.error || error.message || 'Failed to initiate Microsoft login. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Show only key features on landing page
  const keyFeatures = [
    {
      icon: Calendar,
      title: 'Unified View',
      description: 'All your calendars in one place'
    },
    {
      icon: Shield,
      title: 'Smart Detection',
      description: 'Automatically find conflicts'
    },
    {
      icon: Zap,
      title: 'Real-time Sync',
      description: 'Stay synchronized automatically'
    }
  ];

  const loginOptions = [
    {
      name: 'Google',
      icon: (
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
      ),
      handler: handleGoogleLogin,
      available: true
    },
    {
      name: 'Microsoft',
      icon: (
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path fill="#00A4EF" d="M11.5 2.75h-8a.75.75 0 0 0-.75.75v8c0 .414.336.75.75.75h8a.75.75 0 0 0 .75-.75v-8a.75.75 0 0 0-.75-.75zm-8-1.5a1.5 1.5 0 0 0-1.5 1.5v8a1.5 1.5 0 0 0 1.5 1.5h8a1.5 1.5 0 0 0 1.5-1.5v-8a1.5 1.5 0 0 0-1.5-1.5h-8z"/>
          <path fill="#7FBA00" d="M20.5 2.75h-8a.75.75 0 0 0-.75.75v8c0 .414.336.75.75.75h8a.75.75 0 0 0 .75-.75v-8a.75.75 0 0 0-.75-.75zm-8-1.5a1.5 1.5 0 0 0-1.5 1.5v8a1.5 1.5 0 0 0 1.5 1.5h8a1.5 1.5 0 0 0 1.5-1.5v-8a1.5 1.5 0 0 0-1.5-1.5h-8z"/>
          <path fill="#FFB900" d="M11.5 12.75h-8a.75.75 0 0 0-.75.75v8c0 .414.336.75.75.75h8a.75.75 0 0 0 .75-.75v-8a.75.75 0 0 0-.75-.75zm-8-1.5a1.5 1.5 0 0 0-1.5 1.5v8a1.5 1.5 0 0 0 1.5 1.5h8a1.5 1.5 0 0 0 1.5-1.5v-8a1.5 1.5 0 0 0-1.5-1.5h-8z"/>
          <path fill="#F25022" d="M20.5 12.75h-8a.75.75 0 0 0-.75.75v8c0 .414.336.75.75.75h8a.75.75 0 0 0 .75-.75v-8a.75.75 0 0 0-.75-.75zm-8-1.5a1.5 1.5 0 0 0-1.5 1.5v8a1.5 1.5 0 0 0 1.5 1.5h8a1.5 1.5 0 0 0 1.5-1.5v-8a1.5 1.5 0 0 0-1.5-1.5h-8z"/>
        </svg>
      ),
      handler: handleMicrosoftLogin,
      available: true  // Microsoft is now enabled
    },
    {
      name: 'Zoho',
      icon: (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#C8202F">
          <path d="M3 3h18v2.5H3V3zm0 4.5h18v2.5H3V7.5zm0 4.5h18v2.5H3V12zm0 4.5h18V19H3v-2.5z"/>
        </svg>
      ),
      handler: () => alert('Zoho integration coming soon!'),
      available: false
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-purple-50 dark:from-black dark:via-black dark:to-black">
      {/* Simple Header */}
      <div className="border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-black/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex justify-between items-center py-5">
            <div className="flex items-center space-x-3 group">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-purple-700 rounded-lg flex items-center justify-center shadow-md group-hover:shadow-lg transition-shadow duration-200">
                <Calendar className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-gray-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">CalendarSync</span>
            </div>
            <div className="hidden md:flex items-center space-x-8 text-sm font-medium text-gray-600 dark:text-white">
              <span 
                onClick={() => scrollToSection(featuresRef)} 
                className="hover:text-purple-600 dark:hover:text-purple-400 cursor-pointer transition-colors"
              >
                Features
              </span>
              <span 
                onClick={() => scrollToSection(pricingRef)} 
                className="hover:text-purple-600 dark:hover:text-purple-400 cursor-pointer transition-colors"
              >
                Pricing
              </span>
              <span 
                onClick={() => scrollToSection(supportRef)} 
                className="hover:text-purple-600 dark:hover:text-purple-400 cursor-pointer transition-colors"
              >
                Support
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-12 lg:py-20">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left Side - Content */}
          <div className="space-y-8">
            <div className="space-y-5">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 dark:text-white leading-tight">
                Connect your calendars.
                <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-purple-700 dark:from-purple-400 dark:to-purple-500">Stay organized.</span>
              </h1>
              <p className="text-lg md:text-xl text-gray-600 dark:text-gray-300 leading-relaxed max-w-lg">
                Seamlessly integrate Google Calendar and Microsoft Outlook. 
                Detect conflicts, find free time, and keep everything in sync.
              </p>
            </div>

            {/* Key Features - Compact Grid */}
            <div className="grid grid-cols-3 gap-6 pt-6">
              {keyFeatures.map((feature, index) => {
                const Icon = feature.icon;
                return (
                  <div key={index} className="text-center group cursor-default">
                    <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 dark:from-purple-600 dark:to-purple-700 rounded-2xl flex items-center justify-center shadow-lg group-hover:shadow-xl transition-all duration-300 group-hover:scale-110 group-hover:-translate-y-1 mx-auto mb-4">
                      <Icon className="w-7 h-7 text-white" />
                    </div>
                    <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-1.5">{feature.title}</h3>
                    <p className="text-xs text-gray-600 dark:text-gray-400 leading-tight px-1">{feature.description}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Side - Login */}
          <div className="bg-white dark:bg-black dark:text-white rounded-3xl shadow-2xl border border-gray-100 dark:border-gray-800 p-8 lg:p-10 relative overflow-hidden">
            {/* Decorative gradient background */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-purple-100 to-transparent dark:from-purple-900/20 dark:to-transparent rounded-full blur-3xl -mr-32 -mt-32"></div>
            
            <div className="relative space-y-6">
              <div className="text-center">
                <h2 className="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white mb-2">Get started</h2>
                <p className="text-gray-600 dark:text-gray-300 text-sm">
                  Connect your calendar accounts to begin
                </p>
              </div>

              {backendStatus === 'unhealthy' && (
                <div className="bg-purple-50 dark:bg-purple-900/30 border-l-4 border-purple-500 dark:border-purple-400 rounded-lg p-4 text-left">
                  <div className="flex items-start">
                    <AlertTriangle className="w-5 h-5 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
                    <p className="text-purple-800 dark:text-purple-200 text-sm ml-3">
                      Backend server is not responding. Please ensure the backend is running.
                    </p>
                  </div>
                </div>
              )}
              
              {error && (
                <div className="bg-purple-50 dark:bg-purple-900/30 border-l-4 border-purple-500 dark:border-purple-400 rounded-lg p-4 text-left">
                  <div className="flex items-start">
                    <AlertTriangle className="w-5 h-5 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
                    <p className="text-purple-800 dark:text-purple-200 text-sm ml-3">{error}</p>
                  </div>
                </div>
              )}

              {/* Login Options - Show only available ones prominently */}
              <div className="space-y-3">
                {loginOptions.filter(opt => opt.available).map((option, index) => {
                  const isGoogle = option.name === 'Google';
                  const isMicrosoft = option.name === 'Microsoft';
                  
                  return (
                    <button
                      key={index}
                      onClick={option.handler}
                      disabled={loading}
                      className={`w-full flex items-center justify-center space-x-3 py-4 px-5 rounded-xl font-semibold text-sm transition-all duration-200 active:scale-[0.98] ${
                        isGoogle 
                          ? 'bg-purple-600 hover:bg-purple-700 text-white shadow-md hover:shadow-lg' 
                          : isMicrosoft 
                          ? 'bg-purple-600 hover:bg-purple-700 text-white shadow-md hover:shadow-lg'
                          : 'border-2 border-gray-200 dark:border-gray-700 hover:border-purple-400 dark:hover:border-purple-500 hover:shadow-md bg-white dark:bg-black text-gray-700 dark:text-white hover:bg-purple-50 dark:hover:bg-purple-900/30'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                        {option.icon}
                      </div>
                      <span>Continue with {option.name}</span>
                    </button>
                  );
                })}
              </div>

              {/* Coming Soon Options - Collapsed */}
              {loginOptions.filter(opt => !opt.available).length > 0 && (
                <div className="pt-6 border-t border-gray-100 dark:border-gray-800">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-3 text-center uppercase tracking-wider">Coming soon</p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {loginOptions.filter(opt => !opt.available).map((option, index) => (
                      <button
                        key={index}
                        onClick={option.handler}
                        disabled={true}
                        className="flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 text-gray-400 dark:text-gray-500 cursor-not-allowed text-sm transition-opacity hover:opacity-80"
                      >
                        <div className="w-4 h-4 flex items-center justify-center">
                          {option.icon}
                        </div>
                        <span className="font-medium">{option.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="text-xs text-gray-500 dark:text-gray-400 pt-6 text-center leading-relaxed border-t border-gray-100 dark:border-gray-800">
                By signing in, you agree to our{' '}
                <a href="#" className="text-purple-600 dark:text-purple-400 hover:underline font-medium">Terms of Service</a>
                {' '}and{' '}
                <a href="#" className="text-purple-600 dark:text-purple-400 hover:underline font-medium">Privacy Policy</a>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <section ref={featuresRef} className="max-w-7xl mx-auto px-6 py-20 lg:py-28">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
            Powerful Features
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Everything you need to manage your calendars across platforms
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[
            {
              icon: Calendar,
              title: 'Unified Calendar View',
              description: 'View all your Google and Microsoft calendar events in one beautiful, unified interface with color-coded events by provider.'
            },
            {
              icon: Link2,
              title: 'Multi-Account Support',
              description: 'Connect multiple Google and Microsoft accounts simultaneously. Manage all your calendars from one place.'
            },
            {
              icon: AlertTriangle,
              title: 'Conflict Detection',
              description: 'Automatically detect overlapping meetings across all your calendars. Get detailed conflict reports and resolution suggestions.'
            },
            {
              icon: Clock,
              title: 'Free Slots Discovery',
              description: 'Find available meeting times across all your calendars. Discover optimal scheduling windows with customizable search parameters.'
            },
            {
              icon: RefreshCw,
              title: 'Bidirectional Sync',
              description: 'Mirror meetings between calendars automatically. Keep all your calendars in sync without duplicate notifications or emails.'
            },
            {
              icon: Zap,
              title: 'Real-time Synchronization',
              description: 'Stay up-to-date with automatic real-time sync. Your calendars are always current across all platforms.'
            },
            {
              icon: BarChart3,
              title: 'Calendar Analytics',
              description: 'Get insights into your calendar usage with productivity scoring, meeting time analysis, and conflict rate tracking.'
            },
            {
              icon: Shield,
              title: 'Secure OAuth Integration',
              description: 'Enterprise-grade security with OAuth 2.0 authentication. Your data is encrypted and tokens are securely managed.'
            },
            {
              icon: CheckCircle2,
              title: 'Smart Scheduling',
              description: 'AI-powered meeting time suggestions based on your availability. Find the perfect time for meetings automatically.'
            }
          ].map((feature, index) => {
            const Icon = feature.icon;
            return (
              <div
                key={index}
                className="bg-white dark:bg-black border border-gray-200 dark:border-gray-800 rounded-2xl p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
              >
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 dark:from-purple-600 dark:to-purple-700 rounded-xl flex items-center justify-center mb-4">
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Pricing Section */}
      <section ref={pricingRef} className="bg-gradient-to-br from-purple-50 to-white dark:from-black dark:to-gray-900 py-20 lg:py-28">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              One plan. All features. No hidden fees.
            </p>
          </div>

          <div className="bg-white dark:bg-black rounded-3xl shadow-2xl border border-gray-200 dark:border-gray-800 p-8 lg:p-12 max-w-md mx-auto">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 dark:from-purple-600 dark:to-purple-700 rounded-2xl mb-4">
                <DollarSign className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Pro Plan
              </h3>
              <div className="flex items-baseline justify-center gap-2 mb-4">
                <span className="text-5xl font-bold text-gray-900 dark:text-white">$20</span>
                <span className="text-gray-600 dark:text-gray-400">/month</span>
              </div>
              <p className="text-gray-600 dark:text-gray-300">
                Everything you need to manage all your calendars
              </p>
            </div>

            <ul className="space-y-4 mb-8">
              {[
                'Unlimited calendar connections',
                'Multi-account support (Google & Microsoft)',
                'Real-time bidirectional sync',
                'Advanced conflict detection',
                'Free slots discovery',
                'Calendar analytics & insights',
                'Smart scheduling suggestions',
                'Priority support',
                'Secure OAuth integration',
                'No credit card required for trial'
              ].map((feature, index) => (
                <li key={index} className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                </li>
              ))}
            </ul>

            <button className="w-full bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl">
              Get Started
            </button>
          </div>
        </div>
      </section>

      {/* Support Section */}
      <section ref={supportRef} className="max-w-4xl mx-auto px-6 py-20 lg:py-28">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
            Need Help?
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-300">
            We're here to assist you with any questions or issues
          </p>
        </div>

        <div className="bg-white dark:bg-black border border-gray-200 dark:border-gray-800 rounded-3xl shadow-xl p-8 lg:p-12">
          <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-purple-600 dark:from-purple-600 dark:to-purple-700 rounded-2xl flex items-center justify-center flex-shrink-0">
              <Headphones className="w-10 h-10 text-white" />
            </div>
            <div className="flex-1 text-center md:text-left">
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Contact Support
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6 leading-relaxed">
                Have a question or need assistance? Reach out to our support team and we'll get back to you as soon as possible.
              </p>
              <div className="space-y-3">
                <div className="flex items-center justify-center md:justify-start gap-3">
                  <Users className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  <span className="text-gray-900 dark:text-white font-semibold">Purnima Nahata</span>
                </div>
                <div className="flex items-center justify-center md:justify-start gap-3">
                  <Mail className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  <a 
                    href="mailto:p.nahata@cloudextel.com" 
                    className="text-purple-600 dark:text-purple-400 hover:underline font-medium"
                  >
                    p.nahata@cloudextel.com
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-6 py-8 border-t border-gray-200 dark:border-gray-800">
        <div className="text-center">
          <p className="text-xs text-gray-400 dark:text-gray-500 font-light">
            Project by Viral Shah and Team
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LoginPage;
