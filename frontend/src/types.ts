// SSE event types from the backend
export interface ProgressEvent {
  type: 'node_start' | 'node_end' | 'complete' | 'error';
  node?: string;
  state?: Record<string, unknown>;
  signal?: string;
  message?: string;
}

// Analysis request payload sent to POST /api/analyze/{run_id}
export interface AnalyzeRequest {
  ticker: string;
  date: string;
  analysts: string[];
  enable_options: boolean;
  llm_provider: string;
  deep_think_llm: string;
  quick_think_llm: string;
}

// Full analysis result from the "complete" SSE event
export interface AnalysisResult {
  market_report: string;
  technical_report: string;
  sentiment_report: string;
  news_report: string;
  fundamentals_report: string;
  investment_plan: string;
  trader_investment_plan: string;
  final_trade_decision: string;
  // Options fields (empty string when options disabled)
  volatility_report: string;
  options_flow_report: string;
  options_strategy: string;
  options_legs: string;
  options_pricing_report: string;
  greeks_report: string;
  signal?: string;
}

// State for useReducer in useAnalysis hook
export type AnalysisStatus = 'idle' | 'running' | 'done' | 'error';

export interface AnalysisState {
  status: AnalysisStatus;
  currentNode: string | null;
  completedNodes: string[];
  result: AnalysisResult | null;
  errorMsg: string | null;
}

// Known agent node names for the progress stepper
export const EQUITY_NODES = [
  'Market Analyst',
  'Technical Analyst',
  'Social Analyst',
  'News Analyst',
  'Fundamentals Analyst',
] as const;

export const OPTIONS_NODES = [
  'Options - Volatility Analyst',
  'Options - Flow Analyst',
  'Options - Strategy Selector',
  'Options - Strike/Expiry',
  'Options - Pricing Agent',
  'Options - Legs Builder',
  'Options - Greeks Monitor',
] as const;

export const RESEARCH_NODES = [
  'Bull Researcher',
  'Bear Researcher',
  'Research Manager',
] as const;

export const TRADING_NODES = ['Trader'] as const;

export const RISK_NODES = [
  'Aggressive Analyst',
  'Conservative Analyst',
  'Neutral Analyst',
  'Portfolio Manager',
] as const;

// Report tab definitions
export interface ReportTab {
  id: string;
  label: string;
  stateKey: keyof AnalysisResult;
  optionsOnly?: boolean;
}

export const REPORT_TABS: ReportTab[] = [
  { id: 'market', label: 'Market', stateKey: 'market_report' },
  { id: 'technical', label: 'Technical', stateKey: 'technical_report' },
  { id: 'social', label: 'Social', stateKey: 'sentiment_report' },
  { id: 'news', label: 'News', stateKey: 'news_report' },
  { id: 'fundamentals', label: 'Fundamentals', stateKey: 'fundamentals_report' },
  { id: 'volatility', label: 'Volatility', stateKey: 'volatility_report', optionsOnly: true },
  { id: 'flow', label: 'Flow', stateKey: 'options_flow_report', optionsOnly: true },
  { id: 'strategy', label: 'Strategy', stateKey: 'options_strategy', optionsOnly: true },
  { id: 'legs', label: 'Legs/Order', stateKey: 'options_legs', optionsOnly: true },
  { id: 'pricing', label: 'Pricing', stateKey: 'options_pricing_report', optionsOnly: true },
  { id: 'greeks', label: 'Greeks', stateKey: 'greeks_report', optionsOnly: true },
  { id: 'debate', label: 'Debate History', stateKey: 'investment_plan' },
  { id: 'decision', label: 'Final Decision', stateKey: 'final_trade_decision' },
];

// --- Trade types (Phase 14) ---

export type OrderStatus = 'idle' | 'submitted' | 'filled' | 'rejected' | 'error';

