"""
Unified Profile-Based Configuration Manager

This module provides a centralized configuration system where each "profile"
contains all settings needed to route and process requests:
- Upstream API configuration (base_url, api_key, api_format)
- LLM parameters (temperature, max_tokens, etc.)
- Reasoning parameters (type, effort, filter_thinking_tags)
- Model matching patterns for automatic routing
"""

import json
import uuid
import fnmatch
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

CONFIG_FILE = Path(__file__).parent / "proxy_config.json"

# Supported API format types
API_FORMAT_TYPES = ["openai", "openai-response", "anthropic", "gemini", "azure-openai"]

# Supported reasoning types
REASONING_TYPES = ["deepseek", "openai", "anthropic", "gemini", "qwen", "openrouter", "custom", "disabled"]

# Supported reasoning efforts
REASONING_EFFORTS = ["none", "minimal", "low", "medium", "high", "auto"]

# Match types for model patterns
MATCH_TYPES = ["exact", "wildcard", "regex"]


@dataclass
class UpstreamConfig:
    """Upstream API configuration"""
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    api_format: str = "openai"

    def to_dict(self, hide_secrets: bool = True) -> Dict[str, Any]:
        data = asdict(self)
        if hide_secrets and data.get("api_key"):
            key = data["api_key"]
            data["api_key"] = "***" + key[-4:] if len(key) > 4 else "****"
        return data


