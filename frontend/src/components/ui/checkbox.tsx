import * as React from 'react';
import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface CheckboxProps {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  id?: string;
  label?: string;
}

const Checkbox = React.forwardRef<HTMLButtonElement, CheckboxProps>(
  ({ checked = false, onCheckedChange, disabled = false, className, id, label }, ref) => {
    const checkboxElement = (
      <button
        ref={ref}
        id={id}
        type="button"
        role="checkbox"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange?.(!checked)}
        className={cn(
          'peer h-4 w-4 shrink-0 border border-input bg-background',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'flex items-center justify-center',
          checked && 'bg-primary border-primary text-primary-foreground',
          className
        )}
      >
        {checked && <Check className="h-3 w-3" />}
      </button>
    );

    if (label) {
      return (
        <div className="flex items-center gap-2">
          {checkboxElement}
          <label
            htmlFor={id}
            className="text-sm text-foreground cursor-pointer select-none"
            onClick={() => !disabled && onCheckedChange?.(!checked)}
          >
            {label}
          </label>
        </div>
      );
    }

    return checkboxElement;
  }
);

Checkbox.displayName = 'Checkbox';

export { Checkbox };
