import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Settings, Activity, TrendingUp, TrendingDown, Wallet, Target, Zap, AlertTriangle, Bitcoin, Swords, Clock, ArrowUpRight, ArrowDownRight, HelpCircle, Eye, Brain, PiggyBank, Fish, Bell, Lock, ShieldAlert, Timer, CheckCircle, Ghost, FileText, GitBranch } from 'lucide-react';
import { useTrinityStore } from '../../stores/trinityStore';

import { ANGEL_BASE_URL, getTrinityHeaders } from '../../services/angelService';
import { ActionButtons, PanelLayout, ResponsiveGrid, AdaptiveCard, OptionToggle } from '../ui/PanelKit';
import { useUnsavedChanges } from '../../hooks/useUnsavedChanges';
import { useRef } from 'react';

/**
 * SOTA 2026: TraderPanel - Two-column Layout with Tooltips & Full i18n
 */

// Variable labels & help (i18n)
const VARIABLE_INFO = {
    en: {
        rsi_oversold: { label: 'RSI Oversold', help: 'When price dropped too much and may bounce. Lower = waits for bigger dip.' },
        rsi_overbought: { label: 'RSI Overbought', help: 'When price rose too much and may drop. Higher = waits for bigger rally.' },
        rsi_period: { label: 'RSI Period', help: 'Number of candles for RSI calculation. Higher = slower but more reliable.' },
        stop_loss: { label: 'Stop Loss', help: 'Loss limit before auto-sell. e.g. -0.02 = sell if 2% loss.' },
        tp1: { label: 'Target 1', help: 'First profit target. e.g. 0.013 = sell portion at +1.3%.' },
        tp2: { label: 'Target 2', help: 'Second profit target. e.g. 0.016 = sell rest at +1.6%.' },
        min_confidence: { label: 'Min Confidence', help: 'Minimum score to buy. Higher = more selective, fewer trades.' },
        max_positions: { label: 'Max Positions', help: 'Maximum number of cryptos held simultaneously.' },
        trend_ema: { label: 'Trend EMA', help: 'Moving average for trend detection. Higher = long-term trend.' },
        min_trade: { label: 'Min Trade (€)', help: 'Minimum purchase amount in euros.' },
        max_trade: { label: 'Max Trade (€)', help: 'Maximum purchase amount in euros.' },
        rsi_composite_limit: { label: 'RSI Composite', help: 'Combined multi-timeframe RSI limit. Lower = more cautious.' },
    },
    fr: {
        rsi_oversold: { label: 'RSI Survente', help: 'Quand le prix a trop baissé et peut remonter. Plus bas = attend une grosse baisse.' },
        rsi_overbought: { label: 'RSI Surachat', help: 'Quand le prix a trop monté et peut baisser. Plus haut = attend une grosse hausse.' },
        rsi_period: { label: 'Période RSI', help: 'Nombre de bougies pour calculer le RSI. Plus grand = plus lent mais plus fiable.' },
        stop_loss: { label: 'Stop Loss', help: 'Limite de perte avant vente auto. Ex: -0.02 = vend si perte de 2%.' },
        tp1: { label: 'Objectif 1', help: 'Premier objectif de gain. Ex: 0.013 = vend une partie à +1.3%.' },
        tp2: { label: 'Objectif 2', help: 'Second objectif de gain. Ex: 0.016 = vend le reste à +1.6%.' },
        min_confidence: { label: 'Confiance Min', help: 'Score minimum pour acheter. Plus haut = plus sélectif, moins de trades.' },
        max_positions: { label: 'Positions Max', help: 'Nombre maximum de cryptos détenues en même temps.' },
        trend_ema: { label: 'EMA Tendance', help: 'Moyenne mobile pour détecter la tendance. Plus grand = tendance long terme.' },
        min_trade: { label: 'Trade Min (€)', help: 'Montant minimum par achat en euros.' },
        max_trade: { label: 'Trade Max (€)', help: 'Montant maximum par achat en euros.' },
        rsi_composite_limit: { label: 'RSI Composite', help: 'Limite RSI combinée multi-timeframes. Plus bas = plus prudent.' },
    }
};

