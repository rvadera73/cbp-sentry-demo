import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, Loader, Info, BarChart3 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TabNavigation, TabConfig } from '../components/TabNavigation';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';
type TabType = 'Model Weights' | 'Screening Rules' | 'Configuration' | 'Performance Metrics';

interface ModelWeights {
  DOCUMENTATION_RISK: number;
  CORRIDOR_RISK: number;
  COMMODITY_RISK: number;
  ROUTING_RISK: number;
  PARTY_RISK: number;
  PATTERN_RISK: number;
  TIME_SENSITIVITY: number;
}

interface ModelConfig {
  calibration_multiplier: number;
  auto_hold_threshold: number;
  altana_trigger_threshold?: number;
}

interface ModelMetrics {
  auc_roc: number;
  precision: number;
  recall: number;
  f1_score: number;
  total_validated: number;
  threshold: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
  last_run: string;
  model_version: string;
}

const FACTOR_META: Record<string, { label: string; color: string }> = {
  DOCUMENTATION_RISK: { label: 'Documentation Risk (ISF, Element 9, Manifest Completeness)', color: 'text-[#D83933]' },
  CORRIDOR_RISK: { label: 'Corridor Risk (Country-of-Origin Risk Pair)', color: 'text-amber-600' },
  COMMODITY_RISK: { label: 'Commodity Risk (Tariff Rate, Export Control, UFLPA)', color: 'text-orange-600' },
  ROUTING_RISK: { label: 'Routing Risk (AIS Dwell, Port Selection, Vessel Flag)', color: 'text-blue-600' },
  PARTY_RISK: { label: 'Party Risk (Shipper Age, Prior Violations, OFAC, Ownership)', color: 'text-purple-600' },
  PATTERN_RISK: { label: 'Pattern Anomaly (Pricing Anomaly, Weight Anomaly, Trade Frequency)', color: 'text-[#112E51]' },
  TIME_SENSITIVITY: { label: 'Time Sensitivity (Pre-Tariff Timing, Seasonal Anomaly)', color: 'text-slate-600' },
};

// Typical high-risk factor scores for preview calculation
const SAMPLE_SCORES: Record<string, number> = {
  DOCUMENTATION_RISK: 8.5,
  CORRIDOR_RISK: 7.0,
  COMMODITY_RISK: 6.5,
  ROUTING_RISK: 7.5,
  PARTY_RISK: 6.0,
  PATTERN_RISK: 5.0,
  TIME_SENSITIVITY: 4.0,
};

const CORRIDOR_MULTIPLIERS = [
  { corridor: 'CN→US', multiplier: 1.30 },
  { corridor: 'VN→US', multiplier: 1.15 },
  { corridor: 'MY→US', multiplier: 1.10 },
  { corridor: 'CA→US', multiplier: 0.95 },
  { corridor: 'SG→US', multiplier: 0.90 },
];

