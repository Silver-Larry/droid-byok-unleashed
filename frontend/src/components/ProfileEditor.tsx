import { useState, useEffect } from 'react';
import type * as React from 'react';
import { Save, X, Plus, Trash2, TestTube } from 'lucide-react';
import type { Profile, MatchType, ReasoningType, ReasoningEffort, ApiFormatType, ReasoningTypeInfo } from '../types';
import { API_FORMAT_OPTIONS } from '../types';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Switch } from './ui/switch';
import { fetchReasoningTypes, testProfileMatch } from '../services/api';

const MATCH_TYPE_OPTIONS: { value: MatchType; label: string; description: string }[] = [
  { value: 'exact', label: 'Exact', description: 'Exact string match' },
  { value: 'wildcard', label: 'Wildcard', description: 'Supports * and ? patterns' },
  { value: 'regex', label: 'Regex', description: 'Regular expression' },
];

const REASONING_TYPE_OPTIONS: { value: ReasoningType; label: string }[] = [
  { value: 'deepseek', label: 'DeepSeek / GLM' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'qwen', label: 'Qwen' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'custom', label: 'Custom' },
];

const REASONING_EFFORT_OPTIONS: { value: ReasoningEffort; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'minimal', label: 'Minimal' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'auto', label: 'Auto' },
];

interface ProfileEditorProps {
  profile?: Profile;
  onSave: (profile: Partial<Profile>) => void;
  onCancel: () => void;
  onDelete?: () => void;
}