const DICT = {
    en: {
        market: 'MARKET',
        regime: 'Regime',
        btc24h: 'BTC 24h',
        sentiment: 'Sentiment',
        cycle: 'Cycle',
        portfolio: 'PORTFOLIO',
        total: 'Total',
        active: 'Active',
        cash: 'Cash',
        positions: 'Positions',
        btcReserve: 'BTC RESERVE',
        earn: 'Earn',
        value: 'Value',
        piggybank: 'Piggybank',
        combat: 'COMBAT',
        winRate: 'Win Rate',
        score: 'Score',
        pnl24h: 'PnL 24h',
        pnlTotal: 'PnL Total',
        transactions: 'RECENT TRANSACTIONS',
        noTx: 'No transactions',
        mode: 'MODE',
        level: 'LEVEL',
        variables: 'VARIABLES',
        options: 'OPTIONS',
        iaAdjust: 'AI adjusts dynamically',
        noVar: 'No variables',
        refresh: 'REFRESH',
        refreshing: 'REFRESHING...',
        apply: 'APPLY',
        applying: 'APPLYING...',
        offline: 'Cache Mode (Relay Offline)',
        loading: 'Loading...',
        circuitBreaker: 'Circuit Breaker Active',
        levelPassive: 'PASSIVE',
        levelNormal: 'NORMAL',
        levelAggressive: 'AGGRESSIVE',
        modeSniper: { label: 'SNIPER', help: 'Waits for very high confidence signals. Few trades, but higher success rate.' },
        modeMitraillette: { label: 'RAPID FIRE', help: 'Fast and frequent trades on smaller opportunities. Higher volume, smaller gains.' },
        modeIa: { label: 'AI GEMINI', help: 'Gemini AI dynamically adjusts all parameters in real-time based on market conditions.' },
        modeManual: { label: 'MANUAL', help: 'Full control. You set all variables yourself. For experienced traders.' },
        optPanopticon: { label: 'Panopticon', help: 'Visual chart analysis via Gemini 3 Vision. Analyzes market screenshots for additional signals.' },
        optAiValidation: { label: 'AI Mode', help: 'Activates AI-driven piloting (AI Mode).' },
        optAiBuyValidation: { label: 'Buy Validation', help: 'Requires explicit AI validation before any purchase.' },
        optEarn: { label: 'Auto-Staking', help: 'Automatically stakes idle BTC in Kraken Earn for passive returns.' },

        optWhales: { label: 'Whale Tracker', help: 'Detects large wallet movements and whale activity for smarter entries.' },

        // Advanced Section
        notifications: 'NOTIFICATIONS',
        optNotifyBuys: { label: 'Notify Buys', help: 'Push notification when a buy order is executed.' },
        optNotifySells: { label: 'Notify Sells', help: 'Push notification when a sell order is executed.' },
        optNotifyReports: { label: 'Notify Reports', help: 'Push notification when a periodic report is generated.' },
        optNotifyMutations: { label: 'Notify Mutations', help: 'Push notification when AI switches strategy (e.g. Mitraillette -> Sniper).' },
        optNotifyCircuitBreaker: { label: 'Notify Breaker', help: 'Push notification when Circuit Breaker activates (trading halted).' },

        optCircuitBreaker: { label: 'Circuit Breaker', help: 'Safety mechanism that halts trading if daily loss exceeds 3%.' },
        optReportInterval: { label: 'Report Interval (min)', help: 'Time in minutes between each status report scan (Default: 89 - F89).' },
        optGoldenRatchet: { label: 'Golden Ratchet', help: 'Infinite Phi-based trailing stop. ON = lock profits dynamically. OFF = use fixed TP1/TP2.' },
        optGoldenMemory: { label: 'Golden Memory', help: 'Auto-execute trades when pattern matches 89%+ (F89) from winning trade history. Requires 5 memories minimum.' },
        optDca: { label: 'DCA Mode', help: 'Dollar Cost Averaging - Average down on losing positions. EXPERIMENTAL - Use with caution.' },

        syncing: 'SYNCHRONIZATION...',
        syncDesc: 'Fetching live data from Kraken. Please wait.',
        waitingData: 'WAITING FOR DATA...',
    },
    fr: {
        market: 'MARCHÉ',
        regime: 'Régime',
        btc24h: 'BTC 24h',
        sentiment: 'Sentiment',
        cycle: 'Cycle',
        portfolio: 'PORTEFEUILLE',
        total: 'Total',
        active: 'Actif',
        cash: 'Cash',
        positions: 'Positions',
        btcReserve: 'RÉSERVE BTC',
        earn: 'Earn',
        value: 'Valeur',
        piggybank: 'Tirelire',
        combat: 'COMBAT',
        winRate: 'Win Rate',
        score: 'Score',
        pnl24h: 'PnL 24h',
        pnlTotal: 'PnL Total',
        transactions: 'DERNIÈRES TRANSACTIONS',
        noTx: 'Aucune transaction',
        mode: 'MODE',
        level: 'NIVEAU',
        variables: 'VARIABLES',
        options: 'OPTIONS',
        iaAdjust: 'IA ajuste dynamiquement',
        noVar: 'Aucune variable',
        refresh: 'ACTUALISER',
        refreshing: 'ACTUALISATION...',
        apply: 'APPLIQUER',
        applying: 'APPLICATION...',
        offline: 'Mode Cache (Relais Déconnecté)',
        loading: 'Chargement...',
        circuitBreaker: 'Circuit Breaker Actif',
        levelPassive: 'PASSIF',
        levelNormal: 'NORMAL',
        levelAggressive: 'AGRESSIF',
        modeSniper: { label: 'SNIPER', help: 'Attend des signaux à très haute confiance. Peu de trades, mais meilleur taux de réussite.' },
        modeMitraillette: { label: 'MITRAILLETTE', help: 'Trades rapides et fréquents sur de petites opportunités. Plus de volume, gains plus petits.' },
        modeIa: { label: 'IA GEMINI', help: 'L\'IA Gemini ajuste tous les paramètres en temps réel selon les conditions du marché.' },
        modeManual: { label: 'MANUEL', help: 'Contrôle total. Vous définissez toutes les variables. Pour traders expérimentés.' },
        optPanopticon: { label: 'Panopticon', help: 'Analyse visuelle des charts via Gemini 3 Vision. Examine les screenshots du marché pour des signaux supplémentaires.' },
        optAiValidation: { label: 'Mode IA', help: 'Active le pilotage par intelligence artificielle (Mode IA).' },
        optAiBuyValidation: { label: 'Validation Achat', help: 'Nécessite la validation explicite de l\'IA avant tout achat.' },
        optEarn: { label: 'Auto-Staking', help: 'Stake automatiquement les BTC inactifs dans Kraken Earn pour des rendements passifs.' },

        optWhales: { label: 'Traqueur Baleines', help: 'Détecte les mouvements de gros portefeuilles et l\'activité des baleines pour de meilleures entrées.' },

        // Advanced Section
        notifications: 'NOTIFICATIONS',
        optNotifyBuys: { label: 'Notif Achats', help: 'Notification push lorsqu\'un ordre d\'achat est exécuté.' },
        optNotifySells: { label: 'Notif Ventes', help: 'Notification push lorsqu\'un ordre de vente est exécuté.' },
        optNotifyReports: { label: 'Notif Rapports', help: 'Notification push lorsqu\'un rapport périodique est généré.' },
        optNotifyMutations: { label: 'Notif Mutations', help: 'Notification push lorsque l\'IA change de stratégie (ex: Mitraillette -> Sniper).' },
        optNotifyCircuitBreaker: { label: 'Notif Breaker', help: 'Notification push lorsque le Circuit Breaker s\'active (trading stoppé).' },

        optReportInterval: { label: 'Intervalle Rapport', help: 'Temps en minutes entre chaque rapport d\'état (Défaut: 89 - F89).' },
        optCircuitBreaker: { label: 'Circuit Breaker', help: 'Mécanisme de sécurité qui stoppe le trading si la perte journalière dépasse 3%.' },
        optGoldenRatchet: { label: 'Golden Ratchet', help: 'Trailing stop infini basé sur Phi. ON = verrouille les gains dynamiquement. OFF = TP1/TP2 fixes.' },
        optGoldenMemory: { label: 'Golden Memory', help: 'Exécute auto. les trades quand un pattern correspond à 89%+ (F89) de l\'historique gagnant. Minimum 5 mémoires.' },
        optDca: { label: 'Mode DCA', help: 'Dollar Cost Averaging - Moyenne à la baisse sur positions perdantes. EXPÉRIMENTAL - À utiliser avec prudence.' },

        syncing: 'SYNCHRONISATION...',
        syncDesc: 'Récupération des données live Kraken. Veuillez patienter.',
        waitingData: 'EN ATTENTE DES DONNÉES...',
    }
};