@dataclass
class LLMParams:
    """LLM generation parameters"""
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    seed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ReasoningParams:
    """Reasoning model parameters"""
    enabled: bool = False
    type: str = "deepseek"
    effort: str = "auto"
    budget_tokens: Optional[int] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)
    filter_thinking_tags: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Profile:
    """A complete configuration profile"""
    id: str
    name: str
    model_patterns: List[str] = field(default_factory=list)
    match_type: str = "wildcard"
    priority: int = 0
    enabled: bool = True
    upstream: UpstreamConfig = field(default_factory=UpstreamConfig)
    llm_params: LLMParams = field(default_factory=LLMParams)
    reasoning: ReasoningParams = field(default_factory=ReasoningParams)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self, hide_secrets: bool = True) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model_patterns": self.model_patterns,
            "match_type": self.match_type,
            "priority": self.priority,
            "enabled": self.enabled,
            "upstream": self.upstream.to_dict(hide_secrets=hide_secrets),
            "llm_params": self.llm_params.to_dict(),
            "reasoning": self.reasoning.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        upstream_data = data.get("upstream", {})
        upstream = UpstreamConfig(
            base_url=upstream_data.get("base_url", "https://api.deepseek.com"),
            api_key=upstream_data.get("api_key", ""),
            api_format=upstream_data.get("api_format", "openai"),
        )

        llm_data = data.get("llm_params", {})
        llm_params = LLMParams(
            temperature=llm_data.get("temperature"),
            top_p=llm_data.get("top_p"),
            top_k=llm_data.get("top_k"),
            max_tokens=llm_data.get("max_tokens"),
            presence_penalty=llm_data.get("presence_penalty"),
            frequency_penalty=llm_data.get("frequency_penalty"),
            seed=llm_data.get("seed"),
        )

        reasoning_data = data.get("reasoning", {})
        reasoning = ReasoningParams(
            enabled=reasoning_data.get("enabled", False),
            type=reasoning_data.get("type", "deepseek"),
            effort=reasoning_data.get("effort", "auto"),
            budget_tokens=reasoning_data.get("budget_tokens"),
            custom_params=reasoning_data.get("custom_params", {}),
            filter_thinking_tags=reasoning_data.get("filter_thinking_tags", True),
        )

        return cls(
            id=data.get("id", f"profile-{uuid.uuid4().hex[:8]}"),
            name=data.get("name", "Unnamed Profile"),
            model_patterns=data.get("model_patterns", []),
            match_type=data.get("match_type", "wildcard"),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            upstream=upstream,
            llm_params=llm_params,
            reasoning=reasoning,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def matches(self, model: str) -> bool:
        """Check if this profile matches the given model name"""
        if not self.enabled or not model:
            return False

        for pattern in self.model_patterns:
            if self.match_type == "exact":
                if model == pattern:
                    return True
            elif self.match_type == "wildcard":
                if fnmatch.fnmatch(model, pattern):
                    return True
            elif self.match_type == "regex":
                try:
                    if re.match(pattern, model):
                        return True
                except re.error:
                    continue
        return False


@dataclass
class ProxySettings:
    """Proxy server settings"""
    port: int = 5000
    api_key: str = ""

    def to_dict(self, hide_secrets: bool = True) -> Dict[str, Any]:
        data = asdict(self)
        if hide_secrets and data.get("api_key"):
            key = data["api_key"]
            data["api_key"] = "***" + key[-4:] if len(key) > 4 else "****"
        return data


class ConfigManager:
    """Unified configuration manager"""

    def __init__(self):
        self.proxy: ProxySettings = ProxySettings()
        self.profiles: List[Profile] = []
        self.default_profile_id: str = ""
        self._load()

    def _load(self):
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._parse_config(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Failed to load config file: {e}")
                self._create_default()
        else:
            self._migrate_legacy_config()

    def _parse_config(self, data: Dict[str, Any]):
        """Parse configuration data"""
        # Parse proxy settings
        proxy_data = data.get("proxy", {})
        self.proxy = ProxySettings(
            port=proxy_data.get("port", 5000),
            api_key=proxy_data.get("api_key", ""),
        )

        # Parse profiles
        self.profiles = [
            Profile.from_dict(p) for p in data.get("profiles", [])
        ]
        self.profiles.sort(key=lambda p: p.priority, reverse=True)

        # Parse default profile
        self.default_profile_id = data.get("default_profile", "")

        # Ensure at least one profile exists
        if not self.profiles:
            self._create_default()

    def _create_default(self):
        """Create default profile"""
        import os
        default_profile = Profile(
            id="default",
            name="Default",
            model_patterns=["*"],
            match_type="wildcard",
            priority=0,
            enabled=True,
            upstream=UpstreamConfig(
                base_url=os.getenv("UPSTREAM_BASE_URL", "https://api.deepseek.com"),
                api_key=os.getenv("UPSTREAM_API_KEY", ""),
                api_format="openai",
            ),
            reasoning=ReasoningParams(
                enabled=os.getenv("REASONING_ENABLED", "false").lower() == "true",
                type=os.getenv("REASONING_TYPE", "deepseek"),
                effort=os.getenv("REASONING_EFFORT", "auto"),
                filter_thinking_tags=os.getenv("FILTER_THINKING_TAGS", "true").lower() == "true",
            ),
        )
        self.profiles = [default_profile]
        self.default_profile_id = "default"
        self._save()

    def _migrate_legacy_config(self):
        """Migrate from legacy configuration files"""
        import os
        profiles = []

        # Migrate from model_routes.json
        routes_file = Path(__file__).parent / "model_routes.json"
        if routes_file.exists():
            try:
                with open(routes_file, "r", encoding="utf-8") as f:
                    routes_data = json.load(f)
                for route in routes_data.get("routes", []):
                    profile = Profile(
                        id=route.get("id", f"profile-{uuid.uuid4().hex[:8]}"),
                        name=route.get("name", "Migrated Route"),
                        model_patterns=[route.get("pattern", "*")],
                        match_type=route.get("match_type", "wildcard"),
                        priority=route.get("priority", 0),
                        enabled=route.get("enabled", True),
                        upstream=UpstreamConfig(
                            base_url=route.get("upstream_base_url", os.getenv("UPSTREAM_BASE_URL", "https://api.deepseek.com")),
                            api_key=route.get("upstream_api_key", ""),
                            api_format=route.get("upstream_api_format", "openai"),
                        ),
                        reasoning=ReasoningParams(
                            enabled=bool(route.get("reasoning_type")),
                            type=route.get("reasoning_type", "deepseek"),
                            effort=route.get("reasoning_effort", "auto"),
                            budget_tokens=route.get("reasoning_budget_tokens"),
                            custom_params=route.get("reasoning_custom_params", {}),
                            filter_thinking_tags=route.get("filter_thinking_tags", True) if route.get("filter_thinking_tags") is not None else True,
                        ),
                    )
                    profiles.append(profile)
                print(f"[MIGRATE] Migrated {len(profiles)} routes from model_routes.json")
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Failed to migrate model_routes.json: {e}")

        # Create default profile from environment variables
        default_profile = Profile(
            id="default",
            name="Default",
            model_patterns=["*"],
            match_type="wildcard",
            priority=-1,  # Lowest priority
            enabled=True,
            upstream=UpstreamConfig(
                base_url=os.getenv("UPSTREAM_BASE_URL", "https://api.deepseek.com"),
                api_key=os.getenv("UPSTREAM_API_KEY", ""),
                api_format="openai",
            ),
            reasoning=ReasoningParams(
                enabled=os.getenv("REASONING_ENABLED", "false").lower() == "true",
                type=os.getenv("REASONING_TYPE", "deepseek"),
                effort=os.getenv("REASONING_EFFORT", "auto"),
                filter_thinking_tags=os.getenv("FILTER_THINKING_TAGS", "true").lower() == "true",
            ),
        )
        profiles.append(default_profile)

        # Load proxy settings from environment
        self.proxy = ProxySettings(
            port=int(os.getenv("PROXY_PORT", "5000")),
            api_key=os.getenv("PROXY_API_KEY", ""),
        )

        self.profiles = profiles
        self.profiles.sort(key=lambda p: p.priority, reverse=True)
        self.default_profile_id = "default"
        self._save()

    def _save(self) -> bool:
        """Save configuration to file"""
        try:
            data = {
                "proxy": asdict(self.proxy),
                "profiles": [p.to_dict(hide_secrets=False) for p in self.profiles],
                "default_profile": self.default_profile_id,
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"[ERROR] Failed to save config file: {e}")
            return False

    def get_profile(self, profile_id: str) -> Optional[Profile]:
        """Get profile by ID"""
        for profile in self.profiles:
            if profile.id == profile_id:
                return profile
        return None

    def get_default_profile(self) -> Optional[Profile]:
        """Get the default profile"""
        if self.default_profile_id:
            profile = self.get_profile(self.default_profile_id)
            if profile:
                return profile
        # Fallback to first profile
        return self.profiles[0] if self.profiles else None

    def match_profile(self, model: str) -> Optional[Profile]:
        """Find the best matching profile for a model name"""
        for profile in self.profiles:
            if profile.matches(model):
                return profile
        return self.get_default_profile()

    def get_effective_config(self, model: str) -> Dict[str, Any]:
        """Get effective configuration for a model"""
        profile = self.match_profile(model)
        if not profile:
            return {}

        return {
            "profile_id": profile.id,
            "profile_name": profile.name,
            "upstream_base_url": profile.upstream.base_url,
            "upstream_api_key": profile.upstream.api_key,
            "upstream_api_format": profile.upstream.api_format,
            "llm_params": profile.llm_params.to_dict(),
            "reasoning_enabled": profile.reasoning.enabled,
            "reasoning_type": profile.reasoning.type,
            "reasoning_effort": profile.reasoning.effort,
            "reasoning_budget_tokens": profile.reasoning.budget_tokens,
            "reasoning_custom_params": profile.reasoning.custom_params,
            "filter_thinking_tags": profile.reasoning.filter_thinking_tags,
        }

    def test_match(self, model: str) -> Dict[str, Any]:
        """Test model matching against all profiles"""
        matched_profile = self.match_profile(model)
        all_matches = []

        for profile in self.profiles:
            if profile.matches(model):
                all_matches.append({
                    "id": profile.id,
                    "name": profile.name,
                    "patterns": profile.model_patterns,
                    "match_type": profile.match_type,
                    "priority": profile.priority,
                    "enabled": profile.enabled,
                })

        return {
            "model": model,
            "matched": matched_profile.to_dict() if matched_profile else None,
            "all_matches": all_matches,
        }

    # CRUD operations for profiles
    def create_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new profile"""
        if not data.get("name"):
            return {"success": False, "error": "Name is required"}

        if "match_type" in data and data["match_type"] not in MATCH_TYPES:
            return {"success": False, "error": "Invalid match_type"}

        if "model_patterns" in data:
            patterns = data["model_patterns"]
            if not isinstance(patterns, list) or any(not isinstance(p, str) for p in patterns):
                return {"success": False, "error": "model_patterns must be a list of strings"}

        upstream_data = data.get("upstream", {})
        if "api_format" in upstream_data and upstream_data["api_format"] not in API_FORMAT_TYPES:
            return {"success": False, "error": "Invalid upstream.api_format"}

        # Generate ID if not provided
        if not data.get("id"):
            data["id"] = f"profile-{uuid.uuid4().hex[:8]}"

        # Check for duplicate ID
        if any(p.id == data["id"] for p in self.profiles):
            return {"success": False, "error": "Profile ID already exists"}

        # Validate regex patterns
        if data.get("match_type") == "regex":
            for pattern in data.get("model_patterns", []):
                try:
                    re.compile(pattern)
                except re.error as e:
                    return {"success": False, "error": f"Invalid regex pattern: {e}"}

        profile = Profile.from_dict(data)
        self.profiles.append(profile)
        self.profiles.sort(key=lambda p: p.priority, reverse=True)

        if not self._save():
            return {"success": False, "error": "Failed to save configuration"}

        return {"success": True, "profile": profile.to_dict()}

    def update_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing profile"""
        profile = self.get_profile(profile_id)
        if not profile:
            return {"success": False, "error": "Profile not found"}

        match_type = data.get("match_type", profile.match_type)
        if match_type not in MATCH_TYPES:
            return {"success": False, "error": "Invalid match_type"}

        if "model_patterns" in data:
            patterns = data["model_patterns"]
            if not isinstance(patterns, list) or any(not isinstance(p, str) for p in patterns):
                return {"success": False, "error": "model_patterns must be a list of strings"}

        # Validate regex patterns
        if match_type == "regex" and "model_patterns" in data:
            for pattern in data.get("model_patterns", []):
                try:
                    re.compile(pattern)
                except re.error as e:
                    return {"success": False, "error": f"Invalid regex pattern: {e}"}

        # Update fields
        if "name" in data:
            profile.name = data["name"]
        if "model_patterns" in data:
            profile.model_patterns = data["model_patterns"]
        if "match_type" in data:
            profile.match_type = data["match_type"]
        if "priority" in data:
            profile.priority = data["priority"]
        if "enabled" in data:
            profile.enabled = data["enabled"]

        # Update upstream
        if "upstream" in data:
            upstream_data = data["upstream"]
            if "base_url" in upstream_data:
                profile.upstream.base_url = upstream_data["base_url"]
            if "api_key" in upstream_data:
                profile.upstream.api_key = upstream_data["api_key"]
            if "api_format" in upstream_data:
                api_format = upstream_data["api_format"]
                if api_format not in API_FORMAT_TYPES:
                    return {"success": False, "error": "Invalid upstream.api_format"}
                profile.upstream.api_format = upstream_data["api_format"]

        # Update LLM params
        if "llm_params" in data:
            llm_data = data["llm_params"]
            for key in ["temperature", "top_p", "top_k", "max_tokens", "presence_penalty", "frequency_penalty", "seed"]:
                if key in llm_data:
                    setattr(profile.llm_params, key, llm_data[key])

        # Update reasoning
        if "reasoning" in data:
            reasoning_data = data["reasoning"]
            for key in ["enabled", "type", "effort", "budget_tokens", "custom_params", "filter_thinking_tags"]:
                if key in reasoning_data:
                    setattr(profile.reasoning, key, reasoning_data[key])

        profile.updated_at = datetime.now().isoformat()
        self.profiles.sort(key=lambda p: p.priority, reverse=True)

        if not self._save():
            return {"success": False, "error": "Failed to save configuration"}

        return {"success": True, "profile": profile.to_dict()}

    def delete_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a profile"""
        profile = self.get_profile(profile_id)
        if not profile:
            return {"success": False, "error": "Profile not found"}

        # Don't allow deleting the last profile
        if len(self.profiles) <= 1:
            return {"success": False, "error": "Cannot delete the last profile"}

        self.profiles.remove(profile)

        # Update default profile if needed
        if self.default_profile_id == profile_id:
            self.default_profile_id = self.profiles[0].id if self.profiles else ""

        if not self._save():
            return {"success": False, "error": "Failed to save configuration"}

        return {"success": True}

    def set_default_profile(self, profile_id: str) -> Dict[str, Any]:
        """Set the default profile"""
        profile = self.get_profile(profile_id)
        if not profile:
            return {"success": False, "error": "Profile not found"}

        self.default_profile_id = profile_id

        if not self._save():
            return {"success": False, "error": "Failed to save configuration"}

        return {"success": True, "default_profile": profile_id}

    def update_proxy_settings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update proxy server settings"""
        restart_required = False

        if "port" in data:
            port = data["port"]
            if isinstance(port, str):
                try:
                    port = int(port)
                except ValueError:
                    return {"success": False, "error": "Invalid port number"}
            if not (1 <= port <= 65535):
                return {"success": False, "error": "Port must be between 1 and 65535"}
            if port != self.proxy.port:
                self.proxy.port = port
                restart_required = True

        if "api_key" in data:
            self.proxy.api_key = data["api_key"]

        if not self._save():
            return {"success": False, "error": "Failed to save configuration"}

        return {
            "success": True,
            "restart_required": restart_required,
            "proxy": self.proxy.to_dict(),
        }

    def export_config(self) -> Dict[str, Any]:
        """Export full configuration"""
        return {
            "proxy": self.proxy.to_dict(hide_secrets=False),
            "profiles": [p.to_dict(hide_secrets=False) for p in self.profiles],
            "default_profile": self.default_profile_id,
        }

    def import_config(self, data: Dict[str, Any], merge: bool = True) -> Dict[str, Any]:
        """Import configuration"""
        try:
            if not data.get("profiles"):
                return {"success": False, "error": "No profiles found in import data"}

            if merge:
                # Merge with existing profiles
                existing_ids = {p.id for p in self.profiles}
                for profile_data in data.get("profiles", []):
                    if profile_data.get("id") not in existing_ids:
                        profile = Profile.from_dict(profile_data)
                        self.profiles.append(profile)
            else:
                # Replace all profiles
                self.profiles = [Profile.from_dict(p) for p in data.get("profiles", [])]
                if data.get("default_profile"):
                    self.default_profile_id = data["default_profile"]

            self.profiles.sort(key=lambda p: p.priority, reverse=True)

            if not self._save():
                return {"success": False, "error": "Failed to save configuration"}

            return {"success": True, "profiles_count": len(self.profiles)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_profiles(self, hide_secrets: bool = True) -> List[Dict[str, Any]]:
        """Get all profiles"""
        return [p.to_dict(hide_secrets=hide_secrets) for p in self.profiles]


# Global config manager instance
CONFIG_MANAGER = ConfigManager()
