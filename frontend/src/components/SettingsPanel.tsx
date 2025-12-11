import { useState, useEffect } from 'react';
import { Save, X, RotateCcw, Server, Key, Sliders, Zap } from 'lucide-react';
import type { Config } from '../hooks/useConfig';
import type { ReasoningType, ReasoningEffort, ReasoningTypeInfo, ApiFormatType } from '../types';
import { API_FORMAT_OPTIONS } from '../types';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ReasoningPanel } from './ReasoningPanel';
import { fetchReasoningTypes, fetchProxyConfig, updateProxyConfig } from '../services/api';

interface SettingsPanelProps {
  config: Config;
  onUpdate: (updates: Partial<Config>) => void;
  onClose: () => void;
}

function SettingItem({ title, description, children, inline = false }: { 
  title: string; 
  description?: string; 
  children: React.ReactNode;
  inline?: boolean;
}) {
  if (inline) {
    return (
      <div className="flex items-center justify-between py-3 border-b border-border/50 last:border-b-0">
        <div className="flex-1 min-w-0 mr-4">
          <div className="text-sm text-foreground font-medium">{title}</div>
          {description && <div className="text-xs text-muted-foreground mt-0.5">{description}</div>}
        </div>
        <div className="flex-shrink-0">{children}</div>
      </div>
    );
  }
  return (
    <div className="py-3 border-b border-border/50 last:border-b-0">
      <div className="text-sm text-foreground font-medium">{title}</div>
      {description && <div className="text-xs text-muted-foreground mt-0.5">{description}</div>}
      <div className="mt-2">{children}</div>
    </div>
  );
}

function SettingGroup({ 
  title, 
  icon: Icon, 
  children, 
  action,
  highlight = false 
}: { 
  title: string; 
  icon?: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  action?: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div className={`mb-6 rounded-lg border ${highlight ? 'border-primary/30 bg-primary/5' : 'border-border bg-card'}`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          {Icon && <Icon className={`w-4 h-4 ${highlight ? 'text-primary' : 'text-muted-foreground'}`} />}
          <h3 className={`text-xs font-bold uppercase tracking-wider ${highlight ? 'text-primary' : 'text-muted-foreground'}`}>
            {title}
          </h3>
        </div>
        {action}
      </div>
      <div className="px-4 py-2">{children}</div>
    </div>
  );
}

function SliderSetting({ 
  label, 
  value, 
  onChange, 
  min, 
  max, 
  step,
  description 
}: { 
  label: string; 
  value: number; 
  onChange: (v: number) => void; 
  min: number; 
  max: number; 
  step: number;
  description?: string;
}) {
  return (
    <SettingItem title={label} description={description}>
      <div className="flex items-center gap-3 max-w-md">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="flex-1 accent-primary h-1.5 rounded-full"
        />
        <span className="w-12 text-sm text-foreground text-right font-mono bg-muted px-2 py-0.5 rounded">{value.toFixed(step < 1 ? 1 : 0)}</span>
      </div>
    </SettingItem>
  );
}

function NumberSetting({
  label,
  value,
  onChange,
  placeholder,
  description
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  placeholder?: string;
  description?: string;
}) {
  return (
    <SettingItem title={label} description={description}>
      <Input
        type="number"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value ? parseInt(e.target.value, 10) : null)}
        placeholder={placeholder}
        className="max-w-32"
      />
    </SettingItem>
  );
}

const defaultLLMParams = {
  temperature: 0.7,
  topP: 1,
  topK: null as number | null,
  maxTokens: null as number | null,
  presencePenalty: 0,
  frequencyPenalty: 0,
  seed: null as number | null,
};

const defaultReasoningParams = {
  reasoningEnabled: false,
  reasoningType: 'deepseek' as ReasoningType,
  reasoningEffort: 'auto' as ReasoningEffort,
  reasoningBudgetTokens: null as number | null,
  reasoningCustomParams: '{}',
  filterThinkingTags: true,
};