export default function TraderPanel() {
    const { locale, traderState, setTraderState } = useTrinityStore();
    const t = DICT[locale] || DICT.fr;
    const varInfo = VARIABLE_INFO[locale] || VARIABLE_INFO.fr;

    // SOTA 2026: Use persistent store state, fallback to null only if never fetched
    const status = traderState;

    // const [loading, setLoading] = useState(true); // FINAL SOTA 2026: Removed blocking loading
    const [error, setError] = useState(false); // SOTA 2026

    // SOTA 2026: Initialize from Store to prevent flicker
    const config = traderState?.config || {};

    const [selectedMode, setSelectedMode] = useState(config.mode || 'mitraillette');
    const [isOffline, setIsOffline] = useState(false);

    // ... [keep other states]
    const [selectedLevel, setSelectedLevel] = useState(config.level ?? 1);
    const [isApplying, setIsApplying] = useState(false);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [tooltip, setTooltip] = useState(null);

    // Options toggles
    const [optPanopticon, setOptPanopticon] = useState(config.panopticon_enabled || false);
    const [optAiValidation, setOptAiValidation] = useState(config.ai_enabled !== false); // Default true
    const [optAiBuyValidation, setOptAiBuyValidation] = useState(config.ai_buy_validation !== false); // New Validation
    const [optGhostMode, setOptGhostMode] = useState(config.ghost_mode_enabled !== false); // 👻 Ghost Mode
    const [optEarn, setOptEarn] = useState(config.earn !== false); // Default true
    const [optWhales, setOptWhales] = useState(config.whales_enabled !== false); // Default true
    const [optQuantum, setOptQuantum] = useState(config.quantum_enabled !== false); // ⚛️ Quantum Pulse (Default True)

    // Advanced Options
    const [optNotifyBuys, setOptNotifyBuys] = useState(config.notify_buys !== false);
    const [optNotifySells, setOptNotifySells] = useState(config.notify_sells !== false);
    const [optNotifyReports, setOptNotifyReports] = useState(config.notify_reports !== false);
    const [optNotifyMutations, setOptNotifyMutations] = useState(config.notify_mutations !== false);
    const [optNotifyCircuitBreaker, setOptNotifyCircuitBreaker] = useState(config.notify_circuit_breaker !== false);
    const [optReportInterval, setOptReportInterval] = useState(config.report_interval || 89);
    const [optCircuitBreaker, setOptCircuitBreaker] = useState(config.circuit_breaker_enabled !== false);
    const [optGoldenRatchet, setOptGoldenRatchet] = useState(config.use_golden_ratchet !== false);
    const [optGoldenMemoryAutoexec, setOptGoldenMemoryAutoexec] = useState(config.golden_memory_autoexec || false);
    const [optDca, setOptDca] = useState(config.dca_enabled || false);  // 📉 DCA (disabled by default)

    // SOTA 2026: Unsaved Changes Detection
    const originalConfigRef = useRef(null);
    const [isDirty, setIsDirty] = useState(false);

    // Helper to update original config reference
    const updateOriginalConfig = useCallback((config) => {
        originalConfigRef.current = config;
        setIsDirty(false);
    }, []);

    // SOTA 2026: Sync useState from store when traderState changes (hydration + API refresh)
    useEffect(() => {
        if (!traderState?.config) return;
        const cfg = traderState.config;
        setSelectedMode(cfg.mode || 'mitraillette');
        setSelectedLevel(cfg.level ?? 1);
        setOptPanopticon(cfg.panopticon_enabled || false);
        setOptAiValidation(cfg.ai_enabled !== false);
        setOptAiBuyValidation(cfg.ai_buy_validation !== false);
        setOptGhostMode(cfg.ghost_mode_enabled !== false);
        setOptEarn(cfg.earn !== false);
        setOptWhales(cfg.whales_enabled !== false);
        setOptQuantum(cfg.quantum_enabled !== false);
        setOptNotifyBuys(cfg.notify_buys !== false);
        setOptNotifySells(cfg.notify_sells !== false);
        setOptNotifyReports(cfg.notify_reports !== false);
        setOptNotifyMutations(cfg.notify_mutations !== false);
        setOptNotifyCircuitBreaker(cfg.notify_circuit_breaker !== false);
        setOptReportInterval(cfg.report_interval || 89);
        setOptCircuitBreaker(cfg.circuit_breaker_enabled !== false);
        setOptGoldenRatchet(cfg.use_golden_ratchet !== false);
        setOptGoldenMemoryAutoexec(cfg.golden_memory_autoexec || false);
        setOptDca(cfg.dca_enabled || false);
        updateOriginalConfig(cfg);
    }, [traderState, updateOriginalConfig]);

    // Helper to extract comparable config object from current state
    const getCurrentConfigObject = useCallback(() => ({
        mode: selectedMode,
        level: selectedLevel,
        ai_enabled: true, // Always true in UI
        ai_buy_validation: optAiBuyValidation,
        panopticon_enabled: optPanopticon,
        earn: optEarn,
        whales_enabled: optWhales,
        notify_buys: optNotifyBuys,
        notify_sells: optNotifySells,
        notify_reports: optNotifyReports,
        notify_mutations: optNotifyMutations,
        notify_circuit_breaker: optNotifyCircuitBreaker,
        report_interval: parseInt(optReportInterval) || 89,
        circuit_breaker_enabled: optCircuitBreaker,
        use_golden_ratchet: optGoldenRatchet,
        golden_memory_autoexec: optGoldenMemoryAutoexec
    }), [selectedMode, selectedLevel, optAiBuyValidation, optPanopticon, optEarn, optWhales, optNotifyBuys, optNotifySells, optNotifyReports, optNotifyMutations, optNotifyCircuitBreaker, optReportInterval, optCircuitBreaker, optGoldenRatchet, optGoldenMemoryAutoexec]);

    // Check Dirty Status
    useEffect(() => {
        if (!originalConfigRef.current) return;
        const current = getCurrentConfigObject();
        // Simple JSON comparison
        const dirty = JSON.stringify(current) !== JSON.stringify(originalConfigRef.current);
        setIsDirty(dirty);
    }, [getCurrentConfigObject]);

    // SOTA 2026: Hook Protection
    useUnsavedChanges(isDirty);

    const fetchStatus = useCallback(async (force = false) => {
        try {
            setError(false);
            const ts = Date.now();
            const url = `${ANGEL_BASE_URL}/api/trader/status?_t=${ts}${force ? '&refresh=true' : ''}`;
            const res = await fetch(url, { headers: getTrinityHeaders(), cache: 'no-store' });
            if (!res.ok) throw new Error('API Error');
            const data = await res.json();

            // SOTA 2026: Update Global Store (Persist data)
            setTraderState(data);
            setIsOffline(false);

            if (data.config) {
                // ... [keep config mapping]
                setSelectedMode(data.config.mode || 'mitraillette');
                setSelectedLevel(data.config.level ?? 1);
                setOptPanopticon(data.config.panopticon_enabled || false);
                setOptAiValidation(data.config.ai_enabled !== false);
                setOptAiBuyValidation(data.config.ai_buy_validation !== false);
                setOptGhostMode(data.config.ghost_mode_enabled !== false);
                setOptEarn(data.config.earn !== false);
                setOptWhales(data.config.whales_enabled !== false);
                setOptQuantum(data.config.quantum_enabled !== false); // Sync Quantum
                // Advanced
                setOptNotifyBuys(data.config.notify_buys !== false);
                setOptNotifySells(data.config.notify_sells !== false);
                setOptNotifyReports(data.config.notify_reports !== false);
                setOptNotifyMutations(data.config.notify_mutations !== false);
                setOptReportInterval(data.config.report_interval || 89);
                setOptCircuitBreaker(data.config.circuit_breaker_enabled !== false);
                setOptGoldenRatchet(data.config.use_golden_ratchet !== false);
                setOptGoldenMemoryAutoexec(data.config.golden_memory_autoexec || false);
                setOptDca(data.config.dca_enabled || false);

                // Update Reference for Dirty Checking (Normalized)
                updateOriginalConfig({
                    mode: data.config.mode || 'mitraillette',
                    level: data.config.level ?? 1,
                    ai_enabled: true,
                    ai_buy_validation: data.config.ai_buy_validation !== false,
                    ghost_mode_enabled: data.config.ghost_mode_enabled !== false,
                    panopticon_enabled: data.config.panopticon_enabled || false,
                    earn: data.config.earn !== false,
                    whales_enabled: data.config.whales_enabled !== false,
                    quantum_enabled: data.config.quantum_enabled !== false,
                    notify_buys: data.config.notify_buys !== false,
                    notify_sells: data.config.notify_sells !== false,
                    notify_reports: data.config.notify_reports !== false,
                    notify_mutations: data.config.notify_mutations !== false,
                    report_interval: data.config.report_interval || 89,
                    circuit_breaker_enabled: data.config.circuit_breaker_enabled !== false,
                    use_golden_ratchet: data.config.use_golden_ratchet !== false,
                    golden_memory_autoexec: data.config.golden_memory_autoexec || false
                });
            }
        } catch (e) {
            // SOTA 2026: Silent Fail - Suppress console spam for 502s
            // console.error(e); 
            setIsOffline(true);
        }
        finally { setIsRefreshing(false); }
    }, []);

    // SOTA 2026: Auto-polling enabled for Live PnL & Overlay resolution
    useEffect(() => {
        let interval;
        // SOTA 2026: Harmonized timing - 3s initial delay (Standard 350)
        const timer = setTimeout(() => {
            fetchStatus(); // Initial fetch after 3s delay
            interval = setInterval(fetchStatus, 180000); // Poll every 3m
        }, 3000);

        return () => {
            clearTimeout(timer);
            if (interval) clearInterval(interval);
        };
    }, [fetchStatus]);

    const handleRefresh = () => { setIsRefreshing(true); fetchStatus(true); };

    const applyConfig = async () => {
        setIsApplying(true);
        try {
            await fetch(`${ANGEL_BASE_URL}/api/trader/config`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({
                    mode: selectedMode,
                    level: selectedLevel,
                    ai_enabled: true, // SOTA 2026: Forced ON (Button removed)
                    ai_buy_validation: optAiBuyValidation,
                    ghost_mode_enabled: optGhostMode,
                    panopticon_enabled: optPanopticon,
                    earn: optEarn,
                    whales_enabled: optWhales,
                    quantum_enabled: optQuantum, // ⚛️ SOTA
                    // Advanced
                    notify_buys: optNotifyBuys,
                    notify_sells: optNotifySells,
                    notify_reports: optNotifyReports,
                    notify_mutations: optNotifyMutations,
                    notify_circuit_breaker: optNotifyCircuitBreaker,
                    report_interval: parseInt(optReportInterval) || 89,
                    circuit_breaker_enabled: optCircuitBreaker,
                    use_golden_ratchet: optGoldenRatchet,
                    golden_memory_autoexec: optGoldenMemoryAutoexec,
                    dca_enabled: optDca
                })
            });
            await fetchStatus(); // Will update originalConfigRef via fetch
        } catch (e) { console.error(e); }
        finally { setIsApplying(false); }
    };


    const modes = [
        { id: 'sniper', label: t.modeSniper.label, icon: Target, color: 'cyan', help: t.modeSniper.help },
        { id: 'mitraillette', label: t.modeMitraillette.label, icon: Zap, color: 'pink', help: t.modeMitraillette.help },
        { id: 'ia', label: t.modeIa.label, icon: Activity, color: 'purple', help: t.modeIa.help },
        { id: 'manual', label: t.modeManual.label, icon: Settings, color: 'amber', help: t.modeManual.help },
    ];
    const levels = [t.levelPassive, t.levelNormal, t.levelAggressive];



    // SOTA 2026: Always show panel, just indicate status in UI
    // if (status?.status === 'offline') ... removed to allow offline config

    const report = status?.report || {};

    // SOTA 2026: Sync Status Banner
    if (report.sync_status === 'BOOTING') {
        return (
            <div className="flex flex-col items-center justify-center h-full text-white/50 gap-4 text-sm animate-pulse">
                <RefreshCw size={48} className="text-amber-500 animate-spin" />
                <div className="text-center">
                    <h3 className="text-amber-400 font-bold text-lg mb-1">{t.syncing}</h3>
                    <p className="text-white/40">{t.syncDesc}</p>
                </div>
            </div>
        );
    }
    const strategies = status?.strategies || {};
    const ranges = status?.ranges || {};
    const iaState = status?.ia_state || {};
    const currentStrategy = strategies[selectedMode] || strategies.mitraillette || {};
    const currentRanges = ranges[selectedMode] || ranges.mitraillette || {};

    const tradesHistory = report.trades_history || [];
    // SOTA 2026: Enhanced Zero Data Recognition
    // If total capital is 0 AND btc_24h is 0, we assume uninitialized/loading state.
    // This allows active users with 0 balance to still see market data if btc_24h != 0.
    const isUninitialized = (!status && !isOffline) || (status?.status !== 'offline' && (report.total_capital || 0) === 0 && (report.btc_24h || 0) === 0 && (report.sentiment || 50) === 50);

    // IA Mode: active sub-mode and level
    const iaActiveSubmode = iaState.active_mode || 'mitraillette';
    const iaActiveLevel = { LOW: 0, DEFAULT: 1, HIGH: 2 }[iaState.active_variation] ?? 1;


    const getRegimeStyle = (r) => ({ BULL: 'text-green-400', BEAR: 'text-red-400', CRASH: 'text-red-600' }[r] || 'text-amber-400');
    const getRegimeIcon = (r) => ({ BULL: '🟢', BEAR: '🔴', CRASH: '💀' }[r] || '🟡');
    const getTrendColor = (v) => v >= 0 ? 'text-green-400' : 'text-red-400';

    const formatTimeAgo = (time) => {
        if (!time) return 'N/A';
        // Auto-detect seconds vs ms (1e10 is approx year 2286 in seconds, so safe cutoff)
        const timestamp = time > 1e11 ? time / 1000 : time;
        const d = Date.now() / 1000 - timestamp;

        if (d < 60) return `${Math.floor(d)}s`;
        if (d < 3600) return `${Math.floor(d / 60)}m`;
        if (d < 86400) return `${Math.floor(d / 3600)}h`;
        return `${Math.floor(d / 86400)}j`;
    };

    const isLevelDisabled = selectedMode === 'ia' || selectedMode === 'manual';
    const gradientBtn = `w-full py-3 rounded-lg font-bold text-sm bg-gradient-to-r from-cyan-500 to-pink-500 text-white hover:from-cyan-400 hover:to-pink-400 disabled:opacity-50 transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] flex items-center justify-center gap-2`;

    // Progress bar component
    const ProgressBar = ({ value, color }) => (
        <div className="flex items-center gap-2 w-28">
            <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div className={`h-full ${color || 'bg-cyan-500'} transition-all`}
                    style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
            </div>
            <span className="text-white/70 text-sm w-10 text-right">{value.toFixed(0)}%</span>
        </div>
    );

    // Two-column row component
    const Row2 = ({ left, right }) => (
        <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between items-center">
                <span className="text-white/50">{left.label}</span>
                {left.bar !== undefined ? <ProgressBar value={left.bar} color={left.color} /> : <span className={left.color || 'text-white/70'}>{left.value}</span>}
            </div>
            <div className="flex justify-between items-center">
                <span className="text-white/50">{right.label}</span>
                {right.bar !== undefined ? <ProgressBar value={right.bar} color={right.color} /> : <span className={right.color || 'text-white/70'}>{right.value}</span>}
            </div>
        </div>
    );

    // Variable row with tooltip
    const VariableRow = ({ varKey, value, idPrefix = '' }) => {
        const info = varInfo[varKey] || { label: varKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), help: null };
        const range = currentRanges[varKey] || [];
        const displayValue = selectedMode !== 'manual' && range.length > 0 ? range[selectedLevel] || value : value;
        const isActive = tooltip === varKey;

        return (
            <div className="flex justify-between items-center gap-2 py-1 relative">
                <div className="flex items-center gap-1.5">
                    <span className="text-white/60 text-sm">{info.label}</span>
                    {info.help && (
                        <button
                            className="text-white/30 hover:text-cyan-400 transition-colors"
                            onMouseEnter={() => setTooltip(varKey)}
                            onMouseLeave={() => setTooltip(null)}
                        >
                            <HelpCircle size={14} />
                        </button>
                    )}
                    {isActive && info.help && (
                        <div className="absolute left-0 top-8 z-50 bg-black/95 border border-cyan-500/50 rounded-lg p-3 text-sm text-white/90 max-w-xs shadow-xl">
                            {info.help}
                        </div>
                    )}
                </div>
                <input
                    id={`${idPrefix}${varKey}`}
                    name={`${idPrefix}${varKey}`}
                    type="text"
                    readOnly={selectedMode !== 'manual'}
                    disabled={selectedMode !== 'manual'}
                    value={typeof displayValue === 'number' ? displayValue.toFixed(varKey.includes('loss') || varKey.includes('tp') ? 4 : varKey.includes('rsi') || varKey.includes('confidence') ? 1 : 0) : displayValue}
                    className={`w-20 px-2 py-1 text-right text-sm rounded border ${selectedMode === 'manual' ? 'bg-black/50 border-white/20 text-white' : 'bg-black/20 border-white/5 text-white/40 cursor-not-allowed'}`}
                />
            </div>
        );
    };

    return (
        <PanelLayout
            isWaitingForData={false}
            isError={error}
            onRetry={fetchStatus}
            footer={
                <ActionButtons
                    onRefresh={handleRefresh}
                    onApply={applyConfig}
                    isRefreshing={isRefreshing}
                    isApplying={isApplying}
                    refreshLabel={t.refresh}
                    refreshingLabel={t.refreshing}
                    applyLabel={t.apply}
                    applyingLabel={t.applying}
                />
            }
        >
            <ResponsiveGrid>

                {/* COLUMN 1: FINANCIALS & COMBAT */}
                <div className="flex flex-col gap-3">
                    {/* MARCHÉ */}
                    <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                            <TrendingUp size={14} className="text-cyan-400" />{t.market}
                        </h3>
                        <Row2
                            left={{ label: t.regime, value: `${report.regime || 'RANGE'} ${getRegimeIcon(report.regime)}`, color: getRegimeStyle(report.regime) }}
                            right={{ label: t.btc24h, value: `${(report.btc_24h || 0) >= 0 ? '+' : ''}${(report.btc_24h || 0).toFixed(2)}%`, color: getTrendColor(report.btc_24h) }}
                        />
                        <Row2
                            left={{ label: t.sentiment, bar: report.sentiment || 50, color: 'bg-cyan-500' }}
                            right={{ label: t.cycle, value: `#${report.cycle || 0}` }}
                        />
                    </section>

                    {/* PORTEFEUILLE & POSITIONS */}
                    <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                            <Wallet size={14} className="text-cyan-400" />{t.portfolio}
                        </h3>
                        <Row2
                            left={{ label: t.netWorth || "Net Worth", value: `${(report.total_capital || 0).toFixed(2)}€`, color: 'text-cyan-300' }}
                            right={{ label: t.equity || "Equity (EUR)", value: `${(report.capital_actif || 0).toFixed(2)}€` }}
                        />
                        <Row2
                            left={{ label: t.cash, value: `${(report.cash || 0).toFixed(2)}€` }}
                            right={{ label: t.invested || "Invested", value: `${(report.positions_value || 0).toFixed(2)}€` }}
                        />
                    </section>

                    {/* STATUS OF POSITIONS (Detailed) */}
                    {Object.keys(report.positions || {}).length > 0 && (
                        <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                            <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                                <Swords size={14} className="text-cyan-400" />{t.positions || "Active Positions"}
                            </h3>
                            <div className="mt-3 overflow-x-auto">
                                <table className="w-full text-xs text-left">
                                    <thead>
                                        <tr className="text-white/30 border-b border-white/5">
                                            <th className="py-1">Pair</th>
                                            <th className="py-1 text-right text-white/50">{t.invested || "Invested"}</th>
                                            <th className="py-1 text-right text-white/50">{t.current || "Current"}</th>
                                            <th className="py-1 text-right">SL €</th>
                                            <th className="py-1 text-right">TP €</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-white/70">
                                        {Object.entries(report.positions).map(([pair, details]) => {
                                            const entryPrice = details.entry_price || 0;
                                            const quantity = details.quantity || 0;
                                            const cost = details.cost || (entryPrice * quantity);
                                            const currentPrice = details.current_price || 0;
                                            const value = details.value || (currentPrice * quantity);

                                            // SOTA 2026: Golden Ratchet Visualization
                                            // Prioritize Virtual Stop (Ghost) if valid and better than Hard Stop
                                            const hardStop = details.stop_loss || (entryPrice * (1 + (details.sl || currentStrategy.stop_loss || -0.01618)));
                                            const virtualStop = details.virtual_stop_loss || 0;

                                            let finalSlPrice = hardStop;
                                            let slColorClass = "text-red-400"; // Default: Hazard

                                            if (virtualStop > hardStop) {
                                                finalSlPrice = virtualStop;
                                                slColorClass = "text-cyan-400 font-bold"; // SOTA: Profit Secured (Ghost)
                                            }

                                            const slTotal = finalSlPrice * quantity;

                                            // SOTA: Golden Steps for Display
                                            // 1.3, 1.618, 2.618, 4.236, 6.854, 11.09, 17.94
                                            const GOLDEN_STEPS_PCT = [0.013, 0.01618, 0.02618, 0.04236, 0.06854, 0.1109, 0.1794];

                                            const tp1Pct = details.tp1 || currentStrategy.tp1 || 0.013;
                                            const tp1Price = entryPrice * (1 + tp1Pct);
                                            let tpTotalDisplay = (tp1Price * quantity).toFixed(2) + '€';
                                            let tpColorClass = "text-emerald-400";

                                            // If Ratchet is active (Cyan SL), we show the NEXT Golden Target
                                            if (virtualStop > hardStop) {
                                                const currentPct = (currentPrice - entryPrice) / entryPrice;
                                                // Find next step > currentPct
                                                const nextStep = GOLDEN_STEPS_PCT.find(s => s > currentPct) || (currentPct * 1.618);
                                                const nextTargetPrice = entryPrice * (1 + nextStep);

                                                tpTotalDisplay = (nextTargetPrice * quantity).toFixed(2) + '€';
                                                tpColorClass = "text-cyan-400 font-bold"; // Next Target
                                            }

                                            const formatVal = (v) => v.toFixed(2) + '€';

                                            return (
                                                <tr key={pair} className="border-b border-white/5 last:border-0 hover:bg-white/5">
                                                    <td className="py-1 font-mono text-cyan-400">{pair.replace('/EUR', '')}</td>
                                                    <td className="py-1 text-right text-white/50">{formatVal(cost)}</td>
                                                    <td className={`py-1 text-right ${(value || 0) >= cost ? 'text-green-400' : 'text-red-400'}`}>
                                                        {formatVal(value)}
                                                    </td>
                                                    <td className={`py-1 text-right ${slColorClass}`}>
                                                        {formatVal(slTotal)}
                                                        {/* SOTA: Subliminal Ghost Indicator (Only needed if different from hard stop) */}
                                                        {/* We already color the main price in Cyan, so no need for clutter unless requested */}
                                                    </td>
                                                    <td className={`py-1 text-right ${tpColorClass}`}>{tpTotalDisplay}</td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    )}

                    {/* RÉSERVE BTC */}
                    <section className="bg-black/30 border border-orange-500/30 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-orange-400 mb-2 flex items-center gap-1.5">
                            <Bitcoin size={14} />{t.btcReserve}
                        </h3>
                        <Row2
                            left={{ label: t.total, value: `${(report.btc_total || 0).toFixed(6)}`, color: 'text-orange-300' }}
                            right={{ label: t.earn, value: `${(report.btc_earn || 0).toFixed(6)}` }}
                        />
                        <Row2
                            left={{ label: t.value, value: `${(report.btc_value || 0).toFixed(2)}€ 🔒`, color: 'text-orange-400' }}
                            right={{ label: t.piggybank, value: `${(report.cagnotte || 0).toFixed(2)}€` }}
                        />
                    </section>

                    {/* COMBAT (Moved back to Col 1) */}
                    <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                            <Swords size={14} className="text-cyan-400" />{t.combat}
                        </h3>
                        <Row2
                            left={{ label: t.winRate, bar: report.win_rate || 0, color: report.win_rate >= 50 ? 'bg-green-500' : 'bg-red-500' }}
                            right={{ label: t.score, value: <><span className="text-green-400">{report.wins || 0}W</span>-<span className="text-red-400">{report.losses || 0}L</span></> }}
                        />
                        <Row2
                            left={{ label: t.pnl24h, value: `${(report.pnl_daily || 0) >= 0 ? '+' : ''}${(report.pnl_daily || 0).toFixed(2)}€`, color: getTrendColor(report.pnl_daily) }}
                            right={{ label: t.pnlTotal, value: `${(report.pnl_global || 0) >= 0 ? '+' : ''}${(report.pnl_global || 0).toFixed(2)}€`, color: getTrendColor(report.pnl_global) }}
                        />
                    </section>

                    {/* TRANSACTIONS (Moved to Col 1) */}
                    <AdaptiveCard className="flex flex-col h-[250px] min-h-[250px] max-h-[250px]">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5 shrink-0">
                            <Clock size={14} className="text-cyan-400" />{t.transactions} ({tradesHistory.length})
                        </h3>
                        <div className="flex-1 grid grid-cols-2 gap-2 min-h-0">
                            {/* LEFT: SELLS */}
                            <div className="flex flex-col min-h-0 border-r border-white/5 pr-1">
                                <h4 className="text-[10px] font-bold text-red-400/50 uppercase mb-1 tracking-wider">Sells</h4>
                                <div className="flex-1 overflow-y-auto pr-1 space-y-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                                    {tradesHistory.filter(t => t.side === 'sell').length > 0 ? (
                                        tradesHistory.filter(t => t.side === 'sell').map((trade, i) => (
                                            <div key={i} className="flex items-center justify-between gap-1 py-0.5 border-b border-white/5 last:border-0 text-xs hover:bg-white/5 pl-1 rounded">
                                                <span className="text-white/70 font-mono truncate">{trade.pair?.replace('/EUR', '')}</span>
                                                {trade.pnl_pct !== 0 && (
                                                    <span className={`text-[10px] font-mono ${trade.pnl_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {trade.pnl_pct > 0 ? '+' : ''}{(trade.pnl_pct * 100).toFixed(1)}%
                                                    </span>
                                                )}
                                                <span className="text-white/30 text-[10px] ml-auto">{formatTimeAgo(trade.time)}</span>
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-white/20 text-center py-4 text-xs italic">No sells</p>
                                    )}
                                </div>
                            </div>

                            {/* RIGHT: BUYS */}
                            <div className="flex flex-col min-h-0 pl-1">
                                <h4 className="text-[10px] font-bold text-green-400/50 uppercase mb-1 tracking-wider">Buys</h4>
                                <div className="flex-1 overflow-y-auto pr-1 space-y-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                                    {tradesHistory.filter(t => t.side === 'buy').length > 0 ? (
                                        tradesHistory.filter(t => t.side === 'buy').map((trade, i) => (
                                            <div key={i} className="flex items-center justify-between gap-1 py-0.5 border-b border-white/5 last:border-0 text-xs hover:bg-white/5 pl-1 rounded">
                                                <span className="text-white/70 font-mono truncate">{trade.pair?.replace('/EUR', '')}</span>
                                                <span className="text-white/30 text-[10px] ml-auto">{formatTimeAgo(trade.time)}</span>
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-white/20 text-center py-4 text-xs italic">No buys</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    </AdaptiveCard>
                </div>

                {/* COLUMN 2: OPERATIONS (Notifications, Options) */}
                <div className="flex flex-col gap-3">
                    {/* NOTIFICATIONS */}
                    <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                            <Bell size={14} className="text-cyan-400" />{t.notifications}
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            <OptionToggle
                                icon={TrendingUp}
                                label={t.optNotifyBuys.label}
                                value={optNotifyBuys}
                                onChange={() => setOptNotifyBuys(!optNotifyBuys)}
                                activeColor="green"
                                tooltip={t.optNotifyBuys.help}
                                isTooltipActive={tooltip === 'opt_notifyBuys'}
                                onTooltipEnter={() => setTooltip('opt_notifyBuys')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={TrendingDown}
                                label={t.optNotifySells.label}
                                value={optNotifySells}
                                onChange={() => setOptNotifySells(!optNotifySells)}
                                activeColor="red"
                                tooltip={t.optNotifySells.help}
                                isTooltipActive={tooltip === 'opt_notifySells'}
                                onTooltipEnter={() => setTooltip('opt_notifySells')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={ShieldAlert}
                                label={t.optNotifyCircuitBreaker.label}
                                value={optNotifyCircuitBreaker}
                                onChange={() => setOptNotifyCircuitBreaker(!optNotifyCircuitBreaker)}
                                activeColor="amber"
                                tooltip={t.optNotifyCircuitBreaker.help}
                                isTooltipActive={tooltip === 'opt_notifyCircuitBreaker'}
                                onTooltipEnter={() => setTooltip('opt_notifyCircuitBreaker')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={GitBranch}
                                label={t.optNotifyMutations.label}
                                value={optNotifyMutations}
                                onChange={() => setOptNotifyMutations(!optNotifyMutations)}
                                activeColor="purple"
                                tooltip={t.optNotifyMutations.help}
                                isTooltipActive={tooltip === 'opt_notifyMutations'}
                                onTooltipEnter={() => setTooltip('opt_notifyMutations')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                        </div>
                        {/* Bottom Row: Notify Reports (left) + Interval (right) */}
                        <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-white/5">
                            {/* Left: Notify Reports Toggle */}
                            <OptionToggle
                                icon={FileText}
                                label={t.optNotifyReports.label}
                                value={optNotifyReports}
                                onChange={() => setOptNotifyReports(!optNotifyReports)}
                                activeColor="cyan"
                                tooltip={t.optNotifyReports.help}
                                isTooltipActive={tooltip === 'opt_notifyReports'}
                                onTooltipEnter={() => setTooltip('opt_notifyReports')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            {/* Right: Report Interval */}
                            <div className="flex items-center justify-between gap-2 px-2 py-2 rounded border border-white/10 relative">
                                <div className="flex items-center gap-1.5">
                                    <Timer size={14} className="text-white/60" />
                                    <span className="text-white/70 text-sm truncate">{t.optReportInterval.label}</span>
                                    <button
                                        className="text-white/30 hover:text-cyan-400 transition-colors shrink-0"
                                        onMouseEnter={(e) => { e.stopPropagation(); setTooltip('report_interval'); }}
                                        onMouseLeave={() => setTooltip(null)}
                                    >
                                        <HelpCircle size={12} />
                                    </button>
                                    {tooltip === 'report_interval' && (
                                        <div className="absolute left-0 bottom-full mb-2 z-50 bg-black/95 border border-cyan-500/50 rounded-lg p-3 text-sm text-white/90 w-64 shadow-xl text-left">
                                            {t.optReportInterval.help}
                                        </div>
                                    )}
                                </div>
                                <input
                                    id="optReportInterval"
                                    name="optReportInterval"
                                    type="number"
                                    value={optReportInterval}
                                    onChange={(e) => setOptReportInterval(e.target.value)}
                                    className="w-14 px-2 py-0.5 bg-black/50 border border-white/20 rounded text-right text-white text-sm"
                                />
                            </div>
                        </div>
                    </section>

                    {/* OPTIONS */}
                    <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                            <Settings size={14} className="text-cyan-400" />{t.options}
                        </h3>
                        <div className="flex flex-col gap-3">
                            {/* Main Toggles Grid */}
                            <div className="grid grid-cols-2 gap-2">
                                <OptionToggle
                                    icon={Eye}
                                    label={t.optPanopticon.label}
                                    value={optPanopticon}
                                    onChange={() => setOptPanopticon(!optPanopticon)}
                                    activeColor="cyan"
                                    tooltip={t.optPanopticon.help}
                                    isTooltipActive={tooltip === 'opt_panopticon'}
                                    onTooltipEnter={() => setTooltip('opt_panopticon')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={CheckCircle}
                                    label={t.optAiBuyValidation.label.replace('Buy', 'AI Buy')}
                                    value={optAiBuyValidation}
                                    onChange={() => setOptAiBuyValidation(!optAiBuyValidation)}
                                    activeColor="purple"
                                    tooltip={t.optAiBuyValidation.help}
                                    isTooltipActive={tooltip === 'opt_ai_buy'}
                                    onTooltipEnter={() => setTooltip('opt_ai_buy')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={PiggyBank}
                                    label={t.optEarn.label}
                                    value={optEarn}
                                    onChange={() => setOptEarn(!optEarn)}
                                    activeColor="green"
                                    tooltip={t.optEarn.help}
                                    isTooltipActive={tooltip === 'opt_earn'}
                                    onTooltipEnter={() => setTooltip('opt_earn')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={Zap}
                                    label="Quantum Pulse"
                                    value={optQuantum}
                                    onChange={() => setOptQuantum(!optQuantum)}
                                    activeColor="yellow"
                                    tooltip="⚛️ Detects Global Market Coherence (Tsunami Alert)"
                                    isTooltipActive={tooltip === 'opt_quantum'}
                                    onTooltipEnter={() => setTooltip('opt_quantum')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={Ghost}
                                    label="Ghost Mode"
                                    value={optGhostMode}
                                    onChange={() => setOptGhostMode(!optGhostMode)}
                                    activeColor="indigo"
                                    tooltip="👻 Virtual Stop Loss (Hidden from Exchange)"
                                    isTooltipActive={tooltip === 'opt_ghost'}
                                    onTooltipEnter={() => setTooltip('opt_ghost')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={Fish}
                                    label={t.optWhales.label}
                                    value={optWhales}
                                    onChange={() => setOptWhales(!optWhales)}
                                    activeColor="blue"
                                    tooltip={t.optWhales.help}
                                    isTooltipActive={tooltip === 'opt_whales'}
                                    onTooltipEnter={() => setTooltip('opt_whales')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={ShieldAlert}
                                    label={t.optCircuitBreaker.label}
                                    value={optCircuitBreaker}
                                    onChange={() => setOptCircuitBreaker(!optCircuitBreaker)}
                                    activeColor="amber"
                                    tooltip={t.optCircuitBreaker.help}
                                    isTooltipActive={tooltip === 'opt_breaker'}
                                    onTooltipEnter={() => setTooltip('opt_breaker')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={Target}
                                    label={t.optGoldenRatchet.label}
                                    value={optGoldenRatchet}
                                    onChange={() => setOptGoldenRatchet(!optGoldenRatchet)}
                                    activeColor="pink"
                                    tooltip={t.optGoldenRatchet.help}
                                    isTooltipActive={tooltip === 'opt_ratchet'}
                                    onTooltipEnter={() => setTooltip('opt_ratchet')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={Brain}
                                    label={t.optGoldenMemory.label}
                                    value={optGoldenMemoryAutoexec}
                                    onChange={() => setOptGoldenMemoryAutoexec(!optGoldenMemoryAutoexec)}
                                    activeColor="rose"
                                    tooltip={t.optGoldenMemory.help}
                                    isTooltipActive={tooltip === 'opt_golden_memory'}
                                    onTooltipEnter={() => setTooltip('opt_golden_memory')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={TrendingDown}
                                    label={t.optDca.label}
                                    value={optDca}
                                    onChange={() => setOptDca(!optDca)}
                                    activeColor="gray"
                                    tooltip={t.optDca.help}
                                    isTooltipActive={tooltip === 'opt_dca'}
                                    onTooltipEnter={() => setTooltip('opt_dca')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                            </div>


                        </div>
                    </section>
                </div>

                {/* COLUMN 3: CONTROLS & VARIABLES */}
                <div className="flex flex-col gap-3">
                    {/* MODE */}
                    <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                            <Target size={14} className="text-pink-400" />{t.mode}
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            {modes.map(mode => {
                                const Icon = mode.icon;
                                const isSelected = selectedMode === mode.id;
                                const neonClass = { cyan: 'btn-neon-primary text-glow-cyan', pink: 'btn-neon-pink text-glow-pink', purple: 'btn-neon-purple text-glow-purple', amber: 'border-amber-500 bg-amber-500/20 text-amber-400' }[mode.color];
                                const isModeTooltip = tooltip === `mode_${mode.id}`;
                                return (
                                    <div key={mode.id} className="relative">
                                        <button onClick={() => setSelectedMode(mode.id)}
                                            className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded border transition-all text-sm ${isSelected ? `${neonClass} border-transparent` : 'border-white/10 text-white/50 hover:border-white/30'}`}>
                                            <span className="flex items-center gap-2">
                                                <Icon size={14} />
                                                <span className="font-bold">
                                                    {mode.label}
                                                </span>
                                            </span>
                                            <span
                                                className="text-white/30 hover:text-cyan-400 transition-colors"
                                                onMouseEnter={(e) => { e.stopPropagation(); setTooltip(`mode_${mode.id}`); }}
                                                onMouseLeave={() => setTooltip(null)}
                                            >
                                                <HelpCircle size={14} />
                                            </span>
                                        </button>
                                        {isModeTooltip && (
                                            <div className="absolute left-0 top-full mt-1 z-50 bg-black/95 border border-cyan-500/50 rounded-lg p-3 text-sm text-white/90 w-64 shadow-xl">
                                                {mode.help}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </section>

                    {/* NIVEAU */}
                    <section className={`bg-black/30 border border-white/10 rounded-lg p-3 ${isLevelDisabled ? 'opacity-70' : ''}`}>
                        <h3 className="text-sm font-bold text-white/80 mb-2">
                            📊 {t.level} {isLevelDisabled && <span className="text-white/40">(auto)</span>}
                        </h3>
                        <div className="flex gap-2">
                            {levels.map((level, idx) => {
                                const isIaActive = selectedMode === 'ia' && idx === iaActiveLevel;
                                return (
                                    <button key={level} onClick={() => !isLevelDisabled && setSelectedLevel(idx)} disabled={isLevelDisabled}
                                        className={`flex-1 py-2 rounded border text-sm font-bold transition-all ${isLevelDisabled
                                            ? isIaActive
                                                ? 'border-purple-500/50 bg-purple-500/20 text-purple-400/80 cursor-not-allowed'
                                                : 'border-white/5 text-white/30 cursor-not-allowed'
                                            : selectedLevel === idx
                                                ? 'border-cyan-500 bg-cyan-500/20 text-cyan-400'
                                                : 'border-white/10 text-white/50 hover:border-white/30'
                                            }`}>
                                        {level}
                                    </button>
                                );
                            })}
                        </div>
                    </section>

                    {/* VARIABLES */}
                    <AdaptiveCard className="!flex-none h-fit min-h-0">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5 shrink-0">
                            <Settings size={14} className="text-pink-400" />{t.variables}
                            <span className="font-normal text-white/50 ml-1">
                                ({selectedMode === 'ia'
                                    ? `${t.modeIa.label} ${modes.find(m => m.id === iaActiveSubmode)?.label || iaActiveSubmode.toUpperCase()} - ${levels[iaActiveLevel]}`
                                    : selectedMode === 'manual'
                                        ? modes.find(m => m.id === 'manual')?.label || 'MANUAL'
                                        : `${modes.find(m => m.id === selectedMode)?.label || selectedMode.toUpperCase()} - ${levels[selectedLevel]}`})
                            </span>
                        </h3>
                        <div className="flex-1 overflow-y-auto pr-1">
                            {Object.keys(currentStrategy).length === 0 ? (
                                <p className="text-white/40 text-center py-2">{selectedMode === 'ia' ? t.iaAdjust : t.noVar}</p>
                            ) : (
                                <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                                    {Object.entries(currentStrategy).map(([key, value]) => (
                                        <VariableRow key={key} varKey={key} value={value} idPrefix="desktop_" />
                                    ))}
                                </div>
                            )}
                        </div>
                    </AdaptiveCard>
                </div>

                {isOffline && !report.total_capital && (
                    <div className="flex items-center gap-2 text-amber-400 bg-amber-500/10 rounded-lg p-3 text-sm animate-pulse">
                        <Activity size={16} /> 📡 {t.offline || 'Mode Cache'}
                    </div>
                )}
                {report.circuit_breaker && (
                    <div className="flex items-center gap-2 text-red-400 bg-red-500/10 rounded-lg p-3 text-sm">
                        <AlertTriangle size={16} />⚠️ {t.circuitBreaker}
                    </div>
                )}

            </ResponsiveGrid>
        </PanelLayout>
    );
}
