import { Link, useLocation } from 'react-router-dom';
import { Calendar, AlertTriangle, Clock, BarChart3, LogOut, User, Moon, Sun } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const Navbar = ({ user, connections, onLogout, onConnectionsUpdate }) => {
  const location = useLocation();
  const { darkMode, toggleDarkMode } = useTheme();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/calendar', label: 'Calendar', icon: Calendar },
    { path: '/conflicts', label: 'Conflicts', icon: AlertTriangle },
    { path: '/free-slots', label: 'Free Slots', icon: Clock },
    { path: '/summary', label: 'Summary', icon: BarChart3 },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="bg-white dark:bg-black dark:text-white shadow-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50 backdrop-blur-sm bg-white/95 dark:bg-black/95">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Brand */}
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2 group">
              <div className="w-9 h-9 bg-gradient-to-br from-purple-600 to-purple-700 rounded-lg flex items-center justify-center shadow-md group-hover:shadow-lg transition-shadow duration-200">
                <Calendar className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                CalendarSync
              </span>
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                    isActive(item.path)
                      ? 'bg-purple-600 dark:bg-purple-700 text-white shadow-md'
                      : 'text-gray-600 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/30'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {/* Calendar Connections Status */}
            <div className="hidden sm:flex items-center space-x-2">
              {connections.google.connected && (
                <span className="badge-google dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-700">Google</span>
              )}
              {/* Microsoft temporarily disabled */}
              {/* {connections.microsoft.connected && (
                <span className="badge-microsoft">Microsoft</span>
              )} */}
            </div>

            {/* User Profile */}
            <div className="relative group">
              <button className="flex items-center space-x-2 text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors duration-200">
                <div className="w-9 h-9 bg-gradient-to-br from-purple-500 to-purple-600 dark:from-purple-600 dark:to-purple-700 rounded-full flex items-center justify-center shadow-md">
                  <User className="w-5 h-5 text-white" />
                </div>
                <span className="hidden sm:block font-medium">{user.name}</span>
              </button>

              {/* Dropdown Menu */}
              <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-black dark:text-white rounded-xl shadow-lg border border-gray-100 dark:border-gray-800 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 overflow-hidden">
                <div className="py-2">
                  <div className="px-4 py-3 bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-900/30 dark:to-purple-800/30 border-b border-gray-100 dark:border-gray-800">
                    <div className="font-semibold text-gray-900 dark:text-white">{user.name}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{user.email}</div>
                  </div>
                  
                  {/* Dark Mode Toggle */}
                  <button
                    onClick={toggleDarkMode}
                    className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-gray-700 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors duration-200"
                  >
                    <div className="flex items-center space-x-2">
                      {darkMode ? (
                        <Sun className="w-4 h-4" />
                      ) : (
                        <Moon className="w-4 h-4" />
                      )}
                      <span>{darkMode ? 'Light Mode' : 'Dark Mode'}</span>
                    </div>
                    <div className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${darkMode ? 'bg-purple-600' : 'bg-gray-300'}`}>
                      <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-md transform transition-transform duration-200 ${darkMode ? 'translate-x-5' : 'translate-x-0'}`}></div>
                    </div>
                  </button>
                  
                  <div className="border-t border-gray-100 dark:border-gray-800 my-1"></div>
                  
                  <button
                    onClick={onLogout}
                    className="w-full flex items-center space-x-2 px-4 py-2.5 text-sm text-gray-700 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors duration-200"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden py-4 border-t border-gray-200 dark:border-gray-800">
          <div className="flex flex-col space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 ${
                    isActive(item.path)
                      ? 'bg-purple-600 dark:bg-purple-700 text-white shadow-md'
                      : 'text-gray-600 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/30'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
