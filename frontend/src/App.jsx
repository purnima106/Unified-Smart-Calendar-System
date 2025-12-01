import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { authAPI } from './services/api';
import { ThemeProvider } from './contexts/ThemeContext';
import LoginPage from './components/LoginPage';
import Dashboard from './components/Dashboard';
import CalendarView from './components/CalendarView';
import ConflictsView from './components/ConflictsView';
import FreeSlotsView from './components/FreeSlotsView';
import SummaryView from './components/SummaryView';
import Navbar from './components/Navbar';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [userConnections, setUserConnections] = useState({
    google: { connected: false },
    microsoft: { connected: false }
  });

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await authAPI.checkAuth();
      if (response.data.authenticated) {
        setUser(response.data.user);
        setUserConnections({
          google: { connected: response.data.user.google_connected },
          microsoft: { connected: response.data.user.microsoft_connected }
        });
      } else {
        setUser(null);
        setUserConnections({
          google: { connected: false },
          microsoft: { connected: false }
        });
      }
    } catch (error) {
      console.log('Auth check error:', error);
      setUser(null);
      setUserConnections({
        google: { connected: false },
        microsoft: { connected: false }
      });
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await authAPI.logout();
      setUser(null);
      setUserConnections({
        google: { connected: false },
        microsoft: { connected: false }
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const updateUserConnections = async () => {
    try {
      // Only call if user is authenticated
      if (user) {
        const response = await authAPI.getUserConnections();
        setUserConnections(response.data);
      }
    } catch (error) {
      // Silently handle 401 errors (user not authenticated)
      if (error.response?.status !== 401) {
        console.error('Error updating connections:', error);
      }
    }
  };

  if (loading) {
    return (
      <ThemeProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-black flex items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </ThemeProvider>
    );
  }

  if (!user) {
    return (
      <ThemeProvider>
        <Router>
          <Routes>
            <Route 
              path="/login" 
              element={
                <LoginPage 
                  onLoginSuccess={checkAuthStatus}
                  onConnectionsUpdate={updateUserConnections}
                />
              } 
            />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Router>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider>
      <Router>
        <div className="min-h-screen bg-gray-50 dark:bg-black transition-colors duration-200">
          <Navbar 
            user={user} 
            connections={userConnections}
            onLogout={handleLogout}
            onConnectionsUpdate={updateUserConnections}
          />
          
          <main className="container mx-auto px-4 py-8">
            <Routes>
              <Route 
                path="/" 
                element={
                  <Dashboard 
                    user={user}
                    connections={userConnections}
                    onConnectionsUpdate={updateUserConnections}
                  />
                } 
              />
              <Route 
                path="/calendar" 
                element={
                  <CalendarView 
                    user={user}
                    connections={userConnections}
                  />
                } 
              />
              <Route 
                path="/conflicts" 
                element={
                  <ConflictsView 
                    user={user}
                  />
                } 
              />
              <Route 
                path="/free-slots" 
                element={
                  <FreeSlotsView 
                    user={user}
                  />
                } 
              />
              <Route 
                path="/summary" 
                element={
                  <SummaryView 
                    user={user}
                  />
                } 
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
