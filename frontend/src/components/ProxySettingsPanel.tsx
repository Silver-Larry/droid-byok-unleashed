import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { fetchProxyConfig, updateProxyConfig } from '../services/api';
import { Button } from './ui/button';
import { Input } from './ui/input';

export function ProxySettingsPanel() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [port, setPort] = useState<string>('5000');
  const [apiKey, setApiKey] = useState<string>('');

  const load = async () => {
    try {
      setLoading(true);
      const cfg = await fetchProxyConfig();
      setPort(String(cfg.port ?? 5000));
      setApiKey(cfg.api_key ?? '');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load proxy settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleSave = async () => {
    setError(null);
    const parsedPort = Number.parseInt(port, 10);
    if (!Number.isFinite(parsedPort) || parsedPort < 1 || parsedPort > 65535) {
      setError('Port must be an integer between 1 and 65535');
      return;
    }

    try {
      setSaving(true);
      const res = await updateProxyConfig({ port: parsedPort, api_key: apiKey });
      toast.success('Proxy settings saved');
      if (res.restart_required) {
        toast.message('Port changed. Please restart the proxy backend to take effect.');
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save proxy settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-lg font-bold text-foreground">Local Proxy Settings</h2>
        <p className="text-sm text-muted-foreground">
          Configure the proxy server port and (optional) local API key.
        </p>
      </div>

      {error && (
        <div className="text-sm text-destructive bg-destructive/10 px-4 py-2 rounded mb-4">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      <div className="space-y-4 max-w-xl">
        <div className="p-4 border border-border rounded-lg bg-card">
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Proxy Port</label>
              <Input
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="5000"
                inputMode="numeric"
                disabled={loading || saving}
              />
              <p className="text-[11px] text-muted-foreground mt-1">
                Changing port requires restarting the backend.
              </p>
            </div>

            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Proxy API Key (optional)</label>
              <Input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="leave empty to disable auth"
                disabled={loading || saving}
              />
              <p className="text-[11px] text-muted-foreground mt-1">
                When set, clients must send <span className="font-mono">Authorization: Bearer &lt;key&gt;</span> to access the proxy.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-4">
            <Button onClick={handleSave} disabled={loading || saving}>
              {saving ? 'Saving...' : 'Save'}
            </Button>
            <Button variant="outline" onClick={load} disabled={loading || saving}>
              Reload
            </Button>
            {loading && <span className="text-xs text-muted-foreground">Loading...</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
