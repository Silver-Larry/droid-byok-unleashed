import { useState, useEffect, useRef } from 'react';
import type * as React from 'react';
import { Plus, Download, Upload, ChevronDown, Check, Star, Settings2 } from 'lucide-react';
import type { Profile, ProfilesResponse } from '../types';
import { Button } from './ui/button';
import { ProfileEditor } from './ProfileEditor';
import {
  fetchProfiles,
  createProfile,
  updateProfile,
  deleteProfile,
  setDefaultProfile,
  exportConfig,
  importConfig,
} from '../services/api';

const PRESET_PROFILES: Partial<Profile>[] = [
  {
    name: 'GLM-4.6 (Zhipu)',
    model_patterns: ['glm-4.6*', 'glm-4.5*'],
    match_type: 'wildcard',
    priority: 100,
    upstream: { base_url: 'https://open.bigmodel.cn/api/paas/v4', api_key: '', api_format: 'openai' },
    reasoning: { enabled: true, type: 'deepseek', effort: 'auto', filter_thinking_tags: true },
  },
  {
    name: 'Gemini 3 Pro',
    model_patterns: ['gemini-3-pro*', 'gemini-3*'],
    match_type: 'wildcard',
    priority: 90,
    upstream: { base_url: 'https://generativelanguage.googleapis.com', api_key: '', api_format: 'gemini' },
    reasoning: { enabled: true, type: 'gemini', effort: 'auto', filter_thinking_tags: true },
  },
  {
    name: 'Claude Opus 4.5',
    model_patterns: ['claude-opus-4*', 'claude-4*opus*'],
    match_type: 'wildcard',
    priority: 80,
    upstream: { base_url: 'https://api.anthropic.com', api_key: '', api_format: 'anthropic' },
    reasoning: { enabled: true, type: 'anthropic', effort: 'high', filter_thinking_tags: true },
  },
  {
    name: 'GPT-5.1 Codex Max',
    model_patterns: ['gpt-5*', 'gpt-5.1-codex*'],
    match_type: 'wildcard',
    priority: 70,
    upstream: { base_url: 'https://api.openai.com', api_key: '', api_format: 'openai' },
    reasoning: { enabled: true, type: 'openai', effort: 'high', filter_thinking_tags: true },
  },
  {
    name: 'Minimax M2',
    model_patterns: ['minimax-m2*', 'abab7*'],
    match_type: 'wildcard',
    priority: 60,
    upstream: { base_url: 'https://api.minimax.chat', api_key: '', api_format: 'openai' },
    reasoning: { enabled: false, type: 'custom', effort: 'auto', filter_thinking_tags: false },
  },
];

interface ProfileManagerProps {
  onProfileChange?: (profile: Profile) => void;
}