export function ProfileEditor({ profile, onSave, onCancel, onDelete }: ProfileEditorProps) {
  // Basic info
  const [name, setName] = useState(profile?.name || '');
  const [patterns, setPatterns] = useState<string[]>(profile?.model_patterns || ['']);
  const [matchType, setMatchType] = useState<MatchType>(profile?.match_type || 'wildcard');
  const [priority, setPriority] = useState(profile?.priority ?? 0);
  const [enabled, setEnabled] = useState(profile?.enabled ?? true);

  // Upstream config
  const [baseUrl, setBaseUrl] = useState(profile?.upstream?.base_url || 'https://api.deepseek.com');
  const [apiKey, setApiKey] = useState(profile?.upstream?.api_key || '');
  const [apiFormat, setApiFormat] = useState<ApiFormatType>(profile?.upstream?.api_format || 'openai');

  // LLM params
  const [temperature, setTemperature] = useState<number | null>(profile?.llm_params?.temperature ?? null);
  const [topP, setTopP] = useState<number | null>(profile?.llm_params?.top_p ?? null);
  const [maxTokens, setMaxTokens] = useState<number | null>(profile?.llm_params?.max_tokens ?? null);

  // Reasoning config
  const [reasoningEnabled, setReasoningEnabled] = useState(profile?.reasoning?.enabled ?? false);
  const [reasoningType, setReasoningType] = useState<ReasoningType>(profile?.reasoning?.type || 'deepseek');
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort>(profile?.reasoning?.effort || 'auto');
  const [budgetTokens, setBudgetTokens] = useState<number | null>(profile?.reasoning?.budget_tokens ?? null);
  const [filterTags, setFilterTags] = useState(profile?.reasoning?.filter_thinking_tags ?? true);

  // Test
  const [testModel, setTestModel] = useState('');
  const [testResult, setTestResult] = useState<string | null>(null);

  // Reasoning type info from API
  const [typeInfo, setTypeInfo] = useState<ReasoningTypeInfo[]>([]);

  useEffect(() => {
    fetchReasoningTypes()
      .then(data => setTypeInfo(data.types))
      .catch(console.error);
  }, []);

  const handleAddPattern = () => {
    setPatterns([...patterns, '']);
  };

  const handleRemovePattern = (index: number) => {
    if (patterns.length > 1) {
      setPatterns(patterns.filter((_, i) => i !== index));
    }
  };

  const handlePatternChange = (index: number, value: string) => {
    const newPatterns = [...patterns];
    newPatterns[index] = value;
    setPatterns(newPatterns);
  };

  const handleTest = async () => {
    if (!testModel.trim()) return;
    try {
      const result = await testProfileMatch(testModel);
      if (result.matched) {
        setTestResult(`Matched: ${result.matched.name}`);
      } else {
        setTestResult('No match');
      }
    } catch (err) {
      setTestResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Partial<Profile> = {
      name,
      model_patterns: patterns.filter(p => p.trim()),
      match_type: matchType,
      priority,
      enabled,
      upstream: {
        base_url: baseUrl,
        api_key: apiKey,
        api_format: apiFormat,
      },
      llm_params: {
        temperature: temperature ?? undefined,
        top_p: topP ?? undefined,
        max_tokens: maxTokens ?? undefined,
      },
      reasoning: {
        enabled: reasoningEnabled,
        type: reasoningType,
        effort: reasoningEffort,
        budget_tokens: budgetTokens,
        filter_thinking_tags: filterTags,
      },
    };
    if (profile?.id) {
      data.id = profile.id;
    }
    onSave(data);
  };

  const currentTypeInfo = typeInfo.find(t => t.value === reasoningType);
  const supportedEfforts = currentTypeInfo?.supported_efforts || REASONING_EFFORT_OPTIONS.map(o => o.value);

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-foreground border-b border-border pb-2">Basic Info</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Name *</label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="Profile name" required />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Priority</label>
            <Input type="number" value={priority} onChange={e => setPriority(parseInt(e.target.value) || 0)} />
          </div>
        </div>

        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Model Patterns</label>
          {patterns.map((pattern, index) => (
            <div key={index} className="flex gap-2 mb-2">
              <Input
                value={pattern}
                onChange={e => handlePatternChange(index, e.target.value)}
                placeholder={matchType === 'regex' ? '^model-.*' : 'model-*'}
              />
              {patterns.length > 1 && (
                <Button type="button" variant="ghost" size="sm" onClick={() => handleRemovePattern(index)}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={handleAddPattern}>
            <Plus className="w-3 h-3 mr-1" /> Add Pattern
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Match Type</label>
            <select
              value={matchType}
              onChange={e => setMatchType(e.target.value as MatchType)}
              className="w-full border border-input bg-background px-3 py-2 text-sm rounded-md"
            >
              {MATCH_TYPE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground mt-1">
              {MATCH_TYPE_OPTIONS.find(o => o.value === matchType)?.description}
            </p>
          </div>
          <div className="flex items-center justify-between pt-6">
            <label className="text-sm text-foreground">Enabled</label>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>
        </div>
      </div>

      {/* Upstream Config */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-foreground border-b border-border pb-2">Upstream API</h3>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Base URL</label>
          <Input value={baseUrl} onChange={e => setBaseUrl(e.target.value)} placeholder="https://api.deepseek.com" />
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">API Key</label>
          <Input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="sk-..." />
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">API Format</label>
          <select
            value={apiFormat}
            onChange={e => setApiFormat(e.target.value as ApiFormatType)}
            className="w-full border border-input bg-background px-3 py-2 text-sm rounded-md"
          >
            {API_FORMAT_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* LLM Params */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-foreground border-b border-border pb-2">LLM Parameters</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Temperature</label>
            <Input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={temperature ?? ''}
              onChange={e => setTemperature(e.target.value ? parseFloat(e.target.value) : null)}
              placeholder="0.7"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Top P</label>
            <Input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={topP ?? ''}
              onChange={e => setTopP(e.target.value ? parseFloat(e.target.value) : null)}
              placeholder="1.0"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Max Tokens</label>
            <Input
              type="number"
              value={maxTokens ?? ''}
              onChange={e => setMaxTokens(e.target.value ? parseInt(e.target.value) : null)}
              placeholder="4096"
            />
          </div>
        </div>
      </div>

      {/* Reasoning Config */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h3 className="text-sm font-bold text-foreground">Reasoning Model</h3>
          <Switch checked={reasoningEnabled} onCheckedChange={setReasoningEnabled} />
        </div>
        {reasoningEnabled && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Type</label>
                <select
                  value={reasoningType}
                  onChange={e => setReasoningType(e.target.value as ReasoningType)}
                  className="w-full border border-input bg-background px-3 py-2 text-sm rounded-md"
                >
                  {REASONING_TYPE_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Effort</label>
                <select
                  value={reasoningEffort}
                  onChange={e => setReasoningEffort(e.target.value as ReasoningEffort)}
                  className="w-full border border-input bg-background px-3 py-2 text-sm rounded-md"
                >
                  {REASONING_EFFORT_OPTIONS.filter(opt => supportedEfforts.includes(opt.value)).map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Budget Tokens</label>
                <Input
                  type="number"
                  value={budgetTokens ?? ''}
                  onChange={e => setBudgetTokens(e.target.value ? parseInt(e.target.value) : null)}
                  placeholder="16000"
                />
              </div>
              <div className="flex items-center justify-between pt-6">
                <label className="text-sm text-foreground">Filter &lt;think&gt; Tags</label>
                <Switch checked={filterTags} onCheckedChange={setFilterTags} />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Test */}
      <div className="space-y-2">
        <h3 className="text-sm font-bold text-foreground border-b border-border pb-2">Test Match</h3>
        <div className="flex gap-2">
          <Input
            value={testModel}
            onChange={e => setTestModel(e.target.value)}
            placeholder="Enter model name to test..."
            onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleTest())}
          />
          <Button type="button" variant="outline" onClick={handleTest}>
            <TestTube className="w-4 h-4" />
          </Button>
        </div>
        {testResult && (
          <p className="text-xs text-muted-foreground">{testResult}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t border-border">
        <div>
          {onDelete && profile?.id && (
            <Button type="button" variant="destructive" size="sm" onClick={onDelete}>
              <Trash2 className="w-4 h-4 mr-1" /> Delete
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onCancel}>
            <X className="w-4 h-4 mr-1" /> Cancel
          </Button>
          <Button type="submit">
            <Save className="w-4 h-4 mr-1" /> {profile?.id ? 'Update' : 'Create'}
          </Button>
        </div>
      </div>
    </form>
  );
}
