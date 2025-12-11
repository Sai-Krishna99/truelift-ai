'use client';

import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { AlertTriangle, TrendingDown, DollarSign, Activity, XCircle, CheckCircle, Filter, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = API_URL.replace('http', 'ws') + '/ws';

interface Alert {
  alert_id: string;
  promo_id: string;
  product_name: string;
  actual_sales: number;
  predicted_sales: number;
  loss_percentage: number;
  loss_amount: number;
  severity: string;
  status: string;
  alert_timestamp: string;
  strategy?: {
    explanation: string;
    primary_recommendation: {
      action: string;
      details: string;
      expected_impact: string;
    };
    alternatives: Array<{
      action: string;
      details: string;
      expected_impact: string;
    }>;
    confidence_score: number;
  };
}

interface DashboardStats {
  total_alerts: number;
  pending_alerts: number;
  resolved_alerts: number;
  total_loss: number;
  avg_loss_percentage: number;
  active_promotions: number;
  total_actions: number;
}

export default function Home() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [showFilters, setShowFilters] = useState(false);
  const [actionResult, setActionResult] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const [recentActions, setRecentActions] = useState<any[]>([]);
  const [showActionHistory, setShowActionHistory] = useState(false);

  useEffect(() => {
    fetchData();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('WebSocket message:', message);

        if (message.type === 'action_taken' || message.type === 'new_alert') {
          fetchData();
          if (message.type === 'action_taken') {
            const { alert_id, status } = message.data || {};
            setAlerts(prev => prev.map(a => a.alert_id === alert_id ? { ...a, status: status || 'resolved' } : a));
            setSelectedAlert(prev => prev && prev.alert_id === alert_id ? { ...prev, status: status || 'resolved' } : prev);
          }
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };

      ws.onclose = () => {
        console.log('WebSocket closed, reconnecting...');
        setWsConnected(false);
        setTimeout(connectWebSocket, 5000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket connection error:', error);
      setWsConnected(false);
    }
  };

  const fetchData = async () => {
    try {
      const [alertsRes, statsRes, actionsRes] = await Promise.all([
        axios.get(`${API_URL}/alerts?limit=50`),
        axios.get(`${API_URL}/dashboard/stats`),
        axios.get(`${API_URL}/actions/recent?limit=10`)
      ]);
      setAlerts(alertsRes.data);
      setStats(statsRes.data);
      setRecentActions(actionsRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  const handleAlertClick = async (alert: Alert) => {
    try {
      const response = await axios.get(`${API_URL}/alerts/${alert.alert_id}`);
      setSelectedAlert(response.data);
    } catch (error) {
      console.error('Error fetching alert details:', error);
    }
  };

  const handleAction = async (alertId: string, promoId: string, actionType: string) => {
    setActionLoading(true);
    setActionResult(null);

    try {
      const response = await axios.post(`${API_URL}/actions`, {
        alert_id: alertId,
        promo_id: promoId,
        action_type: actionType,
        performed_by: 'manager'
      });

      setSelectedAlert(prev => prev ? { ...prev, status: 'resolved' } : prev);
      setActionResult({
        message: `Action "${actionType}" executed successfully! ${response.data.message}`,
        type: 'success'
      });

      fetchData();

    } catch (error: any) {
      console.error('Error executing action:', error);
      setActionResult({
        message: `Failed to execute action: ${error.response?.data?.detail || error.message}`,
        type: 'error'
      });
    } finally {
      setActionLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-300';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'action_taken':
        return 'bg-amber-100 text-amber-800 border border-amber-200';
      case 'resolved':
        return 'bg-green-100 text-green-800 border border-green-200';
      case 'strategy_generated':
        return 'bg-blue-100 text-blue-800 border border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border border-gray-200';
    }
  };

  const filteredAlerts = alerts.filter(alert => {
    if (statusFilter !== 'all' && alert.status !== statusFilter) return false;
    if (severityFilter !== 'all' && alert.severity !== severityFilter) return false;
    return true;
  });

  const totalPages = Math.ceil(filteredAlerts.length / itemsPerPage);
  const paginatedAlerts = filteredAlerts.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading TrueLift Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">TrueLift Dashboard</h1>
              <p className="text-sm text-gray-500 mt-1">Real-time Cannibalization Detection & Response</p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={fetchData}
                className="flex items-center gap-2 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition"
              >
                <RefreshCw className="w-4 h-4" />
                <span className="text-sm font-medium">Refresh</span>
              </button>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600">{wsConnected ? 'Live' : 'Offline'}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-red-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Pending Alerts</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stats?.pending_alerts || 0}</p>
              </div>
              <AlertTriangle className="w-10 h-10 text-red-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Loss</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  ${(stats?.total_loss || 0).toFixed(2)}
                </p>
              </div>
              <DollarSign className="w-10 h-10 text-yellow-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg Loss %</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {(stats?.avg_loss_percentage || 0).toFixed(1)}%
                </p>
              </div>
              <TrendingDown className="w-10 h-10 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Promos</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stats?.active_promotions || 0}</p>
              </div>
              <Activity className="w-10 h-10 text-green-500" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Cannibalization Alerts</h2>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
            >
              <Filter className="w-4 h-4" />
              <span className="text-sm font-medium">Filters</span>
            </button>
          </div>

          {showFilters && (
            <div className="px-6 py-4 bg-gray-50 border-b">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                  >
                    <option value="all">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="strategy_generated">Strategy Generated</option>
                    <option value="action_taken">Action Taken</option>
                    <option value="resolved">Resolved</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Severity</label>
                  <select
                    value={severityFilter}
                    onChange={(e) => { setSeverityFilter(e.target.value); setCurrentPage(1); }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
                  >
                    <option value="all">All Severities</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={() => {
                      setStatusFilter('all');
                      setSeverityFilter('all');
                      setCurrentPage(1);
                    }}
                    className="w-full px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                  >
                    Clear Filters
                  </button>
                </div>
              </div>
              <div className="mt-3 text-sm text-gray-600">
                Showing {paginatedAlerts.length} of {filteredAlerts.length} alerts
              </div>
            </div>
          )}

          <div className="divide-y">
            {paginatedAlerts.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
                <p>No alerts match your filters. All promotions performing as expected!</p>
              </div>
            ) : (
              paginatedAlerts.map((alert) => (
                <div key={alert.alert_id} className="px-6 py-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => handleAlertClick(alert)}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{alert.product_name}</h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getSeverityColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                        <span className={`px-2 py-1 text-xs font-medium rounded ${alert.status === 'resolved' ? 'bg-green-100 text-green-800' :
                          alert.status === 'strategy_generated' ? 'bg-blue-100 text-blue-800' :
                          alert.status === 'action_taken' ? 'bg-amber-100 text-amber-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                          {alert.status.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
                        <div>
                          <p className="text-xs text-gray-500">Predicted Sales</p>
                          <p className="text-sm font-medium text-gray-900">{alert.predicted_sales} units</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Actual Sales</p>
                          <p className="text-sm font-medium text-gray-900">{alert.actual_sales} units</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Loss %</p>
                          <p className="text-sm font-medium text-red-600">{alert.loss_percentage.toFixed(1)}%</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Revenue Loss</p>
                          <p className="text-sm font-medium text-red-600">${alert.loss_amount.toFixed(2)}</p>
                        </div>
                      </div>

                      <p className="text-xs text-gray-500 mt-3">
                        {new Date(alert.alert_timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {filteredAlerts.length > itemsPerPage && (
            <div className="px-6 py-4 border-t flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="flex items-center gap-1 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="flex items-center gap-1 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {selectedAlert && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h3 className="text-xl font-semibold text-gray-900">Alert Details & AI Strategy</h3>
                <span className={`px-3 py-1 text-xs font-semibold rounded-full ${getStatusBadge(selectedAlert.status)}`}>
                  {selectedAlert.status.replace('_', ' ').toUpperCase()}
                </span>
              </div>
              <button onClick={() => setSelectedAlert(null)} className="text-gray-400 hover:text-gray-600">
                <XCircle className="w-6 h-6" />
              </button>
            </div>

            <div className="px-6 py-4">
              <div className="mb-6">
                <h4 className="text-lg font-semibold text-gray-900 mb-2">{selectedAlert.product_name}</h4>
                <p className="text-sm text-gray-600">Promo ID: {selectedAlert.promo_id}</p>
              </div>

              {actionResult && (
                <div className={`mb-6 p-4 rounded-lg ${actionResult.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                  <p className={`text-sm font-medium ${actionResult.type === 'success' ? 'text-green-800' : 'text-red-800'}`}>
                    {actionResult.message}
                  </p>
                </div>
              )}

              {selectedAlert.strategy && (
                <div className="space-y-6">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h5 className="font-semibold text-blue-900 mb-2">🤖 AI Explanation</h5>
                    <p className="text-sm text-blue-800">{selectedAlert.strategy.explanation}</p>
                  </div>

                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h5 className="font-semibold text-green-900 mb-3">✅ Recommended Action</h5>
                    <div className="space-y-2">
                      <p className="font-medium text-green-800">{selectedAlert.strategy.primary_recommendation.action}</p>
                      <p className="text-sm text-green-700">{selectedAlert.strategy.primary_recommendation.details}</p>
                      <p className="text-xs text-green-600">💡 Expected: {selectedAlert.strategy.primary_recommendation.expected_impact}</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h5 className="font-semibold text-gray-900">🔄 Alternative Strategies</h5>
                    {selectedAlert.strategy.alternatives.map((alt, idx) => (
                      <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="font-medium text-gray-800 text-sm">{alt.action}</p>
                        <p className="text-xs text-gray-600 mt-1">{alt.details}</p>
                      </div>
                    ))}
                      </div>

                  {selectedAlert.status === 'pending' || selectedAlert.status === 'strategy_generated' ? (
                    <div className="pt-4 border-t">
                      <h5 className="font-semibold text-gray-900 mb-3">⚡ Execute Action</h5>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <button
                          onClick={() => handleAction(selectedAlert.alert_id, selectedAlert.promo_id, 'stop_promotion')}
                          disabled={actionLoading}
                          className="flex items-center justify-center gap-2 bg-red-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                          Stop Promotion
                        </button>
                        <button
                          onClick={() => handleAction(selectedAlert.alert_id, selectedAlert.promo_id, 'adjust_price')}
                          disabled={actionLoading}
                          className="flex items-center justify-center gap-2 bg-yellow-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-yellow-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <DollarSign className="w-4 h-4" />}
                          Adjust Price
                        </button>
                        <button
                          onClick={() => setSelectedAlert(null)}
                          disabled={actionLoading}
                          className="flex items-center justify-center gap-2 bg-gray-300 text-gray-700 px-4 py-3 rounded-lg font-medium hover:bg-gray-400 transition"
                        >
                          Dismiss
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mt-3 text-center">
                        Actions will be published to Kafka and processed by the feedback loop system
                      </p>
                    </div>
                  ) : selectedAlert.status === 'action_taken' ? (
                    <div className="pt-4 border-t">
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-center">
                        <div className="flex items-center justify-center gap-2 text-amber-800 font-medium">
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Action recorded — processing</span>
                        </div>
                        <p className="text-xs text-amber-700 mt-2">
                          Feedback loop will update effectiveness once enough events arrive.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="pt-4 border-t">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                        <CheckCircle className="w-8 h-8 text-green-600 mx-auto mb-2" />
                        <p className="text-sm font-medium text-green-800">This alert has been resolved</p>
                      </div>
                    </div>
                  )}

                  <div className="pt-6 border-t mt-6">
                    <div className="flex items-center justify-between mb-3">
                      <h5 className="font-semibold text-gray-900">📜 Recent Actions</h5>
                      <button
                        onClick={() => setShowActionHistory(!showActionHistory)}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        {showActionHistory ? 'Hide' : 'Show'}
                      </button>
                    </div>
                    {showActionHistory && (
                      <div className="space-y-2">
                        {recentActions
                          .filter(a => a.alert_id === selectedAlert.alert_id || a.promo_id === selectedAlert.promo_id)
                          .slice(0, 5)
                          .map((action, idx) => (
                            <div key={`${action.action_id}-${idx}`} className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-gray-800">{action.action_type.replace('_', ' ')}</span>
                                <span className="text-xs text-gray-500">
                                  {new Date(action.action_timestamp || action.timestamp).toLocaleString()}
                                </span>
                              </div>
                              <div className="text-xs text-gray-600 mt-1">
                                {action.product_name ? `${action.product_name} (${action.promo_id})` : action.promo_id}
                              </div>
                            </div>
                          ))}
                        {recentActions.filter(a => a.alert_id === selectedAlert.alert_id || a.promo_id === selectedAlert.promo_id).length === 0 && (
                          <p className="text-sm text-gray-600">No actions recorded for this alert yet.</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