export interface TradeStatus {
  status: OrderStatus;
  fill_price: number | null;
  fill_time: string | null;
  close_time: string | null;         // REQUIRED: Plan 03 reads this for exit marker
  rejection_reason: string | null;
  order_id: string | null;
  close_price: number | null;
  pnl_pct: number | null;
  outcome: string | null;
}

export interface TradeRequest {
  ticker: string;
  direction: string;
  trade_type: 'equity' | 'option';
  strategy_name?: string;
  analysis_date?: string;
  options_legs?: string;
  strike?: number;
  expiry?: string;
  contract_type?: string;
}

export interface TradeResponse {
  id: number;
  order_id: string;
  status: string;
  ticker: string;
  direction: string;
  trade_type: string;
  quantity: number;
  fill_price: number | null;
  fill_time: string | null;
}

// --- Chart types (Phase 13) ---

export type ChartTimeframe = '1D' | '1M' | '3M' | '6M' | '1Y';

export interface AlpacaBar {
  t: string;  // ISO timestamp
  o: number;  // open
  h: number;  // high
  l: number;  // low
  c: number;  // close
  v: number;  // volume
  n: number;  // number of trades
  vw: number; // volume-weighted average price
}

export interface ChartOverlay {
  ticker: string;
  analysis_date: string;
  signal: string;
  entry_price: number | null;
  take_profit: number | null;
  stop_loss: number | null;
  expiry_date: string | null;
  strategy_name: string | null;
  options_legs: string;
  final_trade_decision: string;
}

export const TIMEFRAME_CONFIG: Record<ChartTimeframe, { alpacaTimeframe: string; daysBack: number; label: string }> = {
  '1D': { alpacaTimeframe: '15Min', daysBack: 0, label: '1D' },
  '1M': { alpacaTimeframe: '1Day', daysBack: 30, label: '1M' },
  '3M': { alpacaTimeframe: '1Day', daysBack: 90, label: '3M' },
  '6M': { alpacaTimeframe: '1Day', daysBack: 180, label: '6M' },
  '1Y': { alpacaTimeframe: '1Day', daysBack: 365, label: '1Y' },
};

// --- Screener types ---

export interface ScreenerPick {
  ticker: string;
  score: number;
  rationale: string;
  confidence: number;
  key_metrics: Record<string, number | undefined>;
  sector: string | null;
  market_cap: string | null;
}

export type ScreenerStatus = 'idle' | 'loading' | 'done' | 'error';

export interface ScreenerState {
  status: ScreenerStatus;
  picks: ScreenerPick[];
  screenedAt: string | null;
  errorMsg: string | null;
}

// --- Scoring types (Phase 15) ---

export interface ScoreSummary {
  win_rate: number;
  expectancy: number;
  avg_winner: number;
  avg_loser: number;
  profit_factor: number;
  total_trades: number;
  total_closed: number;
  disclaimer: string | null;
}

export interface CalibrationBucket {
  bucket_label: string;
  bucket_min: number;
  bucket_max: number;
  actual_win_rate: number;
  trade_count: number;
}

export interface CalibrationData {
  buckets: CalibrationBucket[];
  total_scored: number;
  message: string | null;
}

// --- Dashboard types (Phase 16) ---

export interface DashboardSummary {
  total_trades: number;
  total_closed: number;
  win_rate: number;
  expectancy: number;
  avg_winner: number;
  avg_loser: number;
  profit_factor: number;
  aggregate_pnl: number;
  disclaimer: string | null;
}

export interface DashboardTradeItem {
  id: number;
  ticker: string;
  direction: string;
  trade_type: string;
  entry_date: string | null;
  outcome: string | null;
  pnl_pct: number | null;
  strategy_name: string | null;
  is_legacy: boolean;
}

export interface DashboardTradesData {
  trades: DashboardTradeItem[];
  total: number;
}

export interface EquityCurvePoint {
  time: string;
  value: number;
}

export interface EquityCurveData {
  points: EquityCurvePoint[];
  total_trades: number;
}
