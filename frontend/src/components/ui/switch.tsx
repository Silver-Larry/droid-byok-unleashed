import * as React from 'react';
import { cn } from '../../lib/utils';

export interface SwitchProps {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  id?: string;
}

const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked = false, onCheckedChange, disabled = false, className, id }, ref) => {
    return (
      <button
        ref={ref}
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange?.(!checked)}
        className={cn(
          'peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center border-2 border-border transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-50',
          checked ? 'bg-primary border-primary' : 'bg-input',
          className
        )}
      >
        <span
          className={cn(
            'pointer-events-none block h-3 w-3 bg-background shadow-lg transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0.5'
          )}
        />
      </button>
    );
  }
);

Switch.displayName = 'Switch';

export { Switch };
