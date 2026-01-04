import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  MessageSquare,
  FileText,
  Database,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  User,
  MessageCircle,
  BarChart3,
  Sparkles,
} from "lucide-react";
import { useAppContext } from "../../context/Context";
import "./Sidebar.css";

const Sidebar = () => {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const { user, logout } = useAppContext();

  const menuItems = [
    {
      path: "/dashboard",
      icon: <MessageSquare size={20} />,
      label: "Chat",
      exact: true,
    },
    {
      path: "/dashboard/chats",
      icon: <MessageCircle size={20} />,
      label: "All Chats",
    },
    {
      path: "/dashboard/reports",
      icon: <FileText size={20} />,
      label: "Reports",
    },
    {
      path: "/dashboard/datasets",
      icon: <Database size={20} />,
      label: "Datasets",
    },
    {
      path: "/dashboard/analytics",
      icon: <BarChart3 size={20} />,
      label: "Analytics",
    },
  ];

  const isActive = (path, exact = false) => {
    if (exact) {
      return location.pathname === path;
    }
    return location.pathname.startsWith(path);
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = "/signin";
  };

  return (
    <aside className={`dashboard-sidebar ${collapsed ? "collapsed" : ""}`}>
      {/* Logo & Toggle */}
      <div className="sidebar-header">
        <Link to="/dashboard" className="sidebar-logo">
          <div className="logo-icon">
            <Sparkles size={24} />
          </div>
          {!collapsed && <span className="logo-text">KnowYourStats</span>}
        </Link>
        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      {/* User Info */}
      <div className="sidebar-user">
        <div className="user-avatar">
          <User size={20} />
        </div>
        {!collapsed && (
          <div className="user-info">
            <div className="user-name">{user?.full_name || user?.email}</div>
            <div className="user-email">{user?.email}</div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-item ${
              isActive(item.path, item.exact) ? "active" : ""
            }`}
            title={collapsed ? item.label : ""}
          >
            <span className="nav-icon">{item.icon}</span>
            {!collapsed && <span className="nav-label">{item.label}</span>}
            {isActive(item.path, item.exact) && (
              <span className="active-indicator" />
            )}
          </Link>
        ))}
      </nav>

      {/* Bottom Actions */}
      <div className="sidebar-footer">
        <Link
          to="/dashboard/settings"
          className={`nav-item ${
            isActive("/dashboard/settings") ? "active" : ""
          }`}
          title={collapsed ? "Settings" : ""}
        >
          <span className="nav-icon">
            <Settings size={20} />
          </span>
          {!collapsed && <span className="nav-label">Settings</span>}
        </Link>

        <button
          className="nav-item logout-btn"
          onClick={handleLogout}
          title={collapsed ? "Logout" : ""}
        >
          <span className="nav-icon">
            <LogOut size={20} />
          </span>
          {!collapsed && <span className="nav-label">Logout</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