export function SettingsPanel({ config, onUpdate, onClose }: SettingsPanelProps) {
  const [apiKey, setApiKey] = useState(config.apiKey);
  const [baseUrl, setBaseUrl] = useState(config.baseUrl);
  const [apiFormat, setApiFormat] = useState<ApiFormatType>(config.apiFormat || 'openai');
  const [temperature, setTemperature] = useState(config.temperature);
  const [topP, setTopP] = useState(config.topP);
  const [topK, setTopK] = useState(config.topK);
  const [maxTokens, setMaxTokens] = useState(config.maxTokens);
  const [presencePenalty, setPresencePenalty] = useState(config.presencePenalty);
  const [frequencyPenalty, setFrequencyPenalty] = useState(config.frequencyPenalty);
  const [seed, setSeed] = useState(config.seed);

  // Reasoning configuration state
  const [reasoningEnabled, setReasoningEnabled] = useState(config.reasoningEnabled);
  const [reasoningType, setReasoningType] = useState<ReasoningType>(config.reasoningType);
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort>(config.reasoningEffort);
  const [reasoningBudgetTokens, setReasoningBudgetTokens] = useState(config.reasoningBudgetTokens);
  const [reasoningCustomParams, setReasoningCustomParams] = useState(config.reasoningCustomParams);
  const [filterThinkingTags, setFilterThinkingTags] = useState(config.filterThinkingTags);

  // Proxy configuration state
  const [proxyPort, setProxyPort] = useState<number>(5000);
  const [proxyApiKey, setProxyApiKey] = useState<string>('');
  const [proxyLoading, setProxyLoading] = useState(false);
  const [proxyMessage, setProxyMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Reasoning type options from API
  const [typeOptions, setTypeOptions] = useState<ReasoningTypeInfo[]>([]);
  const [effortOptions, setEffortOptions] = useState<{ value: ReasoningEffort; label: string }[]>([]);

  useEffect(() => {
    fetchReasoningTypes()
      .then(data => {
        setTypeOptions(data.types);
        setEffortOptions(data.efforts);
      })
      .catch(err => {
        console.error('Failed to fetch reasoning types:', err);
        // Fallback defaults
        setTypeOptions([
          { value: 'deepseek', label: 'DeepSeek (R1/V3.1)', description: 'thinking.type parameter', supported_efforts: ['none', 'auto'] },
          { value: 'openai', label: 'OpenAI (o1/o3/GPT-5)', description: 'reasoning_effort parameter', supported_efforts: ['low', 'medium', 'high'] },
          { value: 'anthropic', label: 'Anthropic (Claude 3.7/4)', description: 'thinking.budgetTokens parameter', supported_efforts: ['none', 'low', 'medium', 'high'] },
          { value: 'gemini', label: 'Google (Gemini 2.5+)', description: 'thinkingConfig parameter', supported_efforts: ['none', 'low', 'medium', 'high', 'auto'] },
          { value: 'qwen', label: 'Qwen (Qwen3)', description: 'enable_thinking parameter', supported_efforts: ['none', 'low', 'medium', 'high'] },
          { value: 'openrouter', label: 'OpenRouter', description: 'reasoning.enabled parameter', supported_efforts: ['none', 'low', 'medium', 'high'] },
          { value: 'custom', label: 'Custom', description: 'Custom JSON parameters', supported_efforts: ['none', 'minimal', 'low', 'medium', 'high', 'auto'] },
        ]);
        setEffortOptions([
          { value: 'none', label: 'Off' },
          { value: 'minimal', label: 'Minimal' },
          { value: 'low', label: 'Low' },
          { value: 'medium', label: 'Medium' },
          { value: 'high', label: 'High' },
          { value: 'auto', label: 'Auto' },
        ]);
      });

    // Load proxy config
    fetchProxyConfig()
      .then(cfg => {
        setProxyPort(cfg.proxy_port);
        setProxyApiKey(cfg.proxy_api_key);
      })
      .catch(err => console.error('Failed to fetch proxy config:', err));
  }, []);

  const handleSave = () => {
    onUpdate({ 
      apiKey, 
      baseUrl,
      apiFormat,
      temperature,
      topP,
      topK,
      maxTokens,
      presencePenalty,
      frequencyPenalty,
      seed,
      reasoningEnabled,
      reasoningType,
      reasoningEffort,
      reasoningBudgetTokens,
      reasoningCustomParams,
      filterThinkingTags,
    });
    onClose();
  };

  const handleResetLLMParams = () => {
    setTemperature(defaultLLMParams.temperature);
    setTopP(defaultLLMParams.topP);
    setTopK(defaultLLMParams.topK);
    setMaxTokens(defaultLLMParams.maxTokens);
    setPresencePenalty(defaultLLMParams.presencePenalty);
    setFrequencyPenalty(defaultLLMParams.frequencyPenalty);
    setSeed(defaultLLMParams.seed);
  };

  const handleResetReasoningParams = () => {
    setReasoningEnabled(defaultReasoningParams.reasoningEnabled);
    setReasoningType(defaultReasoningParams.reasoningType);
    setReasoningEffort(defaultReasoningParams.reasoningEffort);
    setReasoningBudgetTokens(defaultReasoningParams.reasoningBudgetTokens);
    setReasoningCustomParams(defaultReasoningParams.reasoningCustomParams);
    setFilterThinkingTags(defaultReasoningParams.filterThinkingTags);
  };

  const handleSaveProxyConfig = async () => {
    if (proxyPort < 1 || proxyPort > 65535) {
      setProxyMessage({ type: 'error', text: 'Port must be between 1 and 65535' });
      return;
    }
    setProxyLoading(true);
    setProxyMessage(null);
    try {
      const result = await updateProxyConfig({ proxy_port: proxyPort, proxy_api_key: proxyApiKey });
      if (result.restart_required) {
        setProxyMessage({ type: 'success', text: 'Saved. Restart proxy to apply port change.' });
      } else {
        setProxyMessage({ type: 'success', text: 'Proxy config saved.' });
      }
    } catch {
      setProxyMessage({ type: 'error', text: 'Failed to save proxy config.' });
    } finally {
      setProxyLoading(false);
    }
  };

  return (
    <main className="flex-1 p-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-border">
        <h2 className="text-lg font-bold text-foreground">Settings</h2>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            <X className="w-3.5 h-3.5 mr-1.5" />
            Cancel
          </Button>
          <Button size="sm" onClick={handleSave}>
            <Save className="w-3.5 h-3.5 mr-1.5" />
            Save All
          </Button>
        </div>
      </div>

      <div className="max-w-5xl space-y-6">
        {/* Row 1: API & Proxy Configuration side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upstream API Configuration */}
          <SettingGroup title="Upstream API" icon={Key}>
            <SettingItem title="Base URL" description="Upstream API service endpoint">
              <div className="flex gap-2">
                <Input
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://api.deepseek.com"
                  className="flex-1"
                />
                <select
                  value={apiFormat}
                  onChange={(e) => setApiFormat(e.target.value as ApiFormatType)}
                  className="border border-input bg-background px-3 py-2 text-sm text-foreground focus:border-ring focus:outline-none cursor-pointer rounded-md min-w-[140px]"
                  title="API Format"
                >
                  {API_FORMAT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value} title={option.description}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </SettingItem>
            <SettingItem title="API Key" description="Authentication key for upstream service">
              <Input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full"
              />
            </SettingItem>
          </SettingGroup>

          {/* Proxy Server Configuration */}
          <SettingGroup 
            title="Proxy Server" 
            icon={Server}
            action={
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleSaveProxyConfig} 
                disabled={proxyLoading}
                className="text-xs"
              >
                <Save className="w-3 h-3 mr-1" />
                {proxyLoading ? 'Saving...' : 'Apply'}
              </Button>
            }
          >
            <SettingItem title="Port" description="Local proxy listening port (1-65535)" inline>
              <Input
                type="number"
                min={1}
                max={65535}
                value={proxyPort}
                onChange={(e) => setProxyPort(parseInt(e.target.value) || 5000)}
                className="w-24 text-center"
              />
            </SettingItem>
            <SettingItem title="Proxy API Key" description="Optional authentication for proxy access">
              <Input
                type="password"
                value={proxyApiKey}
                onChange={(e) => setProxyApiKey(e.target.value)}
                placeholder="Leave empty to disable"
                className="w-full"
              />
            </SettingItem>
            {proxyMessage && (
              <div className={`text-xs py-2 ${proxyMessage.type === 'error' ? 'text-destructive' : 'text-primary'}`}>
                {proxyMessage.text}
              </div>
            )}
          </SettingGroup>
        </div>

        {/* Row 2: LLM Parameters & Reasoning Model side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* LLM Parameters */}
          <SettingGroup 
            title="LLM Parameters" 
            icon={Sliders}
            action={
              <Button variant="ghost" size="sm" onClick={handleResetLLMParams} className="text-xs">
                <RotateCcw className="w-3 h-3 mr-1" />
                Reset
              </Button>
            }
          >
            <SliderSetting
              label="Temperature"
              description="Controls randomness (0-2)"
              value={temperature}
              onChange={setTemperature}
              min={0}
              max={2}
              step={0.1}
            />
            <SliderSetting
              label="Top P"
              description="Nucleus sampling threshold (0-1)"
              value={topP}
              onChange={setTopP}
              min={0}
              max={1}
              step={0.05}
            />
            <div className="grid grid-cols-2 gap-4">
              <NumberSetting
                label="Top K"
                description="Token selection limit"
                value={topK}
                onChange={setTopK}
                placeholder="e.g. 40"
              />
              <NumberSetting
                label="Max Tokens"
                description="Output token limit"
                value={maxTokens}
                onChange={setMaxTokens}
                placeholder="e.g. 4096"
              />
            </div>
            <SliderSetting
              label="Presence Penalty"
              description="Penalize repeated topics (-2 to 2)"
              value={presencePenalty}
              onChange={setPresencePenalty}
              min={-2}
              max={2}
              step={0.1}
            />
            <SliderSetting
              label="Frequency Penalty"
              description="Penalize repeated tokens (-2 to 2)"
              value={frequencyPenalty}
              onChange={setFrequencyPenalty}
              min={-2}
              max={2}
              step={0.1}
            />
            <NumberSetting
              label="Seed"
              description="For reproducible outputs"
              value={seed}
              onChange={setSeed}
              placeholder="e.g. 42"
            />
          </SettingGroup>

          {/* Reasoning Model */}
          <SettingGroup title="Reasoning Model" icon={Zap} highlight>
            <ReasoningPanel
              enabled={reasoningEnabled}
              type={reasoningType}
              effort={reasoningEffort}
              budgetTokens={reasoningBudgetTokens}
              customParams={reasoningCustomParams}
              filterTags={filterThinkingTags}
              typeOptions={typeOptions}
              effortOptions={effortOptions}
              onEnabledChange={setReasoningEnabled}
              onTypeChange={setReasoningType}
              onEffortChange={setReasoningEffort}
              onBudgetTokensChange={setReasoningBudgetTokens}
              onCustomParamsChange={setReasoningCustomParams}
              onFilterTagsChange={setFilterThinkingTags}
              onReset={handleResetReasoningParams}
              compact
            />
          </SettingGroup>
        </div>
      </div>
    </main>
  );
}
