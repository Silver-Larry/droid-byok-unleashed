import { useEffect, useState } from 'react';
import { fetchModels } from '../services/api';
import type { Model } from '../types';
import type { Config } from '../hooks/useConfig';

interface ModelSelectorProps {
  value: string;
  onChange: (model: string) => void;
  config: Config;
}

export function ModelSelector({ value, onChange, config }: ModelSelectorProps) {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await fetchModels(config);
        setModels(response.data || []);
        if (response.data?.length > 0 && !value) {
          onChange(response.data[0].id);
        }
      } catch {
        setModels([{ id: 'deepseek-reasoner', object: 'model' }]);
      } finally {
        setLoading(false);
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.apiKey, config.baseUrl]);

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={loading}
      className="border border-input bg-background px-2 py-1 text-xs text-foreground focus:border-ring focus:outline-none cursor-pointer"
    >
      {models.map((model) => (
        <option key={model.id} value={model.id}>
          {model.id}
        </option>
      ))}
    </select>
  );
}