export function ProfileManager({ onProfileChange }: ProfileManagerProps) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [defaultProfileId, setDefaultProfileId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadProfiles = async () => {
    try {
      setLoading(true);
      const data: ProfilesResponse = await fetchProfiles();
      setProfiles(data.profiles);
      setDefaultProfileId(data.default_profile);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profiles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfiles();
  }, []);

  const handleSave = async (data: Partial<Profile>) => {
    try {
      if (data.id) {
        await updateProfile(data.id, data);
      } else {
        await createProfile(data);
      }
      await loadProfiles();
      setEditingProfile(null);
      setIsCreating(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    }
  };

  const handleDelete = async (profileId: string) => {
    if (!confirm('Are you sure you want to delete this profile?')) return;
    try {
      await deleteProfile(profileId);
      await loadProfiles();
      setEditingProfile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete profile');
    }
  };

  const handleSetDefault = async (profileId: string) => {
    try {
      await setDefaultProfile(profileId);
      setDefaultProfileId(profileId);
      const profile = profiles.find(p => p.id === profileId);
      if (profile && onProfileChange) {
        onProfileChange(profile);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set default profile');
    }
  };

  const handleExport = async () => {
    try {
      const config = await exportConfig();
      const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `droid-proxy-config-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export config');
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const content = await file.text();
      const config = JSON.parse(content);
      await importConfig(config, true);
      await loadProfiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import config');
    }
    e.target.value = '';
  };

  const handleAddPreset = async (preset: Partial<Profile>) => {
    try {
      await createProfile({ ...preset, enabled: true });
      await loadProfiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add preset');
    }
  };

  const defaultProfile = profiles.find(p => p.id === defaultProfileId);

  if (editingProfile || isCreating) {
    return (
      <div className="p-6">
        <h2 className="text-lg font-bold mb-4">
          {editingProfile ? `Edit Profile: ${editingProfile.name}` : 'Create New Profile'}
        </h2>
        <ProfileEditor
          profile={editingProfile || undefined}
          onSave={handleSave}
          onCancel={() => { setEditingProfile(null); setIsCreating(false); }}
          onDelete={editingProfile ? () => handleDelete(editingProfile.id) : undefined}
        />
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-foreground">Configuration Profiles</h2>
          <p className="text-sm text-muted-foreground">
            Manage API configurations with model pattern matching
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
            <Upload className="w-4 h-4 mr-1" /> Import
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="w-4 h-4 mr-1" /> Export
          </Button>
          <Button size="sm" onClick={() => setIsCreating(true)}>
            <Plus className="w-4 h-4 mr-1" /> New Profile
          </Button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-destructive bg-destructive/10 px-4 py-2 rounded mb-4">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {/* Default Profile Selector */}
      <div className="mb-6 p-4 border border-border rounded-lg bg-card">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-foreground">Default Profile</h3>
            <p className="text-xs text-muted-foreground">Used when no model pattern matches</p>
          </div>
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-2 border border-input rounded-md bg-background hover:bg-muted"
            >
              <span className="text-sm">{defaultProfile?.name || 'Select...'}</span>
              <ChevronDown className="w-4 h-4" />
            </button>
            {dropdownOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
                <div className="absolute right-0 top-full mt-1 w-48 bg-card border border-border rounded-md shadow-lg z-50">
                  {profiles.map(profile => (
                    <button
                      key={profile.id}
                      onClick={() => { handleSetDefault(profile.id); setDropdownOpen(false); }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted text-left"
                    >
                      {profile.id === defaultProfileId && <Check className="w-4 h-4 text-primary" />}
                      <span className={profile.id === defaultProfileId ? 'font-medium' : ''}>{profile.name}</span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Profiles List */}
      {loading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : profiles.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-lg">
          <p className="text-muted-foreground mb-4">No profiles configured</p>
          <p className="text-sm text-muted-foreground mb-4">Add a preset to get started:</p>
          <div className="flex flex-wrap gap-2 justify-center">
            {PRESET_PROFILES.map((preset, i) => (
              <Button key={i} variant="outline" size="sm" onClick={() => handleAddPreset(preset)}>
                <Plus className="w-3 h-3 mr-1" /> {preset.name}
              </Button>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {profiles.map(profile => (
            <div
              key={profile.id}
              className={`flex items-center gap-4 p-4 border rounded-lg cursor-pointer transition-colors ${
                profile.enabled ? 'border-border bg-card hover:bg-muted/50' : 'border-border/50 bg-muted/30 opacity-60'
              }`}
              onClick={() => setEditingProfile(profile)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-foreground">{profile.name}</span>
                  {profile.id === defaultProfileId && (
                    <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                  )}
                  <span className="text-xs px-1.5 py-0.5 bg-muted rounded">{profile.match_type}</span>
                  {profile.reasoning?.enabled && (
                    <span className="text-xs px-1.5 py-0.5 bg-primary/10 text-primary rounded">
                      {profile.reasoning.type}
                    </span>
                  )}
                  {!profile.enabled && (
                    <span className="text-xs px-1.5 py-0.5 bg-muted text-muted-foreground rounded">disabled</span>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  <span className="font-mono">{profile.model_patterns.join(', ')}</span>
                  <span className="mx-2">|</span>
                  <span>{profile.upstream?.base_url}</span>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setEditingProfile(profile); }}>
                <Settings2 className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Presets */}
      {profiles.length > 0 && (
        <div className="mt-8 pt-6 border-t border-border">
          <p className="text-xs text-muted-foreground mb-3">Quick add presets:</p>
          <div className="flex flex-wrap gap-2">
            {PRESET_PROFILES.filter(p => !profiles.some(existing => existing.name === p.name)).map((preset, i) => (
              <Button key={i} variant="outline" size="sm" onClick={() => handleAddPreset(preset)}>
                <Plus className="w-3 h-3 mr-1" /> {preset.name}
              </Button>
            ))}
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleImport}
        className="hidden"
      />
    </div>
  );
}
