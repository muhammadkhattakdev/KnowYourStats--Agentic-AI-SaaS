import React, { createContext, useContext, useState, useEffect } from 'react';
import Request from '../utils/Request';

const AppContext = createContext();

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [currentChat, setCurrentChat] = useState(null);
  const [notifications, setNotifications] = useState([]);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = () => {
      const token = localStorage.getItem('access_token');
      const savedUser = localStorage.getItem('user');

      if (token && savedUser) {
        setUser(JSON.parse(savedUser));
        setIsAuthenticated(true);
        
        // Fetch fresh user data
        fetchUserProfile();
      }
      
      setLoading(false);
    };

    initAuth();
  }, []);

  // Fetch user profile
  const fetchUserProfile = async () => {
    try {
      const response = await Request.get('/auth/profile/');
      if (response.success !== false) {
        setUser(response);
        localStorage.setItem('user', JSON.stringify(response));
      }
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
    }
  };

  // Login
  const login = async (email, password) => {
    try {
      const response = await Request.post('/auth/login/', { email, password });
      
      if (response.success) {
        const { user, tokens } = response;
        
        // Save to localStorage
        localStorage.setItem('access_token', tokens.access);
        localStorage.setItem('refresh_token', tokens.refresh);
        localStorage.setItem('user', JSON.stringify(user));
        
        // Update state
        setUser(user);
        setIsAuthenticated(true);
        
        return { success: true };
      }
      
      return { success: false, message: response.message };
    } catch (error) {
      return {
        success: false,
        message: error.response?.data?.message || 'Login failed',
      };
    }
  };

  // Register
  const register = async (userData) => {
    try {
      const response = await Request.post('/auth/register/', userData);
      
      if (response.success) {
        const { user, tokens } = response;
        
        // Save to localStorage
        localStorage.setItem('access_token', tokens.access);
        localStorage.setItem('refresh_token', tokens.refresh);
        localStorage.setItem('user', JSON.stringify(user));
        
        // Update state
        setUser(user);
        setIsAuthenticated(true);
        
        return { success: true };
      }
      
      return { success: false, message: response.message };
    } catch (error) {
      return {
        success: false,
        message: error.response?.data?.message || 'Registration failed',
      };
    }
  };

  // Logout
  const logout = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await Request.post('/auth/logout/', { refresh_token: refreshToken });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear localStorage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      
      // Clear state
      setUser(null);
      setIsAuthenticated(false);
      setCurrentChat(null);
    }
  };

  // Add notification
  const addNotification = (notification) => {
    const id = Date.now();
    const newNotification = {
      id,
      ...notification,
      timestamp: new Date(),
    };
    
    setNotifications((prev) => [...prev, newNotification]);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      removeNotification(id);
    }, 5000);
    
    return id;
  };

  // Remove notification
  const removeNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  // Show success notification
  const showSuccess = (message) => {
    addNotification({
      type: 'success',
      message,
    });
  };

  // Show error notification
  const showError = (message) => {
    addNotification({
      type: 'error',
      message,
    });
  };

  // Show info notification
  const showInfo = (message) => {
    addNotification({
      type: 'info',
      message,
    });
  };

  const value = {
    user,
    setUser,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
    fetchUserProfile,
    currentChat,
    setCurrentChat,
    notifications,
    addNotification,
    removeNotification,
    showSuccess,
    showError,
    showInfo,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export default AppContext;