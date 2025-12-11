import { useEffect, useState } from 'react';
import { checkHealth } from '../services/api';
import { cn } from '../lib/utils';

export function StatusBar() {
  const [status, setStatus] = useState<'checking' | 'healthy' | 'error'>('checking');
  const [upstream, setUpstream] = useState<string>('');

  useEffect(() => {
    const check = async () => {
      try {
        const health = await checkHealth();
        setStatus('healthy');
        setUpstream(health.upstream);
      } catch {
        setStatus('error');
      }
    };

    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className="inline-flex items-center gap-1.5">
      <svg width="6" height="6" viewBox="0 0 6 6" className="shrink-0">
        <circle
          cx="3"
          cy="3"
          r="3"
          className={cn(
            status === 'healthy' && "fill-emerald-400",
            status === 'error' && "fill-red-400",
            status === 'checking' && "fill-amber-400 animate-pulse"
          )}
        />
      </svg>
      <span className="text-primary-foreground/80">
        {status === 'healthy'
          ? upstream || 'CONNECTED'
          : status === 'error'
          ? 'DISCONNECTED'
          : 'CHECKING...'}
      </span>
    </span>
  );
}