export default function V2AITuningPage() {
  const [activeTab, setActiveTab] = useState<TabType>('Model Weights');
  const [weights, setWeights] = useState<ModelWeights>({
    DOCUMENTATION_RISK: 25,
    CORRIDOR_RISK: 20,
    COMMODITY_RISK: 15,
    ROUTING_RISK: 15,
    PARTY_RISK: 15,
    PATTERN_RISK: 10,
    TIME_SENSITIVITY: 10,
  });

  const [config, setConfig] = useState<ModelConfig>({
    calibration_multiplier: 1.2,
    auto_hold_threshold: 80,
    altana_trigger_threshold: 80,
  });

  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [rules, setRules] = useState({
    'W-121': true,
    'W-822': true,
    'UFLPA-301': true,
  });

  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        const [weightsResp, metricsResp] = await Promise.all([
          fetch('/api/model/weights'),
          fetch('/api/model/metrics'),
        ]);

        if (weightsResp.ok) {
          const data = await weightsResp.json();
          setWeights(data.weights);
          setConfig(data.config);
        }

        if (metricsResp.ok) {
          const data = await metricsResp.json();
          setMetrics(data);
        }
      } catch (err) {
        console.error('Error loading model data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // Calculate total weight
  const totalWeight = Object.values(weights).reduce((s, v) => s + v, 0);
  const isWeightValid = Math.abs(totalWeight - 100) < 0.5;

  // Calculate score preview
  const previewScore = Math.min(
    Object.entries(weights).reduce((sum, [factor, weight]) => {
      const score = SAMPLE_SCORES[factor] ?? 5.0;
      return sum + (score * weight) / 100;
    }, 0) * config.calibration_multiplier,
    100
  );

  // Save weights and rules
  const handleSave = async () => {
    if (!isWeightValid) {
      setErrorMessage('Weights must sum to 100%');
      return;
    }

    setSaveStatus('saving');
    setErrorMessage(null);

    try {
      // Save weights
      const weightsResp = await fetch('/api/model/weights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weights, config }),
      });

      if (!weightsResp.ok) {
        const error = await weightsResp.json();
        throw new Error(error.detail || 'Failed to save weights');
      }

      // Save rules
      const rulesResp = await fetch('/api/rules/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          h1_weight: weights.DOCUMENTATION_RISK,
          h2_weight: weights.ROUTING_RISK,
          h3_weight: weights.CORRIDOR_RISK,
          rules: {
            'W-121': rules['W-121'],
            'W-822': rules['W-822'],
            'UFLPA-301': rules['UFLPA-301'],
          },
          analyst_id: 'CBP-98522',
          analyst_name: 'Rav J. D.',
          environment: 'PROD',
        }),
      });

      if (!rulesResp.ok) {
        const error = await rulesResp.json();
        throw new Error(error.detail || error.message || 'Failed to save rules');
      }

      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err) {
      setSaveStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Error saving configuration');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-5 bg-[#F7F9FC]">
        <Loader className="w-6 h-6 animate-spin text-[#005EA2]" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC]">
      {/* Page Title Header */}
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-4 shadow-sm">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-xl font-bold text-[#0B1F33]">AI Model Configuration & Performance</h1>
            <p className="text-xs text-slate-600 mt-1">
              Adjust factor weights, review validation metrics, and manage screening rules
            </p>
          </div>
          <div className="text-right text-[9px] font-mono text-slate-500">
            Model v{metrics?.model_version} • Last trained: {metrics?.last_run.split('T')[0]}
          </div>
        </div>
      </div>

      {/* Summary Card - Key Metrics */}
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-4 shadow-sm">
        <div className="grid grid-cols-4 gap-6">
          <div>
            <p className="text-[9px] font-bold text-slate-500 uppercase mb-1">Model Status</p>
            <p className="text-sm font-bold text-[#0B1F33]">
              {saveStatus === 'saved' ? '✓ Active' : saveStatus === 'saving' ? 'Updating...' : 'Ready'}
            </p>
          </div>
          <div>
            <p className="text-[9px] font-bold text-slate-500 uppercase mb-1">Total Weight</p>
            <p className={`text-lg font-bold font-mono ${isWeightValid ? 'text-[#07A41E]' : 'text-[#D83933]'}`}>
              {totalWeight}%
            </p>
          </div>
          <div>
            <p className="text-[9px] font-bold text-slate-500 uppercase mb-1">Performance (F1)</p>
            <p className="text-sm font-bold text-[#0B1F33]">{metrics?.f1_score.toFixed(3) || 'N/A'}</p>
          </div>
          <div>
            <p className="text-[9px] font-bold text-slate-500 uppercase mb-1">Rules Active</p>
            <p className="text-sm font-bold text-[#0B1F33]">{Object.values(rules).filter(Boolean).length} of 3</p>
          </div>
        </div>
      </div>

      {/* Tab Navigation Component - Horizontal */}
      <TabNavigation
        tabs={[
          { id: 'Model Weights', label: 'Model Weights' },
          { id: 'Screening Rules', label: 'Screening Rules' },
          { id: 'Configuration', label: 'Configuration' },
          { id: 'Performance Metrics', label: 'Performance Metrics' },
        ]}
        activeTab={activeTab}
        onTabChange={(tabId) => setActiveTab(tabId as TabType)}
        orientation="horizontal"
      />

      {/* Error Banner */}
      {errorMessage && (
        <div className="mx-5 mt-4 flex items-start space-x-3 p-4 bg-red-50 border border-red-200 rounded-sm">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-bold text-red-900">Error</p>
            <p className="text-xs text-red-700">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Content Pane - Full Width */}
      <div className="flex-1 overflow-y-auto bg-[#F7F9FC] p-6">
        <div className="max-w-4xl">
          {activeTab === 'Model Weights' && (
            <ModelWeightsTab
              weights={weights}
              setWeights={setWeights}
              config={config}
              totalWeight={totalWeight}
              isWeightValid={isWeightValid}
              previewScore={previewScore}
            />
          )}

          {activeTab === 'Screening Rules' && (
            <ScreeningRulesTab rules={rules} setRules={setRules} corridors={CORRIDOR_MULTIPLIERS} />
          )}

          {activeTab === 'Configuration' && (
            <ConfigurationTab config={config} setConfig={setConfig} />
          )}

          {activeTab === 'Performance Metrics' && <PerformanceMetricsTab metrics={metrics} />}
        </div>
      </div>

      {/* Action Bar - Apply Changes Button */}
      <div className="bg-white border-t border-[#D0D7DE] px-6 py-4 shadow-sm">
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={!isWeightValid || saveStatus === 'saving'}
            className={`px-6 py-2 font-bold rounded-sm cursor-pointer transition-all flex items-center space-x-2 text-[10px] ${
              !isWeightValid
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : saveStatus === 'saved'
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : saveStatus === 'error'
                    ? 'bg-red-600 hover:bg-red-700 text-white'
                    : 'bg-[#005EA2] hover:bg-[#0076D6] text-white disabled:opacity-50'
            }`}
          >
            {saveStatus === 'saving' && <Loader className="w-4 h-4 animate-spin" />}
            {saveStatus === 'saved' && <CheckCircle className="w-4 h-4" />}
            {saveStatus === 'error' && <AlertCircle className="w-4 h-4" />}
            <span>
              {saveStatus === 'saving'
                ? 'Saving Changes...'
                : saveStatus === 'saved'
                  ? 'Changes Saved ✓'
                  : 'Apply Changes'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

// MODEL WEIGHTS TAB
function ModelWeightsTab({
  weights,
  setWeights,
  config,
  totalWeight,
  isWeightValid,
  previewScore,
}: any) {
  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-bold text-[#0B1F33] mb-1">Risk Factor Weights</h2>
        <p className="text-xs text-slate-600 mb-4">
          Adjust the relative importance of each risk factor. Total weight must equal 100%.
        </p>

        <div className="space-y-5">
          {(Object.entries(weights) as Array<[string, number]>).map(([factor, value]) => {
            const numValue = value as number;
            const meta = FACTOR_META[factor as keyof typeof FACTOR_META];
            return (
              <div key={factor} className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <label className={`text-xs font-bold uppercase tracking-wide font-mono ${meta.color}`}>
                      {meta.label}
                    </label>
                  </div>
                  <span className={`text-lg font-bold font-mono ${meta.color} whitespace-nowrap ml-2`}>
                    {numValue.toFixed(1)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="50"
                  step="0.1"
                  value={numValue}
                  onChange={(e) => setWeights({ ...weights, [factor]: parseFloat(e.target.value) })}
                  className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
                />
              </div>
            );
          })}
        </div>

        {/* Total Weight Indicator */}
        <div className="mt-6 p-4 rounded-sm bg-slate-50 border border-slate-200">
          <div className="flex justify-between items-center">
            <span className="text-xs font-bold text-[#112E51] uppercase font-mono">Total Weight</span>
            <span
              className={`text-lg font-bold font-mono ${
                isWeightValid ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {totalWeight.toFixed(1)}%
            </span>
          </div>
          {!isWeightValid && <p className="text-[9px] text-red-600 mt-2">⚠ Weights must sum to 100%</p>}
        </div>

        {/* Score Impact Preview */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-sm">
          <div className="text-[10px] font-bold text-[#0B1F33] uppercase tracking-wide font-mono mb-3">
            Score Impact Preview
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-xs text-slate-600">Adjusted Score (typical high-risk):</span>
            <span className={`text-2xl font-bold font-mono ${previewScore >= 80 ? 'text-[#D83933]' : 'text-[#FFBE2E]'}`}>
              {previewScore.toFixed(1)}
            </span>
            <span className="text-xs text-slate-600">/100</span>
          </div>
          <p className="text-[9px] text-slate-600 mt-2">
            Based on sample component scores with {config.calibration_multiplier.toFixed(2)}x calibration
          </p>
        </div>
      </div>
    </div>
  );
}

// SCREENING RULES TAB
function ScreeningRulesTab({ rules, setRules, corridors }: any) {
  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-bold text-[#0B1F33] mb-4">Screening Rules</h2>

        <div className="grid grid-cols-2 gap-6">
          {/* Rules */}
          <div className="bg-white rounded-sm border border-[#D0D7DE] p-4 space-y-3">
            <h3 className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide font-mono">
              Mandatory Rules
            </h3>
            {[
              { id: 'W-121', label: 'W-121', desc: 'UNVERIFIED RELEGATED IMPORTER' },
              { id: 'W-822', label: 'W-822', desc: 'AIS SILENT PATTERN ANOMALY' },
              { id: 'UFLPA-301', label: 'UFLPA-301', desc: 'AD/CVD RECLASSIFICATION' },
            ].map((rule) => (
              <label
                key={rule.id}
                className={`flex items-start space-x-3 p-3 rounded cursor-pointer transition-colors border ${
                  rules[rule.id as keyof typeof rules]
                    ? 'border-blue-200 bg-blue-50'
                    : 'border-transparent hover:bg-slate-50'
                }`}
              >
                <input
                  type="checkbox"
                  checked={rules[rule.id as keyof typeof rules]}
                  onChange={(e) => setRules({ ...rules, [rule.id]: e.target.checked })}
                  className="w-4 h-4 border border-gray-300 rounded mt-0.5 cursor-pointer"
                />
                <div className="text-xs flex-1">
                  <p className="font-bold text-[#0B1F33]">{rule.label}</p>
                  <p className="text-[#5C5C5C] text-[9px]">{rule.desc}</p>
                </div>
              </label>
            ))}
          </div>

          {/* Corridors */}
          <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
            <h3 className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide font-mono mb-4">
              Corridor Risk Multipliers
            </h3>
            <div className="space-y-3">
              {corridors.map((c: any) => (
                <div key={c.corridor} className="flex justify-between items-center p-2 bg-slate-50 rounded">
                  <span className="font-mono text-sm text-slate-700">{c.corridor}</span>
                  <span className="font-bold text-amber-600 font-mono text-lg">{c.multiplier.toFixed(2)}x</span>
                </div>
              ))}
            </div>
            <p className="text-[9px] text-slate-500 mt-4">
              These multipliers are applied to base scores based on origin-destination corridor risk.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// CONFIGURATION TAB
function ConfigurationTab({ config, setConfig }: any) {
  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-bold text-[#0B1F33] mb-4">Model Settings</h2>

        <div className="grid grid-cols-2 gap-6">
          {/* Calibration Multiplier */}
          <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
            <div className="flex justify-between items-center mb-4">
              <label className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide font-mono">
                Calibration Multiplier
              </label>
              <span className="text-xl font-bold text-blue-600 font-mono">
                {config.calibration_multiplier.toFixed(2)}x
              </span>
            </div>
            <input
              type="range"
              min="1.0"
              max="2.0"
              step="0.05"
              value={config.calibration_multiplier}
              onChange={(e) => setConfig({ ...config, calibration_multiplier: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
            />
            <p className="text-[9px] text-slate-600 mt-3">
              Applied to all component scores before final ranking. Higher values increase overall risk scores.
            </p>
          </div>

          {/* Auto-Hold Threshold */}
          <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
            <div className="flex justify-between items-center mb-4">
              <label className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide font-mono">
                Auto-Hold Threshold
              </label>
              <span
                className={`text-xl font-bold font-mono ${
                  config.auto_hold_threshold >= 80 ? 'text-[#D83933]' : 'text-slate-600'
                }`}
              >
                {config.auto_hold_threshold}
              </span>
            </div>
            <input
              type="range"
              min="60"
              max="95"
              step="1"
              value={config.auto_hold_threshold}
              onChange={(e) => setConfig({ ...config, auto_hold_threshold: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
            />
            <p className="text-[9px] text-slate-600 mt-3">
              Shipments with scores ≥ this value are automatically flagged for review.
            </p>
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-sm flex items-start space-x-3">
          <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
          <p className="text-[9px] text-blue-800">
            Configuration changes apply immediately to all future shipment evaluations. Previously scored shipments retain their original scores.
          </p>
        </div>
      </div>
    </div>
  );
}

// PERFORMANCE METRICS TAB
function PerformanceMetricsTab({ metrics }: any) {
  if (!metrics) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500">
        No metrics data available
      </div>
    );
  }

  const chartData = [
    { name: 'AUC-ROC', value: metrics.auc_roc },
    { name: 'Precision', value: metrics.precision },
    { name: 'Recall', value: metrics.recall },
    { name: 'F1 Score', value: metrics.f1_score },
  ];

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-bold text-[#0B1F33] mb-1">Model Performance</h2>
        <p className="text-xs text-slate-600 mb-6">
          Live metrics from the latest model validation run
        </p>

        <div className="grid grid-cols-2 gap-6">
          {/* Metrics Table */}
          <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
            <h3 className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide font-mono mb-4">
              Validation Metrics
            </h3>
            <div className="space-y-3">
              {[
                { label: 'AUC-ROC', value: metrics.auc_roc, target: 0.75 },
                { label: 'Precision', value: metrics.precision, target: 0.70 },
                { label: 'Recall', value: metrics.recall, target: 0.65 },
                { label: 'F1 Score', value: metrics.f1_score, target: 0.67 },
              ].map((metric) => {
                const passed = metric.value >= metric.target;
                return (
                  <div key={metric.label} className="flex justify-between items-center p-2 bg-slate-50 rounded">
                    <div>
                      <p className="text-[10px] font-bold text-slate-700 uppercase font-mono">
                        {metric.label}
                      </p>
                      <p className="text-[9px] text-slate-500">Target: {metric.target.toFixed(2)}</p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-lg font-bold text-slate-900 font-mono">
                        {metric.value.toFixed(4)}
                      </span>
                      <span
                        className={`px-2 py-1 rounded text-[9px] font-bold ${
                          passed
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {passed ? 'PASS' : 'FAIL'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Confusion Matrix */}
          <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
            <h3 className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide font-mono mb-4">
              Confusion Matrix
            </h3>
            <div className="grid grid-cols-2 gap-2 mb-4">
              <div className="bg-green-100 p-3 rounded text-center">
                <div className="text-[9px] font-bold text-green-900">True Positives</div>
                <div className="text-2xl font-bold text-green-700 font-mono">
                  {metrics.true_positives.toLocaleString()}
                </div>
              </div>
              <div className="bg-red-100 p-3 rounded text-center">
                <div className="text-[9px] font-bold text-red-900">False Positives</div>
                <div className="text-2xl font-bold text-red-700 font-mono">
                  {metrics.false_positives.toLocaleString()}
                </div>
              </div>
              <div className="bg-green-100 p-3 rounded text-center">
                <div className="text-[9px] font-bold text-green-900">True Negatives</div>
                <div className="text-2xl font-bold text-green-700 font-mono">
                  {metrics.true_negatives.toLocaleString()}
                </div>
              </div>
              <div className="bg-red-100 p-3 rounded text-center">
                <div className="text-[9px] font-bold text-red-900">False Negatives</div>
                <div className="text-2xl font-bold text-red-700 font-mono">
                  {metrics.false_negatives.toLocaleString()}
                </div>
              </div>
            </div>

            <div className="text-[9px] text-slate-600 space-y-1 pt-4 border-t border-slate-200">
              <p>
                <strong>Total Validated:</strong> {metrics.total_validated.toLocaleString()} shipments
              </p>
              <p>
                <strong>Decision Threshold:</strong> Risk Score ≥ {metrics.threshold}
              </p>
            </div>
          </div>
        </div>

        {/* Performance Chart */}
        <div className="mt-6 bg-white rounded-sm border border-[#D0D7DE] p-5">
          <h3 className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide font-mono mb-4">
            Metric Performance
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 9 }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 9 }} />
              <Tooltip formatter={(value: any) => typeof value === 'number' ? (value as number).toFixed(4) : String(value)} />
              <Bar dataKey="value" fill="#005EA2" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
