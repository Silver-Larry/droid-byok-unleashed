import { RotateCcw } from 'lucide-react';
import type { ReasoningType, ReasoningEffort, ReasoningTypeInfo } from '../types';
import { Switch } from './ui/switch';
import { Select } from './ui/select';
import { Checkbox } from './ui/checkbox';
import { Textarea } from './ui/textarea';
import { Input } from './ui/input';
import { Button } from './ui/button';

interface ReasoningPanelProps {
  enabled: boolean;
  type: ReasoningType;
  effort: ReasoningEffort;
  budgetTokens: number | null;
  customParams: string;
  filterTags: boolean;
  typeOptions: ReasoningTypeInfo[];
  effortOptions: { value: ReasoningEffort; label: string }[];
  onEnabledChange: (v: boolean) => void;
  onTypeChange: (v: ReasoningType) => void;
  onEffortChange: (v: ReasoningEffort) => void;
  onBudgetTokensChange: (v: number | null) => void;
  onCustomParamsChange: (v: string) => void;
  onFilterTagsChange: (v: boolean) => void;
  onReset: () => void;
  compact?: boolean;
}

function SettingItem({ title, description, children, inline = false }: { 
  title: string; 
  description?: string; 
  children: React.ReactNode;
  inline?: boolean;
}) {
  if (inline) {
    return (
      <div className="flex items-center justify-between py-2">
        <div className="flex-1 min-w-0 mr-3">
          <div className="text-sm text-foreground font-medium">{title}</div>
          {description && <div className="text-xs text-muted-foreground mt-0.5">{description}</div>}
        </div>
        <div className="flex-shrink-0">{children}</div>
      </div>
    );
  }
  return (
    <div className="py-2">
      <div className="text-sm text-foreground font-medium">{title}</div>
      {description && <div className="text-xs text-muted-foreground mt-0.5">{description}</div>}
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function ReasoningPanel({
  enabled,
  type,
  effort,
  budgetTokens,
  customParams,
  filterTags,
  typeOptions,
  effortOptions,
  onEnabledChange,
  onTypeChange,
  onEffortChange,
  onBudgetTokensChange,
  onCustomParamsChange,
  onFilterTagsChange,
  onReset,
  compact = false,
}: ReasoningPanelProps) {
  const selectedType = typeOptions.find(t => t.value === type);
  const availableEfforts = effortOptions.filter(
    e => selectedType?.supported_efforts.includes(e.value)
  );

  const typeSelectOptions = typeOptions.map(t => ({
    value: t.value,
    label: t.label,
    description: t.description,
  }));

  const effortSelectOptions = availableEfforts.map(e => ({
    value: e.value,
    label: e.label,
  }));

  if (compact) {
    return (
      <div className="space-y-2">
        <SettingItem title="Enable Reasoning" inline>
          <Switch checked={enabled} onCheckedChange={onEnabledChange} />
        </SettingItem>

        {enabled ? (
          <>
            <div className="grid grid-cols-2 gap-3">
              <SettingItem title="Type" description={selectedType?.description}>
                <Select
                  value={type}
                  onValueChange={(v) => onTypeChange(v as ReasoningType)}
                  options={typeSelectOptions}
                  placeholder="Select type"
                />
              </SettingItem>
              <SettingItem title="Effort">
                <Select
                  value={effort}
                  onValueChange={(v) => onEffortChange(v as ReasoningEffort)}
                  options={effortSelectOptions}
                  placeholder="Select effort"
                  disabled={effortSelectOptions.length === 0}
                />
              </SettingItem>
            </div>

            <SettingItem title="Budget Tokens" description="Override auto token budget" inline>
              <Input
                type="number"
                value={budgetTokens ?? ''}
                onChange={(e) => onBudgetTokensChange(e.target.value ? parseInt(e.target.value, 10) : null)}
                placeholder="Auto"
                className="w-24 text-center"
              />
            </SettingItem>

            <div className="py-2 border-b border-border/50">
              <Checkbox
                checked={filterTags}
                onCheckedChange={onFilterTagsChange}
                label="Filter <think> tags from response"
              />
            </div>

            <SettingItem title="Custom Parameters" description="Additional JSON (advanced)">
              <Textarea
                value={customParams}
                onChange={(e) => onCustomParamsChange(e.target.value)}
                placeholder='{"key": "value"}'
                className="min-h-[50px] text-xs"
              />
            </SettingItem>

            <div className="flex justify-end">
              <Button variant="ghost" size="sm" onClick={onReset} className="text-xs">
                <RotateCcw className="w-3 h-3 mr-1" />
                Reset
              </Button>
            </div>
          </>
        ) : (
          <div className="text-sm text-muted-foreground py-4 text-center border-t border-border/50">
            Enable to configure reasoning parameters
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="border-2 border-primary/30 bg-primary/5 p-4 h-fit rounded-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-bold text-primary uppercase tracking-wider">
          Reasoning Model
        </h3>
        <Switch checked={enabled} onCheckedChange={onEnabledChange} />
      </div>

      {enabled ? (
        <div className="space-y-3">
          <SettingItem
            title="Type"
            description={selectedType?.description}
          >
            <Select
              value={type}
              onValueChange={(v) => onTypeChange(v as ReasoningType)}
              options={typeSelectOptions}
              placeholder="Select reasoning type"
            />
          </SettingItem>

          <SettingItem
            title="Effort"
            description="Controls reasoning intensity and token budget"
          >
            <Select
              value={effort}
              onValueChange={(v) => onEffortChange(v as ReasoningEffort)}
              options={effortSelectOptions}
              placeholder="Select effort level"
              disabled={effortSelectOptions.length === 0}
            />
          </SettingItem>

          <SettingItem
            title="Budget Tokens"
            description="Override auto-calculated token budget (optional)"
          >
            <Input
              type="number"
              value={budgetTokens ?? ''}
              onChange={(e) => onBudgetTokensChange(e.target.value ? parseInt(e.target.value, 10) : null)}
              placeholder="Auto calculate"
              className="max-w-32"
            />
          </SettingItem>

          <div className="py-2">
            <Checkbox
              checked={filterTags}
              onCheckedChange={onFilterTagsChange}
              label="Filter <think> tags from response"
            />
          </div>

          <SettingItem
            title="Custom Parameters"
            description="Additional JSON parameters to merge (advanced)"
          >
            <Textarea
              value={customParams}
              onChange={(e) => onCustomParamsChange(e.target.value)}
              placeholder='{"key": "value"}'
              className="min-h-[60px] text-xs"
            />
          </SettingItem>

          <div className="flex justify-end pt-2">
            <Button variant="ghost" size="sm" onClick={onReset} className="text-xs">
              <RotateCcw className="w-3 h-3 mr-1" />
              Reset
            </Button>
          </div>
        </div>
      ) : (
        <div className="text-sm text-muted-foreground py-4 text-center">
          Enable to configure reasoning model parameters
        </div>
      )}
    </div>
  );
}
