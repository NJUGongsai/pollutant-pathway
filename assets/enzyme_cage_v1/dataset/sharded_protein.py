import json
import os
import pickle
from collections import OrderedDict
from collections.abc import Mapping

import torch


def _torch_load_trusted(path):
    torch_error = None
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        try:
            return torch.load(path, map_location="cpu")
        except Exception as exc:
            torch_error = exc
    except Exception as exc:
        torch_error = exc

    try:
        with open(path, "rb") as handle:
            return pickle.load(handle)
    except Exception as pickle_error:
        raise RuntimeError(
            f"Failed to load trusted mapping from {path} with torch.load "
            f"({type(torch_error).__name__}: {torch_error}) or pickle.load "
            f"({type(pickle_error).__name__}: {pickle_error})"
        ) from pickle_error


def _resolve_cache_size(manifest):
    value = os.environ.get("ENZYMECAGE_SHARD_CACHE_SIZE", "1").strip().lower()
    num_shards = len(set(manifest["uid_to_shard"].values()))
    if value == "all":
        return num_shards
    try:
        size = int(value)
    except ValueError as exc:
        raise ValueError(
            "ENZYMECAGE_SHARD_CACHE_SIZE must be a positive integer or 'all'"
        ) from exc
    if size < 1:
        raise ValueError("ENZYMECAGE_SHARD_CACHE_SIZE must be at least 1")
    return min(size, num_shards)


class LazyShardMapping(Mapping):
    def __init__(self, manifest_path):
        self.manifest_path = manifest_path
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.uid_to_shard = manifest["uid_to_shard"]
        self.shard_dir = os.path.join(os.path.dirname(manifest_path), manifest["shard_dir"])
        self.max_cached_shards = _resolve_cache_size(manifest)
        self._shard_cache = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0

    def _load_shard(self, shard_name):
        if shard_name in self._shard_cache:
            self._cache_hits += 1
            self._shard_cache.move_to_end(shard_name)
            return self._shard_cache[shard_name]

        self._cache_misses += 1
        shard_path = os.path.join(self.shard_dir, shard_name)
        shard_data = _torch_load_trusted(shard_path)
        self._shard_cache[shard_name] = shard_data
        self._shard_cache.move_to_end(shard_name)

        while len(self._shard_cache) > self.max_cached_shards:
            self._shard_cache.popitem(last=False)
            self._cache_evictions += 1
        return shard_data

    def cache_info(self):
        return {
            "max_cached_shards": self.max_cached_shards,
            "resident_shards": len(self._shard_cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "evictions": self._cache_evictions,
        }

    def __getitem__(self, key):
        shard_name = self.uid_to_shard[key]
        shard_data = self._load_shard(shard_name)
        return shard_data[key]

    def __iter__(self):
        return iter(self.uid_to_shard)

    def __len__(self):
        return len(self.uid_to_shard)

    def keys(self):
        return self.uid_to_shard.keys()

    def items(self):
        for key in self.uid_to_shard:
            yield key, self[key]

    def __contains__(self, key):
        return key in self.uid_to_shard


def _load_sharded_mapping(path, expected_format=None):
    obj = _torch_load_trusted(path)
    if isinstance(obj, dict) and obj.get("__format__") in {
        "sharded_gvp_v1",
        "sharded_esm_pocket_v1",
    }:
        if expected_format is not None and obj.get("__format__") != expected_format:
            raise ValueError(
                f"Expected {expected_format}, found {obj.get('__format__')} in {path}"
            )
        manifest_path = obj["manifest_path"]
        if not os.path.isabs(manifest_path):
            manifest_path = os.path.join(os.path.dirname(path), manifest_path)
        return LazyShardMapping(manifest_path)
    return obj


def load_protein_gvp_data(path):
    protein_obj = _torch_load_trusted(path)
    if isinstance(protein_obj, dict) and protein_obj.get("__format__") == "sharded_gvp_v1":
        manifest_path = protein_obj["manifest_path"]
        if not os.path.isabs(manifest_path):
            manifest_path = os.path.join(os.path.dirname(path), manifest_path)
        return LazyShardMapping(manifest_path)
    return protein_obj


def load_pocket_node_feature_data(path):
    return _load_sharded_mapping(path, expected_format="sharded_esm_pocket_v1")
