'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertTriangle, TrendingDown, DollarSign, Activity, XCircle, CheckCircle } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [alertsRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/alerts?limit=20`),
        axios.get(`${API_URL}/dashboard/stats`)
      ]);
      setAlerts(alertsRes.data);
      setStats(statsRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  const handleAlertClick = async (alert: Alert) => {
    try {
      // Fetch full alert details with strategy
      const response = await axios.get(`${API_URL}/alerts/${alert.alert_id}`);
      setSelectedAlert(response.data);
    } catch (error) {
      console.error('Error fetching alert details:', error);
    }
  };

  const handleAction = async (alertId: string, promoId: string, actionType: string) => {
    try {
      await axios.post(`${API_URL}/actions`, {
        alert_id: alertId,
        promo_id: promoId,
        action_type: actionType,
        performed_by: 'manager'
      });
      
      fetchData();
      setSelectedAlert(null);
    } catch (error) {
      console.error('Error executing action:', error);
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
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-green-500 animate-pulse" />
              <span className="text-sm text-gray-600">Live</span>
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
          <div className="px-6 py-4 border-b">
            <h2 className="text-xl font-semibold text-gray-900">Cannibalization Alerts</h2>
          </div>
          
          <div className="divide-y">
            {alerts.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
                <p>No active alerts. All promotions performing as expected!</p>
              </div>
            ) : (
              alerts.map((alert) => (
                <div key={alert.alert_id} className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                     onClick={() => handleAlertClick(alert)}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{alert.product_name}</h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getSeverityColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          alert.status === 'resolved' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {alert.status}
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
                          <p className="text-sm font-medium text-red-600">{alert.loss_percentage}%</p>
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
        </div>
      </main>

      {selectedAlert && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="text-xl font-semibold text-gray-900">Alert Details & AI Strategy</h3>
              <button onClick={() => setSelectedAlert(null)} className="text-gray-400 hover:text-gray-600">
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            
            <div className="px-6 py-4">
              <div className="mb-6">
                <h4 className="text-lg font-semibold text-gray-900 mb-2">{selectedAlert.product_name}</h4>
                <p className="text-sm text-gray-600">Promo ID: {selectedAlert.promo_id}</p>
              </div>

              {selectedAlert.strategy && (
                <div className="space-y-6">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h5 className="font-semibold text-blue-900 mb-2">AI Explanation</h5>
                    <p className="text-sm text-blue-800">{selectedAlert.strategy.explanation}</p>
                  </div>

                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h5 className="font-semibold text-green-900 mb-3">Recommended Action</h5>
                    <div className="space-y-2">
                      <p className="font-medium text-green-800">{selectedAlert.strategy.primary_recommendation.action}</p>
                      <p className="text-sm text-green-700">{selectedAlert.strategy.primary_recommendation.details}</p>
                      <p className="text-xs text-green-600">Expected: {selectedAlert.strategy.primary_recommendation.expected_impact}</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h5 className="font-semibold text-gray-900">Alternative Strategies</h5>
                    {selectedAlert.strategy.alternatives.map((alt, idx) => (
                      <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="font-medium text-gray-800 text-sm">{alt.action}</p>
                        <p className="text-xs text-gray-600 mt-1">{alt.details}</p>
                      </div>
                    ))}
                  </div>

                  {selectedAlert.status !== 'action_taken' && selectedAlert.status !== 'resolved' && (
                    <div className="flex gap-3 pt-4 border-t">
                      <button
                        onClick={() => handleAction(selectedAlert.alert_id, selectedAlert.promo_id, 'stop_promotion')}
                        className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700 transition"
                      >
                        Stop Promotion
                      </button>
                      <button
                        onClick={() => handleAction(selectedAlert.alert_id, selectedAlert.promo_id, 'adjust_price')}
                        className="flex-1 bg-yellow-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-yellow-700 transition"
                      >
                        Adjust Price
                      </button>
                      <button
                        onClick={() => setSelectedAlert(null)}
                        className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg font-medium hover:bg-gray-400 transition"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
