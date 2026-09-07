"""Shared helpers: config loading, project-relative paths, logging."""
import logging
import os

import yaml

_ROOT = os.path.dirname(os.path.abspath(__file__))


def get_path(rel: str) -> str:
    """Resolve a path relative to the project root and ensure its parent exists."""
    path = rel if os.path.isabs(rel) else os.path.join(_ROOT, rel)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


def load_config() -> dict:
    with open(os.path.join(_ROOT, "config.yaml"), "r") as f:
        return yaml.safe_load(f)


def get_logger(name: str) -> logging.Logger:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    return logging.getLogger(name)
